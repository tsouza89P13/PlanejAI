from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import re
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import CapacidadeEquipe, Equipamento, Ocorrencia, Plano, RestricaoCalendario
from services.capacidade import capacidade_disponivel_por_disciplina, hh_necessario_por_disciplina
from services.dashboard import calcular_indicadores
from services.status import status_ocorrencia


ROOT = Path(__file__).resolve().parent.parent
BASE_CONHECIMENTO_PATH = ROOT / "docs" / "base_conhecimento_assistente.md"


def _ano_da_pergunta(pergunta: str, padrao: int | None = None) -> int:
    match = re.search(r"\b(20\d{2})\b", pergunta)
    return int(match.group(1)) if match else (padrao or date.today().year)


def _semana_da_pergunta(pergunta: str) -> int | None:
    match = re.search(r"\b(?:s|semana)\s*([1-9]|[1-4]\d|5[0-2])\b", pergunta, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _codigo_equipamento_da_pergunta(pergunta: str) -> str | None:
    match = re.search(r"\b([A-Z0-9]{2,}(?:[-|][A-Z0-9]{2,})+)\b", pergunta.upper())
    return match.group(1).replace("|", "-") if match else None


def _normalizar_texto(texto: str) -> str:
    substituicoes = str.maketrans(
        "áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ",
        "aaaaeeiooouucAAAAEEIOOOUUC",
    )
    return texto.translate(substituicoes).lower()


def _palavras_relevantes(texto: str) -> set[str]:
    texto_norm = _normalizar_texto(texto)
    palavras = set(re.findall(r"[a-z0-9]{4,}", texto_norm))
    irrelevantes = {
        "para",
        "como",
        "qual",
        "quais",
        "quando",
        "onde",
        "sobre",
        "esse",
        "essa",
        "desse",
        "dessa",
        "sistema",
        "planejai",
    }
    return palavras - irrelevantes


def _ocorrencia_linha(oc: Ocorrencia) -> dict[str, Any]:
    plano = oc.plano
    equipamento = plano.equipamento if plano else None
    return {
        "equipamento": equipamento.codigo if equipamento else "-",
        "descricao_equipamento": equipamento.descricao if equipamento else "-",
        "plano": plano.nome if plano else "-",
        "disciplina": plano.disciplina if plano else "-",
        "tipo_intervencao": plano.tipo_intervencao if plano else "-",
        "ano": oc.ano,
        "semana": oc.semana,
        "status": status_ocorrencia(oc.status, oc.ano, oc.semana),
        "hh_previsto": oc.hh_previsto or 0.0,
        "hh_realizado": oc.hh_realizado or 0.0,
        "observacao": oc.observacao or "",
    }


def consultar_resumo_dashboard(ano: int) -> dict[str, Any]:
    indicadores = calcular_indicadores(ano)
    return {
        "nome": "consultar_resumo_dashboard",
        "resumo": f"Indicadores consolidados do ano {ano}.",
        "dados": {
            "ano": ano,
            "kpis": indicadores["kpis"],
            "absolutos": indicadores["absolutos"],
        },
    }


def consultar_ocorrencias_atrasadas(ano: int, limite: int = 50) -> dict[str, Any]:
    session = SessionLocal()
    try:
        ocorrencias = (
            session.query(Ocorrencia)
            .join(Plano, Ocorrencia.plano_id == Plano.id)
            .join(Equipamento, Plano.equipamento_id == Equipamento.id)
            .options(joinedload(Ocorrencia.plano).joinedload(Plano.equipamento))
            .filter(Ocorrencia.ano == ano)
            .order_by(Ocorrencia.semana, Plano.nome)
            .all()
        )
        atrasadas = [oc for oc in ocorrencias if status_ocorrencia(oc.status, oc.ano, oc.semana) == "Atrasado"]
        linhas = [_ocorrencia_linha(oc) for oc in atrasadas[:limite]]
        por_disciplina = Counter(linha["disciplina"] for linha in linhas)
        return {
            "nome": "consultar_ocorrencias_atrasadas",
            "resumo": f"{len(atrasadas)} ocorrência(s) atrasada(s) em {ano}.",
            "dados": {
                "ano": ano,
                "total": len(atrasadas),
                "hh_total": sum((oc.hh_previsto or 0.0) for oc in atrasadas),
                "por_disciplina": dict(por_disciplina),
                "registros": linhas,
            },
        }
    finally:
        session.close()


def consultar_ocorrencias_por_semana(ano: int, semana: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        ocorrencias = (
            session.query(Ocorrencia)
            .join(Plano, Ocorrencia.plano_id == Plano.id)
            .join(Equipamento, Plano.equipamento_id == Equipamento.id)
            .options(joinedload(Ocorrencia.plano).joinedload(Plano.equipamento))
            .filter(Ocorrencia.ano == ano, Ocorrencia.semana == semana)
            .order_by(Plano.disciplina, Plano.nome)
            .all()
        )
        linhas = [_ocorrencia_linha(oc) for oc in ocorrencias]
        return {
            "nome": "consultar_ocorrencias_por_semana",
            "resumo": f"{len(linhas)} ocorrência(s) encontradas na S{semana}/{ano}.",
            "dados": {
                "ano": ano,
                "semana": semana,
                "total": len(linhas),
                "hh_total": sum(linha["hh_previsto"] for linha in linhas),
                "registros": linhas,
            },
        }
    finally:
        session.close()


def consultar_backlog_por_equipamento(ano: int, limite: int = 10) -> dict[str, Any]:
    session = SessionLocal()
    try:
        ocorrencias = (
            session.query(Ocorrencia)
            .join(Plano, Ocorrencia.plano_id == Plano.id)
            .join(Equipamento, Plano.equipamento_id == Equipamento.id)
            .options(joinedload(Ocorrencia.plano).joinedload(Plano.equipamento))
            .filter(Ocorrencia.ano == ano)
            .all()
        )
        agregados: dict[str, dict[str, Any]] = {}
        for oc in ocorrencias:
            if status_ocorrencia(oc.status, oc.ano, oc.semana) != "Atrasado":
                continue
            equipamento = oc.plano.equipamento if oc.plano else None
            chave = equipamento.codigo if equipamento else "-"
            item = agregados.setdefault(
                chave,
                {
                    "equipamento": chave,
                    "descricao": equipamento.descricao if equipamento else "-",
                    "ocorrencias": 0,
                    "hh_atrasado": 0.0,
                },
            )
            item["ocorrencias"] += 1
            item["hh_atrasado"] += oc.hh_previsto or 0.0
        registros = sorted(agregados.values(), key=lambda item: item["hh_atrasado"], reverse=True)[:limite]
        return {
            "nome": "consultar_backlog_por_equipamento",
            "resumo": f"Ranking de backlog por equipamento em {ano}.",
            "dados": {"ano": ano, "registros": registros},
        }
    finally:
        session.close()


def consultar_capacidade_por_disciplina(ano: int) -> dict[str, Any]:
    hh_necessario = hh_necessario_por_disciplina(ano)
    hh_disponivel = capacidade_disponivel_por_disciplina(ano)
    session = SessionLocal()
    try:
        capacidades = {
            (cap.disciplina or "-"): cap
            for cap in session.query(CapacidadeEquipe).filter(CapacidadeEquipe.ano == ano).all()
        }
        disciplinas = sorted(set(hh_necessario) | set(hh_disponivel) | set(capacidades))
        registros = []
        for disciplina in disciplinas:
            cap = capacidades.get(disciplina)
            necessario = hh_necessario.get(disciplina, 0.0)
            disponivel = hh_disponivel.get(disciplina, 0.0)
            registros.append(
                {
                    "disciplina": disciplina,
                    "hh_necessario_semana": necessario,
                    "hh_disponivel_semana": disponivel,
                    "colaboradores": cap.num_colaboradores if cap else 0,
                    "eficiencia": cap.eficiencia if cap else 0.0,
                    "situacao": "OK" if disponivel >= necessario else "Atenção",
                }
            )
        return {
            "nome": "consultar_capacidade_por_disciplina",
            "resumo": f"Capacidade por disciplina em {ano}.",
            "dados": {"ano": ano, "registros": registros},
        }
    finally:
        session.close()


def consultar_planos_por_equipamento(codigo: str | None) -> dict[str, Any]:
    session = SessionLocal()
    try:
        query = session.query(Plano).join(Equipamento, Plano.equipamento_id == Equipamento.id).options(joinedload(Plano.equipamento))
        if codigo:
            query = query.filter(Equipamento.codigo.ilike(f"%{codigo}%"))
        planos = query.order_by(Equipamento.codigo, Plano.nome).limit(80).all()
        registros = [
            {
                "equipamento": plano.equipamento.codigo if plano.equipamento else "-",
                "plano": plano.nome,
                "disciplina": plano.disciplina,
                "frequencia": plano.frequencia,
                "janela": f"S{plano.janela_inicio}-S{plano.janela_fim}",
                "status": plano.status,
                "grupo_parada": plano.grupo_parada or "",
            }
            for plano in planos
        ]
        return {
            "nome": "consultar_planos_por_equipamento",
            "resumo": f"{len(registros)} plano(s) encontrado(s).",
            "dados": {"codigo_pesquisado": codigo, "registros": registros},
        }
    finally:
        session.close()


def consultar_ranking_planos_por_equipamento(limite: int = 10) -> dict[str, Any]:
    session = SessionLocal()
    try:
        rows = (
            session.query(
                Equipamento.codigo,
                Equipamento.descricao,
                Equipamento.area,
                Equipamento.criticidade,
                func.count(Plano.id).label("total_planos"),
                func.sum(case((Plano.status == "Ativo", 1), else_=0)).label("planos_ativos"),
                func.sum(Plano.duracao_hh).label("hh_total"),
            )
            .join(Plano, Equipamento.id == Plano.equipamento_id)
            .group_by(Equipamento.id)
            .order_by(func.count(Plano.id).desc(), Equipamento.codigo)
            .limit(limite)
            .all()
        )
        registros = [
            {
                "equipamento": codigo,
                "descricao": descricao,
                "area": area or "",
                "criticidade": criticidade or "",
                "total_planos": int(total_planos or 0),
                "planos_ativos": int(planos_ativos or 0),
                "hh_total_planos": float(hh_total or 0.0),
            }
            for codigo, descricao, area, criticidade, total_planos, planos_ativos, hh_total in rows
        ]
        return {
            "nome": "consultar_ranking_planos_por_equipamento",
            "resumo": "Ranking dos equipamentos com mais planos cadastrados.",
            "dados": {"registros": registros},
        }
    finally:
        session.close()


def consultar_equipamentos_sem_plano() -> dict[str, Any]:
    session = SessionLocal()
    try:
        equipamentos = (
            session.query(Equipamento)
            .outerjoin(Plano, Equipamento.id == Plano.equipamento_id)
            .group_by(Equipamento.id)
            .having(func.count(Plano.id) == 0)
            .order_by(Equipamento.codigo)
            .all()
        )
        registros = [
            {
                "codigo": eq.codigo,
                "descricao": eq.descricao,
                "area": eq.area or "",
                "criticidade": eq.criticidade or "",
                "status": eq.status or "",
            }
            for eq in equipamentos
        ]
        return {
            "nome": "consultar_equipamentos_sem_plano",
            "resumo": f"{len(registros)} equipamento(s) sem plano vinculado.",
            "dados": {"registros": registros},
        }
    finally:
        session.close()


def consultar_concentracao_por_semana(ano: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        rows = (
            session.query(Ocorrencia.semana, func.count(Ocorrencia.id), func.sum(Ocorrencia.hh_previsto))
            .filter(Ocorrencia.ano == ano)
            .group_by(Ocorrencia.semana)
            .order_by(func.sum(Ocorrencia.hh_previsto).desc())
            .all()
        )
        registros = [
            {"semana": semana, "ocorrencias": total, "hh_previsto": float(hh or 0.0)}
            for semana, total, hh in rows
        ]
        return {
            "nome": "consultar_concentracao_por_semana",
            "resumo": f"Concentração de HH por semana em {ano}.",
            "dados": {"ano": ano, "registros": registros[:20]},
        }
    finally:
        session.close()


def consultar_restricoes_calendario(ano: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        restricoes = (
            session.query(RestricaoCalendario)
            .filter(RestricaoCalendario.ano == ano)
            .order_by(RestricaoCalendario.data_inicio)
            .all()
        )
        registros = [
            {
                "tipo": item.tipo,
                "descricao": item.descricao or "",
                "data_inicio": item.data_inicio.isoformat() if item.data_inicio else "",
                "data_fim": item.data_fim.isoformat() if item.data_fim else "",
                "bloqueia_execucao": bool(item.bloqueia_execucao),
            }
            for item in restricoes
        ]
        return {
            "nome": "consultar_restricoes_calendario",
            "resumo": f"{len(registros)} restrição(ões) de calendário em {ano}.",
            "dados": {"ano": ano, "registros": registros},
        }
    finally:
        session.close()


def consultar_base_conhecimento(pergunta: str, limite: int = 4) -> dict[str, Any]:
    if not BASE_CONHECIMENTO_PATH.exists():
        return {
            "nome": "consultar_base_conhecimento",
            "resumo": "Base de conhecimento nao encontrada.",
            "dados": {"registros": []},
        }

    conteudo = BASE_CONHECIMENTO_PATH.read_text(encoding="utf-8")
    secoes = re.findall(r"^### (.+?)\n\n(.+?)(?=\n### |\n## |\Z)", conteudo, flags=re.MULTILINE | re.DOTALL)
    termos_pergunta = _palavras_relevantes(pergunta)
    registros = []

    for titulo, corpo in secoes:
        termos_secao = _palavras_relevantes(f"{titulo} {corpo}")
        intersecao = termos_pergunta & termos_secao
        if not intersecao:
            continue
        score = len(intersecao)
        if _normalizar_texto(titulo).strip("?") in _normalizar_texto(pergunta):
            score += 5
        registros.append(
            {
                "titulo": titulo.strip(),
                "resposta": corpo.strip(),
                "score": score,
                "termos_encontrados": sorted(intersecao),
            }
        )

    registros = sorted(registros, key=lambda item: item["score"], reverse=True)[:limite]
    return {
        "nome": "consultar_base_conhecimento",
        "resumo": f"{len(registros)} trecho(s) encontrado(s) na base de conhecimento.",
        "dados": {"registros": registros, "arquivo": str(BASE_CONHECIMENTO_PATH)},
    }


def consultar_limitacoes_sistema() -> dict[str, Any]:
    registros = [
        {
            "area": "Assistente",
            "limitacao": "O modo Jovem Aprendiz é determinístico: ele consulta ferramentas locais e não usa uma IA externa.",
            "impacto": "Perguntas muito abertas ou pessoais podem não ter resposta completa sem OpenAI, Gemini ou Claude.",
        },
        {
            "area": "Assistente",
            "limitacao": "As respostas dependem das ferramentas de leitura já cadastradas no PlanejAI.",
            "impacto": "Se uma pergunta não tiver ferramenta correspondente, o assistente deve avisar a limitação em vez de inventar.",
        },
        {
            "area": "Execução",
            "limitacao": "A reprogramação altera a semana da ocorrência, mas não executa uma otimização completa do mapa anual.",
            "impacto": "O mapa reflete a nova semana, porém conflitos de capacidade/restrição devem ser conferidos pelo usuário.",
        },
        {
            "area": "Planos",
            "limitacao": "Prioridade e janela ficam registradas no plano, mas a prioridade ainda não é um critério automático forte de decisão.",
            "impacto": "A priorização operacional ainda depende de análise do usuário e dos indicadores.",
        },
        {
            "area": "Segurança",
            "limitacao": "A aplicação local não possui autenticação por usuário/perfis de permissão.",
            "impacto": "Em uso multiusuário real, seria necessário incluir login, autorização e trilha de auditoria mais forte.",
        },
    ]
    return {
        "nome": "consultar_limitacoes_sistema",
        "resumo": "Limitacoes e fragilidades conhecidas do PlanejAI.",
        "dados": {"registros": registros},
    }


def consultar_pergunta_fora_escopo(pergunta: str) -> dict[str, Any]:
    return {
        "nome": "pergunta_fora_escopo",
        "resumo": "Pergunta sem ferramenta local segura para resposta.",
        "dados": {
            "pergunta": pergunta,
            "mensagem": (
                "Não encontrei uma ferramenta local capaz de responder essa pergunta com segurança. "
                "O PlanejAI consegue consultar dados e orientar sobre funções do sistema, mas não possui "
                "memória pessoal do usuário nem deve inventar informações fora do banco."
            ),
            "sugestoes": [
                "Pergunte por indicadores do dashboard, backlog, atrasos, capacidade ou semanas carregadas.",
                "Pergunte como usar telas do sistema, como importação, equipamentos, planos, mapa ou execução.",
                "Para perguntas abertas em linguagem natural, configure OpenAI, Gemini ou Claude com uma chave API.",
            ],
        },
    }


def consultar_ajuda_sistema(pergunta: str) -> dict[str, Any]:
    topicos = {
        "equipamentos": {
            "titulo": "Cadastro de Equipamentos",
            "orientacoes": [
                "Acesse Inputs > Equipamentos.",
                "Preencha Código, Descrição, Local, Área, Criticidade e Status.",
                "O Código identifica o ativo e deve ser único.",
                "Ao remover um equipamento, todos os planos e ocorrências vinculados também são removidos após confirmação explícita.",
            ],
        },
        "planos": {
            "titulo": "Cadastro de Planos de Manutenção",
            "orientacoes": [
                "Acesse Inputs > Planos de Manutenção.",
                "Vincule o plano a um equipamento ativo.",
                "Informe tipo de intervenção, disciplina, frequência, duração em HH, prioridade, janela de execução e status.",
                "A janela início/fim limita as semanas em que o plano pode ser distribuído no mapa anual.",
                "A prioridade está cadastrada e disponível para análise, mas atualmente não é usada como critério automático de programação.",
            ],
        },
        "grupo_parada": {
            "titulo": "Grupo de Parada",
            "orientacoes": [
                "O Grupo de Parada agrupa planos do mesmo equipamento que devem ocorrer na mesma parada operacional.",
                "Na geração do mapa anual, planos do mesmo equipamento com o mesmo grupo de parada podem ser alinhados na mesma semana.",
                "O agrupamento respeita janela, restrições de calendário e espaçamento mínimo.",
                "É mais útil para atividades mensais, bimestrais, trimestrais, quadrimestrais, semestrais e anuais.",
            ],
        },
        "importacao": {
            "titulo": "Importação via Excel",
            "orientacoes": [
                "Acesse Inputs > Importação via Excel.",
                "Baixe primeiro o template oficial.",
                "Importe equipamentos antes de importar planos.",
                "O código do equipamento informado no arquivo de planos precisa existir no cadastro de equipamentos.",
                "O sistema valida campos obrigatórios, frequência, disciplina, duração, prioridade, janelas e status.",
            ],
        },
        "mapa": {
            "titulo": "Mapa de 52 Semanas",
            "orientacoes": [
                "Acesse Gestão > Mapa de 52 Semanas.",
                "Gere o plano anual para distribuir as ocorrências conforme frequência, janela, restrições e capacidade.",
                "As semanas são exibidas como S1 a S52.",
                "O mapa lê as ocorrências diretamente do banco. Reprogramações feitas na execução aparecem no mapa automaticamente.",
            ],
        },
        "execucao": {
            "titulo": "Execução de Ocorrências",
            "orientacoes": [
                "Acesse Inputs > Execução de Ocorrência.",
                "Use os filtros de ano, semana e equipamento.",
                "É possível marcar como realizado, reprogramar ou cancelar uma ocorrência.",
                "Ao reprogramar, a ocorrência muda de semana e passa a aparecer como Reprogramado no mapa.",
                "Alterações ficam registradas no histórico da ocorrência.",
            ],
        },
        "calendario": {
            "titulo": "Calendário de Restrição",
            "orientacoes": [
                "Acesse Inputs > Calendário de Restrição.",
                "Cadastre feriados, grandes paradas, férias ou eventos.",
                "Quando marcado como bloqueio, o período restringe a distribuição das ocorrências no mapa anual.",
            ],
        },
        "capacidade": {
            "titulo": "Capacidade de Equipe",
            "orientacoes": [
                "Acesse Inputs > Capacidade de Equipe.",
                "Cadastre colaboradores e eficiência por disciplina e ano.",
                "A capacidade é usada para comparar demanda planejada com HH disponível semanal.",
            ],
        },
        "dashboard": {
            "titulo": "Dashboard",
            "orientacoes": [
                "Acesse Gestão > Dashboard.",
                "Use os filtros de ano, disciplina, tipo de intervenção e área.",
                "A tela mostra eficiência, aderência, backlog, cancelamento, HH planejado e gráficos da carteira.",
            ],
        },
    }

    pergunta_norm = pergunta.lower()
    chaves = []
    mapa_palavras = {
        "equipamentos": ["equipamento", "ativo", "criticidade"],
        "planos": ["plano", "frequência", "frequencia", "janela", "prioridade"],
        "grupo_parada": ["grupo de parada", "parada"],
        "importacao": ["importação", "importacao", "excel", "template"],
        "mapa": ["mapa", "52", "semanas", "s52"],
        "execucao": ["execução", "execucao", "ocorrência", "ocorrencia", "reprogram"],
        "calendario": ["calendário", "calendario", "restrição", "restricao", "feriado"],
        "capacidade": ["capacidade", "equipe", "colaboradores"],
        "dashboard": ["dashboard", "indicador", "kpi"],
    }
    for chave, palavras in mapa_palavras.items():
        if any(palavra in pergunta_norm for palavra in palavras):
            chaves.append(chave)

    if not chaves:
        chaves = ["dashboard", "mapa", "equipamentos", "planos"]

    registros = [topicos[chave] for chave in dict.fromkeys(chaves)]
    return {
        "nome": "consultar_ajuda_sistema",
        "resumo": "Orientações oficiais de uso do PlanejAI.",
        "dados": {"registros": registros},
    }


def selecionar_e_executar_ferramentas(pergunta: str) -> list[dict[str, Any]]:
    pergunta_norm = pergunta.lower()
    ano = _ano_da_pergunta(pergunta)
    semana = _semana_da_pergunta(pergunta)
    codigo = _codigo_equipamento_da_pergunta(pergunta)
    resultados: list[dict[str, Any]] = []
    pergunta_de_ajuda = any(
        palavra in pergunta_norm
        for palavra in [
            "como",
            "para que serve",
            "o que é",
            "o que significa",
            "funciona",
            "usar",
            "cadastro",
            "cadastrar",
            "importar",
            "explica",
            "dúvida",
            "duvida",
        ]
    )

    if pergunta_de_ajuda:
        resultados.append(consultar_ajuda_sistema(pergunta))
        base = consultar_base_conhecimento(pergunta)
        if base["dados"].get("registros"):
            resultados.append(base)
        return resultados

    if any(
        palavra in pergunta_norm
        for palavra in [
            "fragilidade",
            "fragilidades",
            "ponto fraco",
            "pontos fracos",
            "limitacao",
            "limitacoes",
            "limitação",
            "limitações",
            "risco do sistema",
            "riscos do sistema",
            "problema do sistema",
        ]
    ):
        resultados.append(consultar_limitacoes_sistema())
        base = consultar_base_conhecimento(pergunta)
        if base["dados"].get("registros"):
            resultados.append(base)
        return resultados

    if any(palavra in pergunta_norm for palavra in ["atrasad", "backlog"]):
        resultados.append(consultar_ocorrencias_atrasadas(ano))
        resultados.append(consultar_backlog_por_equipamento(ano))

    if semana is not None or "semana" in pergunta_norm:
        resultados.append(consultar_ocorrencias_por_semana(ano, semana or date.today().isocalendar()[1]))

    if any(palavra in pergunta_norm for palavra in ["capacidade", "sobrecarreg", "equipe", "disciplina"]):
        resultados.append(consultar_capacidade_por_disciplina(ano))

    pergunta_ranking_planos = (
        "mais plano" in pergunta_norm
        or "mais planos" in pergunta_norm
        or "maior quantidade de plano" in pergunta_norm
        or "maior quantidade de planos" in pergunta_norm
        or "quantos planos por equipamento" in pergunta_norm
    )

    if pergunta_ranking_planos:
        resultados.append(consultar_ranking_planos_por_equipamento())
    elif codigo and any(palavra in pergunta_norm for palavra in ["plano", "equipamento"]):
        resultados.append(consultar_planos_por_equipamento(codigo))
    elif any(palavra in pergunta_norm for palavra in ["plano", "equipamento"]):
        resultados.append(consultar_ranking_planos_por_equipamento())
        resultados.append(consultar_planos_por_equipamento(codigo))

    if any(palavra in pergunta_norm for palavra in ["sem plano", "sem planos"]):
        resultados.append(consultar_equipamentos_sem_plano())

    if any(palavra in pergunta_norm for palavra in ["concentra", "carregad", "carga", "hh por semana"]):
        resultados.append(consultar_concentracao_por_semana(ano))

    if any(palavra in pergunta_norm for palavra in ["restri", "calend", "feriado", "parada"]):
        resultados.append(consultar_restricoes_calendario(ano))

    if any(palavra in pergunta_norm for palavra in ["dashboard", "indicador", "indicadores", "kpi", "resumo geral", "carteira"]):
        resultados.append(consultar_resumo_dashboard(ano))
        resultados.append(consultar_concentracao_por_semana(ano))

    if not resultados:
        base = consultar_base_conhecimento(pergunta)
        if base["dados"].get("registros"):
            resultados.append(base)
        else:
            resultados.append(consultar_pergunta_fora_escopo(pergunta))

    nomes_vistos = set()
    unicos = []
    for resultado in resultados:
        nome = resultado["nome"]
        if nome not in nomes_vistos:
            unicos.append(resultado)
            nomes_vistos.add(nome)
    return unicos
