import math
from collections import defaultdict

from database import SessionLocal
from models import CapacidadeEquipe, Ocorrencia, Plano


def calcular_hh_util_semanal(num_colaboradores: int, eficiencia: float) -> float:
    return num_colaboradores * 40 * eficiencia


def calcular_dimensionamento(hh_necessario_medio: float, eficiencia: float) -> int:
    if not hh_necessario_medio or hh_necessario_medio == 0:
        return 0
    return math.ceil(hh_necessario_medio / (40 * eficiencia))


def hh_necessario_por_disciplina(ano: int) -> dict[str, float]:
    """
    Retorna HH médio necessário por semana para cada disciplina,
    baseado nos planos ativos do ano selecionado.
    """
    from models import Ocorrencia, Plano
    from sqlalchemy import func

    session = SessionLocal()
    try:
        resultado = (
            session.query(
                Plano.disciplina,
                func.sum(Ocorrencia.hh_previsto).label("total_hh")
            )
            .join(Ocorrencia, Ocorrencia.plano_id == Plano.id)
            .filter(
                Ocorrencia.ano == ano,
                Ocorrencia.status != "Cancelado"
            )
            .group_by(Plano.disciplina)
            .all()
        )

        return {
            disciplina: round(total_hh / 52, 1)
            for disciplina, total_hh in resultado
            if total_hh is not None
        }
    finally:
        session.close()


def capacidade_disponivel_por_disciplina(ano: int) -> dict[str, float]:
    session = SessionLocal()
    try:
        resultados = (
            session.query(CapacidadeEquipe.disciplina, CapacidadeEquipe.num_colaboradores, CapacidadeEquipe.eficiencia)
            .filter(CapacidadeEquipe.ano == ano)
            .all()
        )
        return {
            disciplina: calcular_hh_util_semanal(num_colaboradores, eficiencia)
            for disciplina, num_colaboradores, eficiencia in resultados
        }
    finally:
        session.close()


def semanas_sobrecarregadas(ano: int) -> list[int]:
    session = SessionLocal()
    try:
        capacidade_total = sum(calcular_hh_util_semanal(num, eff) for _, num, eff in session.query(CapacidadeEquipe.disciplina, CapacidadeEquipe.num_colaboradores, CapacidadeEquipe.eficiencia).filter(CapacidadeEquipe.ano == ano).all())
        semana_totais = defaultdict(float)
        ocorrencias = session.query(Ocorrencia).filter(Ocorrencia.ano == ano).all()
        for oc in ocorrencias:
            semana_totais[oc.semana] += oc.hh_previsto or 0.0
        return [semana for semana, total in semana_totais.items() if total > capacidade_total]
    finally:
        session.close()
