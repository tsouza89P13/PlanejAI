from collections import Counter, defaultdict
from datetime import timedelta
from statistics import pstdev
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import CapacidadeEquipe, Ocorrencia, Plano, RestricaoCalendario
from services.frequencia import calcular_espacamento_minimo, distribuir_semanas, ORDEM_DISTRIBUICAO

FREQUENCIAS_AGRUPAMENTO_PERMITIDO = {
    "Mensal", "Bimestral", "Trimestral",
    "Quadrimestral", "Semestral", "Anual"
}
 
# Frequências permitidas para balanceamento: não incluir 'Semanal'
FREQUENCIAS_BALANCEAMENTO_PERMITIDO = {
    "Mensal", "Bimestral", "Trimestral",
    "Quadrimestral", "Semestral", "Anual"
}


def _get_restricoes_por_semana(session, ano: int) -> tuple[set[int], dict[int, float]]:
    restricoes = session.query(RestricaoCalendario).filter(
        RestricaoCalendario.ano == ano,
        RestricaoCalendario.bloqueia_execucao == True,
    ).all()

    bloqueadas: set[int] = set()
    feriados_reducao: dict[int, float] = {}

    for restricao in restricoes:
        if not restricao.data_inicio or not restricao.data_fim:
            continue

        dias = (restricao.data_fim - restricao.data_inicio).days + 1
        data_atual = restricao.data_inicio
        semanas = set()
        while data_atual <= restricao.data_fim:
            semanas.add(data_atual.isocalendar()[1])
            data_atual += timedelta(days=1)

        if restricao.tipo == "Feriado" and dias == 1:
            semana = restricao.data_inicio.isocalendar()[1]
            feriados_reducao[semana] = feriados_reducao.get(semana, 0.0) + 8.0
        else:
            bloqueadas.update(semanas)

    return bloqueadas, feriados_reducao


def _capacidade_semanal_total(session, ano: int) -> float:
    resultado = session.query(func.sum(CapacidadeEquipe.num_colaboradores * 40 * CapacidadeEquipe.eficiencia)).filter(
        CapacidadeEquipe.ano == ano
    ).scalar()
    return float(resultado or 0.0)


def _ajustar_semana_disponivel(semana: int, janela_inicio: int, janela_fim: int, bloqueadas: set[int]) -> int:
    if semana < janela_inicio:
        semana = janela_inicio
    if semana > janela_fim:
        semana = janela_fim
    if semana not in bloqueadas:
        return semana

    deslocamento = 1
    while deslocamento <= max(52, janela_fim - janela_inicio + 1):
        anterior = semana - deslocamento
        proxima = semana + deslocamento
        if anterior >= janela_inicio and anterior not in bloqueadas:
            return anterior
        if proxima <= janela_fim and proxima not in bloqueadas:
            return proxima
        deslocamento += 1
    return semana


def _semana_preserva_espacamento(
    semana: int,
    plano: Plano,
    semanas_ocupadas: set[int],
    semana_atual: Optional[int] = None,
) -> bool:
    if semana < plano.janela_inicio or semana > plano.janela_fim:
        return False

    outras_semanas = set(semanas_ocupadas)
    if semana_atual is not None:
        outras_semanas.discard(semana_atual)

    if semana in outras_semanas:
        return False

    distancia_minima = calcular_espacamento_minimo(plano.frequencia) + 1
    return all(abs(semana - existente) >= distancia_minima for existente in outras_semanas)


def _buscar_semana_valida(
    semana_preferida: int,
    plano: Plano,
    bloqueadas: set[int],
    semanas_ocupadas: set[int],
) -> Optional[int]:
    inicio = max(1, int(plano.janela_inicio or 1))
    fim = min(52, int(plano.janela_fim or 52))
    semana_preferida = max(inicio, min(fim, int(semana_preferida)))

    candidatos = sorted(
        range(inicio, fim + 1),
        key=lambda candidato: (abs(candidato - semana_preferida), candidato),
    )
    for candidato in candidatos:
        if candidato in bloqueadas:
            continue
        if _semana_preserva_espacamento(candidato, plano, semanas_ocupadas):
            return candidato
    return None


def _calcular_hh_por_semana(ocorrencias: List[Ocorrencia]) -> dict[int, float]:
    totals = defaultdict(float)
    for ocorrencia in ocorrencias:
        totals[ocorrencia.semana] += ocorrencia.hh_previsto or 0.0
    return totals


def _obter_semana_moda(grupo: List[Ocorrencia]) -> Optional[int]:
    semanas = [oc.semana for oc in grupo]
    if not semanas:
        return None
    moda, _ = Counter(semanas).most_common(1)[0]
    return moda


def _balancear_carga(
    ocorrencias: List[Ocorrencia],
    plano_por_id: dict[int, Plano],
    feriados_reducao: dict[int, float],
    capacidade_total: float,
    bloqueadas: set[int],
    max_iter: int = 100,
) -> None:
    if not ocorrencias:
        return
    
    def calcular_desvio(ocs: List[Ocorrencia]) -> float:
        valores = list(_calcular_hh_por_semana(ocs).values())
        if len(valores) < 2:
            return 0.0
        return pstdev(valores)

    # mapa de semanas ocupadas por cada plano (para evitar duplicatas)
    semanas_por_plano: dict[int, set[int]] = defaultdict(set)
    for oc in ocorrencias:
        if oc.plano_id is not None:
            semanas_por_plano[oc.plano_id].add(oc.semana)

    for _ in range(max_iter):
        atual_std = calcular_desvio(ocorrencias)
        alteracao_executada = False
        totals = _calcular_hh_por_semana(ocorrencias)

        # ordenar ocorrências que têm maior janela primeiro
        for oc in sorted(ocorrencias, key=lambda x: (plano_por_id.get(x.plano_id).janela_fim - plano_por_id.get(x.plano_id).janela_inicio) if plano_por_id.get(x.plano_id) else 0, reverse=True):
            plano = plano_por_id.get(oc.plano_id)
            if not plano:
                continue

            # NÃO balancear planos com frequência semanal
            if plano.frequencia not in FREQUENCIAS_BALANCEAMENTO_PERMITIDO:
                continue

            flexibilidade = plano.janela_fim - plano.janela_inicio
            if flexibilidade <= 4:
                continue

            atual = oc.semana
            melhor_semana = atual
            melhor_std = atual_std

            # procurar candidatos em distâncias crescentes
            for desloc in range(1, max(2, flexibilidade) + 1):
                for candidato in (atual - desloc, atual + desloc):
                    if candidato < plano.janela_inicio or candidato > plano.janela_fim:
                        continue
                    if candidato in bloqueadas:
                        continue

                    # CORREÇÃO: nunca mover para semana já ocupada pelo mesmo plano
                    semanas_do_plano = semanas_por_plano.get(oc.plano_id, set())
                    if not _semana_preserva_espacamento(
                        candidato,
                        plano,
                        semanas_do_plano,
                        semana_atual=atual,
                    ):
                        continue

                    novo_totals = totals.copy()
                    novo_totals[atual] -= oc.hh_previsto or 0.0
                    novo_totals[candidato] += oc.hh_previsto or 0.0
                    valores = [v for v in novo_totals.values()]
                    if len(valores) < 2:
                        novo_std = 0.0
                    else:
                        novo_std = pstdev(valores)

                    if capacidade_total > 0:
                        limite = capacidade_total - feriados_reducao.get(candidato, 0.0)
                        if novo_totals[candidato] > limite:
                            continue

                    if novo_std < melhor_std:
                        melhor_std = novo_std
                        melhor_semana = candidato

                # se já encontramos uma melhoria significativa, podemos considerar interromper procura mais distante
                # (mas deixamos o loop continuar para achar melhores opções)

            if melhor_semana != atual:
                # atualizar estruturas
                totals[atual] -= oc.hh_previsto or 0.0
                totals[melhor_semana] += oc.hh_previsto or 0.0
                # atualizar semanas_por_plano para evitar duplicatas futuras
                semanas_por_plano[oc.plano_id].discard(atual)
                semanas_por_plano[oc.plano_id].add(melhor_semana)
                oc.semana = melhor_semana
                atual_std = melhor_std
                alteracao_executada = True

        if not alteracao_executada:
            break


def gerar_plano_anual(ano: int) -> dict[str, int]:
    """
    Gera o plano anual com ocorrências respeitando:
    1. Frequência exata de cada plano
    2. Espaçamento mínimo entre ocorrências
    3. Restrições de janela de execução
    4. Semanas bloqueadas/feriados
    5. Agrupamento de paradas onde permitido
    6. Balanceamento de carga por semana
    """
    session = SessionLocal()
    try:
        ocorrencias_existentes = session.query(Ocorrencia).filter(Ocorrencia.ano == ano).all()
        status_bloqueantes = {"Realizado", "Reprogramado", "Cancelado"}
        bloqueadas_por_execucao = [oc for oc in ocorrencias_existentes if oc.status in status_bloqueantes]
        if bloqueadas_por_execucao:
            return {
                "ocorrencias_geradas": 0,
                "erro": (
                    f"O plano de {ano} possui {len(bloqueadas_por_execucao)} ocorrência(s) "
                    "executada(s), reprogramada(s) ou cancelada(s). A geração foi bloqueada "
                    "para evitar perda de dados operacionais."
                ),
            }

        # Passo 1: Limpa apenas ocorrências ainda operacionais do ano.
        session.query(Ocorrencia).filter(
            Ocorrencia.ano == ano
        ).delete(synchronize_session=False)

        # Passo 2: Carrega dados
        planos = (
            session.query(Plano)
            .options(joinedload(Plano.equipamento))
            .filter(Plano.status == "Ativo")
            .all()
        )
        bloqueadas, feriados_reducao = _get_restricoes_por_semana(session, ano)
        capacidade_total = _capacidade_semanal_total(session, ano)

        # Passo 3: Ordena planos pela ordem de distribuição
        # Semanais primeiro, Anuais por último
        def ordem_freq(plano):
            try:
                return ORDEM_DISTRIBUICAO.index(plano.frequencia)
            except ValueError:
                return len(ORDEM_DISTRIBUICAO)

        planos_ordenados = sorted(planos, key=ordem_freq)

        ocorrencias: List[Ocorrencia] = []
        # Controle de semanas já ocupadas por plano
        # para evitar duplicatas
        semanas_por_plano: dict[int, set[int]] = defaultdict(set)

        # Passo 4: Distribui cada plano na ordem correta
        for plano in planos_ordenados:
            semanas_sugeridas = distribuir_semanas(
                plano.frequencia,
                plano.janela_inicio,
                plano.janela_fim
            )

            for semana in semanas_sugeridas:
                # Evita duplicata para o mesmo plano
                if semana in semanas_por_plano[plano.id]:
                    continue

                semana_disponivel = _buscar_semana_valida(
                    semana,
                    plano,
                    bloqueadas,
                    semanas_por_plano[plano.id],
                )
                if semana_disponivel is None:
                    continue
                
                # Registra que essa semana foi usada por este plano
                semanas_por_plano[plano.id].add(semana_disponivel)
                
                ocorrencias.append(
                    Ocorrencia(
                        plano_id=plano.id,
                        ano=ano,
                        semana=semana_disponivel,
                        status="Programado",
                        hh_previsto=plano.duracao_hh or 0.0,
                    )
                )

        plano_por_id = {p.id: p for p in planos}

        # Passo 5: Agrupamento de paradas
        # (só frequências baixas)
        grupos = defaultdict(list)
        for oc in ocorrencias:
            plano = plano_por_id.get(oc.plano_id)
            if not plano or not plano.grupo_parada:
                continue
            if plano.frequencia not in FREQUENCIAS_AGRUPAMENTO_PERMITIDO:
                continue
            chave = (plano.equipamento_id, plano.grupo_parada)
            grupos[chave].append(oc)

        for chave, grupo in grupos.items():
            if not grupo:
                continue
            modasemana = _obter_semana_moda(grupo)
            if modasemana is None:
                continue
            for oc in grupo:
                plano = plano_por_id.get(oc.plano_id)
                if not plano:
                    continue
                if plano.frequencia not in FREQUENCIAS_AGRUPAMENTO_PERMITIDO:
                    continue
                semanas_do_plano = semanas_por_plano.get(oc.plano_id, set())
                if (oc.semana != modasemana
                        and modasemana not in bloqueadas
                        and _semana_preserva_espacamento(
                            modasemana,
                            plano,
                            semanas_do_plano,
                            semana_atual=oc.semana,
                        )):
                    semanas_do_plano.discard(oc.semana)
                    semanas_do_plano.add(modasemana)
                    oc.semana = modasemana

        # Passo 6: Balanceamento de carga
        _balancear_carga(ocorrencias, plano_por_id, feriados_reducao, capacidade_total, bloqueadas)

        # Passo 7: Persiste ocorrências
        if ocorrencias:
            session.add_all(ocorrencias)
        session.commit()

        return {"ocorrencias_geradas": len(ocorrencias)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
