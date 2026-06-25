from datetime import date as _date

import streamlit as st

from componentes.ui import page_header, section
from database import SessionLocal
from models import Equipamento, Plano
from services.dashboard import calcular_indicadores
from services.relatorios_pdf import gerar_pdf_backlog, gerar_pdf_dashboard


ano_atual = _date.today().year
anos_disponiveis = list(range(ano_atual - 1, ano_atual + 6))


def _pct(valor: float) -> str:
    return f"{valor:.0%}"


def render():
    page_header(
        "Dashboard",
        "Visão executiva da carteira PCM: volume planejado, aderência, backlog, capacidade e tendência de execução.",
    )

    session = SessionLocal()
    try:
        disciplinas = [d[0] for d in session.query(Plano.disciplina).distinct().all() if d[0]]
        tipos = [t[0] for t in session.query(Plano.tipo_intervencao).distinct().all() if t[0]]
        areas = [a[0] for a in session.query(Equipamento.area).distinct().filter(Equipamento.area != None).all() if a[0]]
    finally:
        session.close()

    section("Filtros operacionais", "Use os filtros para avaliar disciplina, tipo de intervenção e área sem sair da visão geral.")
    f1, f2, f3, f4 = st.columns([1, 1.4, 1.4, 1.4])
    with f1:
        ano = st.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual))
    with f2:
        filtros = st.multiselect("Disciplina", disciplinas, placeholder="Selecione disciplinas")
    with f3:
        filtros_tipo = st.multiselect("Tipo de intervenção", tipos, placeholder="Selecione tipos")
    with f4:
        filtros_area = st.multiselect("Área", areas, placeholder="Selecione áreas")

    indicadores = calcular_indicadores(ano, filtros, filtros_tipo, filtros_area)
    kpis = indicadores["kpis"]
    absolutos = indicadores["absolutos"]

    pdf_col1, pdf_col2, _ = st.columns([1.2, 1.2, 3])
    try:
        pdf_col1.download_button(
            "Baixar Dashboard PDF",
            data=gerar_pdf_dashboard(ano, filtros, filtros_tipo, filtros_area),
            file_name=f"planejai_dashboard_{ano}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        pdf_col2.download_button(
            "Baixar Backlog PDF",
            data=gerar_pdf_backlog(ano),
            file_name=f"planejai_backlog_{ano}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except RuntimeError as exc:
        st.warning(str(exc))

    hh_atrasado = absolutos["hh_atrasado"]
    hh_planejado = absolutos["hh_planejado"]
    pct_backlog = (hh_atrasado / hh_planejado * 100) if hh_planejado else 0.0

    section("Saúde do plano")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Eficiência", _pct(kpis["eficiencia"]), help="HH realizado sobre HH planejado.")
    c2.metric("Aderência", _pct(kpis["aderencia"]), help="HH executado dentro da carteira planejada.")
    c3.metric("Backlog", f"{hh_atrasado:.1f} HH", delta=f"{pct_backlog:.1f}%", delta_color="inverse")
    c4.metric("Cancelamento", _pct(kpis["cancelamento"]))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("HH Planejado", f"{absolutos['hh_planejado']:.1f}")
    c6.metric("HH Executado", f"{absolutos['hh_executado']:.1f}")
    c7.metric("HH Reprogramado", f"{absolutos['hh_reprogramado']:.1f}")
    c8.metric("Atividades", f"{absolutos['total_atividades']}")

    section("Carga semanal e capacidade")
    st.plotly_chart(indicadores["graficos"]["hh_por_semana"], use_container_width=True)

    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(indicadores["graficos"]["capacidade_utilizada"], use_container_width=True)
    with g2:
        st.plotly_chart(indicadores["graficos"]["tendencia_execucao"], use_container_width=True)

    section("Composição da carteira")
    g3, g4 = st.columns(2)
    with g3:
        st.plotly_chart(indicadores["graficos"]["hh_por_disciplina"], use_container_width=True)
    with g4:
        st.plotly_chart(indicadores["graficos"]["hh_por_tipo"], use_container_width=True)

    g5, g6 = st.columns(2)
    with g5:
        st.plotly_chart(indicadores["graficos"]["status_atividades"], use_container_width=True)
    with g6:
        st.plotly_chart(indicadores["graficos"]["hh_por_equipamento"], use_container_width=True)

    st.info(f"Desvio padrão semanal: {indicadores['graficos']['desvio_semanal']:.2f} HH")
