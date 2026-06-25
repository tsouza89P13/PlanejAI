from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import CapacidadeEquipe, Equipamento, Ocorrencia, Plano
from services.status import status_ocorrencia


PLOT_TEMPLATE = "plotly_white"
COLORWAY = ["#38BDF8", "#34D399", "#7C3AED", "#D97706", "#EF4444", "#64748B"]
STATUS_COLORS = {
    "Programado": "#38BDF8",
    "Realizado": "#34D399",
    "Reprogramado": "#D97706",
    "Cancelado": "#94A3B8",
    "Atrasado": "#EF4444",
}


def _aplicar_layout(fig, titulo: str):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18, color="#172033")),
        template=PLOT_TEMPLATE,
        colorway=COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#172033"),
        margin=dict(l=24, r=24, t=58, b=34),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#172033", size=13),
            title=dict(font=dict(color="#172033")),
        ),
    )
    fig.update_xaxes(
        gridcolor="#D8E0EA",
        zerolinecolor="#D8E0EA",
        color="#172033",
        title_font=dict(color="#172033", size=13),
        tickfont=dict(color="#172033", size=12),
    )
    fig.update_yaxes(
        gridcolor="#D8E0EA",
        zerolinecolor="#D8E0EA",
        color="#172033",
        title_font=dict(color="#172033", size=13),
        tickfont=dict(color="#172033", size=12),
    )
    return fig


def _consulta_ocorrencias(session, ano: int, disciplinas: List[str], tipos: List[str], areas: List[str]):
    query = (
        session.query(Ocorrencia)
        .join(Plano, Ocorrencia.plano)
        .join(Equipamento, Plano.equipamento)
        .options(joinedload(Ocorrencia.plano).joinedload(Plano.equipamento))
        .filter(Ocorrencia.ano == ano)
    )

    if disciplinas:
        query = query.filter(Plano.disciplina.in_(disciplinas))
    if tipos:
        query = query.filter(Plano.tipo_intervencao.in_(tipos))
    if areas:
        query = query.filter(Equipamento.area.in_(areas))

    return query.all()


def _capacidade_semana(session, ano: int, disciplinas: List[str] = None) -> float:
    disciplinas = disciplinas or []
    query = session.query(
        func.sum(CapacidadeEquipe.num_colaboradores * 40 * CapacidadeEquipe.eficiencia)
    ).filter(CapacidadeEquipe.ano == ano)
    if disciplinas:
        query = query.filter(CapacidadeEquipe.disciplina.in_(disciplinas))
    resultado = query.scalar()
    return float(resultado or 0.0)


def calcular_indicadores(ano: int, disciplinas: List[str] = None, tipos: List[str] = None, areas: List[str] = None) -> Dict[str, object]:
    disciplinas = disciplinas or []
    tipos = tipos or []
    areas = areas or []

    session = SessionLocal()
    try:
        ocorrencias = _consulta_ocorrencias(session, ano, disciplinas, tipos, areas)
        data = [
            {
                "ano": oc.ano,
                "semana": oc.semana,
                "status": status_ocorrencia(oc.status, oc.ano, oc.semana),
                "hh_previsto": oc.hh_previsto or 0.0,
                "hh_realizado": oc.hh_realizado or 0.0,
                "disciplina": oc.plano.disciplina,
                "tipo_intervencao": oc.plano.tipo_intervencao,
                "equipamento": oc.plano.equipamento.descricao if oc.plano.equipamento else "",
                "area": oc.plano.equipamento.area if oc.plano.equipamento else "",
            }
            for oc in ocorrencias
        ]
        df = pd.DataFrame(data)
        if df.empty:
            df = pd.DataFrame(columns=["ano", "semana", "status", "hh_previsto", "hh_realizado", "disciplina", "tipo_intervencao", "equipamento", "area"])

        hh_planejado = df["hh_previsto"].sum()
        hh_executado = df.loc[df["status"] == "Realizado", "hh_realizado"].sum()
        hh_cancelado = df.loc[df["status"] == "Cancelado", "hh_previsto"].sum()
        hh_reprogramado = df.loc[df["status"] == "Reprogramado", "hh_previsto"].sum()
        hh_atrasado = df.loc[df["status"] == "Atrasado", "hh_previsto"].sum()
        executado_prazo = hh_executado

        eficiencia = hh_executado / hh_planejado if hh_planejado else 0.0
        aderencia = executado_prazo / hh_planejado if hh_planejado else 0.0
        backlog = hh_atrasado / hh_planejado if hh_planejado else 0.0
        cancelamento = hh_cancelado / hh_planejado if hh_planejado else 0.0

        capacidade_semanal_total = _capacidade_semana(session, ano, disciplinas)
        capacidade_disponivel = capacidade_semanal_total

        semana_totais = df.groupby("semana")["hh_previsto"].sum().reindex(range(1, 53), fill_value=0)
        desvio_semanal = float(semana_totais.std(ddof=0)) if not semana_totais.empty else 0.0

        acumulado_planejado = semana_totais.cumsum()
        realizado_semana = df.loc[df["status"] == "Realizado"].groupby("semana")["hh_realizado"].sum().reindex(range(1, 53), fill_value=0)
        acumulado_realizado = realizado_semana.cumsum()

        return {
            "kpis": {
                "eficiencia": eficiencia,
                "aderencia": aderencia,
                "backlog": backlog,
                "cancelamento": cancelamento,
            },
            "absolutos": {
                "hh_planejado": hh_planejado,
                "hh_executado": hh_executado,
                "hh_cancelado": hh_cancelado,
                "hh_reprogramado": hh_reprogramado,
                "hh_atrasado": hh_atrasado,
                "total_atividades": len(df),
            },
            "graficos": {
                "hh_por_semana": _grafico_hh_por_semana(semana_totais, capacidade_disponivel),
                "hh_por_disciplina": _grafico_pizza(df, "disciplina", "hh_previsto", "HH por Disciplina"),
                "hh_por_tipo": _grafico_pizza(df, "tipo_intervencao", "hh_previsto", "HH por Tipo de Intervenção"),
                "hh_por_equipamento": _grafico_barras_horizontal(df, "equipamento", "hh_previsto", "HH por Equipamento", top_n=10),
                "status_atividades": _grafico_donut(df, "status", "hh_previsto", "Status das Atividades"),
                "capacidade_utilizada": _grafico_area_utilizacao(semana_totais, capacidade_disponivel),
                "tendencia_execucao": _grafico_tendencia(acumulado_planejado, acumulado_realizado),
                "desvio_semanal": desvio_semanal,
            },
        }
    finally:
        session.close()


def _grafico_hh_por_semana(semana_totais: pd.Series, capacidade: float):
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=semana_totais.index,
            y=semana_totais.values,
            name="HH Planejado",
            marker_color="#38BDF8",
            marker_line_color="#1E293B",
            marker_line_width=0.4,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=semana_totais.index,
            y=[capacidade] * len(semana_totais),
            mode="lines",
            name="Capacidade Disponível",
            line=dict(color="#EF4444", dash="dash", width=3),
        )
    )
    fig.update_layout(xaxis_title="Semana", yaxis_title="HH")
    return _aplicar_layout(fig, "HH por Semana")


def _grafico_pizza(df: pd.DataFrame, campo: str, valor: str, titulo: str):
    if df.empty or df[campo].nunique() == 0:
        return _aplicar_layout(go.Figure(), titulo)
    agrupado = df.groupby(campo)[valor].sum().reset_index()
    fig = px.pie(agrupado, names=campo, values=valor, color_discrete_sequence=COLORWAY)
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    return _aplicar_layout(fig, titulo)


def _grafico_barras_horizontal(df: pd.DataFrame, campo: str, valor: str, titulo: str, top_n: int = 10):
    agrupado = df.groupby(campo)[valor].sum().nlargest(top_n).reset_index()
    fig = px.bar(agrupado, x=valor, y=campo, orientation="h", color_discrete_sequence=["#1E293B"])
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    fig.update_traces(marker_line_width=0, hovertemplate="%{y}<br>%{x:.1f} HH<extra></extra>")
    return _aplicar_layout(fig, titulo)


def _grafico_donut(df: pd.DataFrame, campo: str, valor: str, titulo: str):
    agrupado = df.groupby(campo)[valor].sum().reset_index()
    fig = px.pie(
        agrupado,
        names=campo,
        values=valor,
        hole=0.55,
        color=campo,
        color_discrete_map=STATUS_COLORS,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    return _aplicar_layout(fig, titulo)


def _grafico_area_utilizacao(semana_totais: pd.Series, capacidade: float):
    percentual = semana_totais / capacidade * 100 if capacidade else semana_totais * 0.0
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=semana_totais.index,
            y=percentual.values,
            fill='tozeroy',
            name="Capacidade Utilizada (%)",
            line=dict(color="#7C3AED", width=3),
            fillcolor="rgba(124,58,237,0.16)",
        )
    )
    fig.add_hline(y=100, line_color="#EF4444", line_dash="dash", annotation_text="Limite")
    fig.update_layout(xaxis_title="Semana", yaxis_title="% da Capacidade")
    return _aplicar_layout(fig, "Capacidade Utilizada por Semana")


def _grafico_tendencia(acumulado_planejado: pd.Series, acumulado_realizado: pd.Series):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=acumulado_planejado.index, y=acumulado_planejado.values, mode="lines+markers", name="Planejado", line=dict(color="#38BDF8", width=3)))
    fig.add_trace(go.Scatter(x=acumulado_realizado.index, y=acumulado_realizado.values, mode="lines+markers", name="Realizado", line=dict(color="#34D399", width=3)))
    fig.update_layout(xaxis_title="Semana", yaxis_title="HH Acumulado")
    return _aplicar_layout(fig, "Tendência de Execução")
