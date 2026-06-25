from datetime import date as _date
from html import escape
from typing import Dict, List

import streamlit as st

from componentes.ui import mini_badge, page_header, section
from database import SessionLocal
from models import Equipamento, Ocorrencia, Plano
from services.planejamento import gerar_plano_anual
from services.relatorios_pdf import gerar_pdf_mapa_52w
from services.status import status_ocorrencia


STATUS_CORES = {
    "Programado": "#38BDF8",
    "Realizado": "#34D399",
    "Reprogramado": "#D97706",
    "Cancelado": "#94A3B8",
    "Atrasado": "#EF4444",
}

STATUS_NOMES = {
    "Programado": "Prog",
    "Realizado": "Real",
    "Reprogramado": "Repr",
    "Cancelado": "Canc",
    "Atrasado": "Atr",
}

FREQUENCIA_CORES = {
    "Diaria": "#38BDF8",
    "Diária": "#38BDF8",
    "Semanal": "#38BDF8",
    "Quinzenal": "#38BDF8",
    "Mensal": "#34D399",
    "Bimestral": "#34D399",
    "Trimestral": "#7C3AED",
    "Quadrimestral": "#7C3AED",
    "Semestral": "#D97706",
    "Anual": "#D97706",
}


def _normalizar(texto: str | None) -> str:
    if not texto:
        return "-"
    return texto


def _criar_badge(status: str) -> str:
    cor = STATUS_CORES.get(status, "#64748B")
    texto_badge = STATUS_NOMES.get(status, status[:3])
    return mini_badge(texto_badge, cor)


def _frequencia_badge(frequencia: str | None) -> str:
    freq = _normalizar(frequencia)
    cor = FREQUENCIA_CORES.get(freq, "#64748B")
    return mini_badge(freq, cor)


def _montar_tabela(planos: List[Plano], ocorrencias_por_plano: Dict[int, List[Ocorrencia]], ano: int) -> str:
    cabecalho = "<tr><th class='plan-col'>Plano</th>"
    for semana in range(1, 53):
        cabecalho += f"<th class='week-col'>S{semana}</th>"
    cabecalho += "</tr>"

    linhas = [cabecalho]

    for plano in planos:
        equipamento = plano.equipamento
        equipamento_txt = ""
        if equipamento:
            equipamento_txt = f"{escape(equipamento.codigo or '')} - {escape(equipamento.descricao or '')}"

        linha = (
            "<tr>"
            "<td class='plan-cell'>"
            f"<div class='plan-name'>{escape(plano.nome or '')}</div>"
            f"<div class='equipment-name'>{equipamento_txt}</div>"
            "<div class='plan-meta'>"
            f"{_frequencia_badge(plano.frequencia)}"
            f"<span>{escape(_normalizar(plano.disciplina))}</span>"
            f"<span>{plano.duracao_hh or 0:.1f} HH</span>"
            "</div>"
            "</td>"
        )

        ocorrencias = ocorrencias_por_plano.get(plano.id, [])
        mapa = {oc.semana: oc for oc in ocorrencias}

        for semana in range(1, 53):
            celula = ""
            classe = "week-cell"
            if semana in mapa:
                status = status_ocorrencia(mapa[semana].status, ano, mapa[semana].semana)
                celula = _criar_badge(status)
                classe += f" status-{status.lower()}"
            linha += f"<td class='{classe}'>{celula}</td>"

        linha += "</tr>"
        linhas.append(linha)

    tabela = (
        "<style>"
        ".mapa-wrap { overflow:auto; max-height:680px; border:1px solid #D8E0EA; border-radius:8px; background:#fff; box-shadow:0 8px 24px rgba(15,23,42,.05); }"
        ".mapa-table { border-collapse:separate; border-spacing:0; width:100%; font-family:Inter, Segoe UI, sans-serif; font-size:13px; }"
        ".mapa-table th { position:sticky; top:0; z-index:8; background:#1E293B; color:#F8FAFC !important; font-weight:800; border-bottom:1px solid rgba(255,255,255,.12); }"
        ".mapa-table th * { color:#F8FAFC !important; }"
        ".mapa-table td { border-bottom:1px solid #EDF1F6; border-right:1px solid #EDF1F6; }"
        ".mapa-table tr:nth-child(even) .week-cell, .mapa-table tr:nth-child(even) .plan-cell { background:#F8FAFC; }"
        ".plan-col { left:0; z-index:12 !important; min-width:360px; max-width:430px; text-align:left; padding:11px 14px; box-shadow:5px 0 12px rgba(15,23,42,0.12); }"
        ".week-col { min-width:48px; height:40px; text-align:center; padding:0 6px; color:#FFFFFF !important; font-size:13px; font-weight:950; text-transform:uppercase; letter-spacing:.04em; }"
        ".week-col, .week-col * { color:#FFFFFF !important; }"
        ".plan-cell { position:sticky; left:0; z-index:5; min-width:360px; max-width:430px; padding:12px 14px; background:#fff; box-shadow:5px 0 12px rgba(15,23,42,0.06); vertical-align:top; }"
        ".plan-name { color:#172033; font-weight:800; line-height:1.25; white-space:normal; }"
        ".equipment-name { color:#64748B; font-size:12px; margin-top:4px; line-height:1.25; white-space:normal; }"
        ".plan-meta { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }"
        ".plan-meta span:not(.pcm-pill) { background:#E8EEF6; color:#344054; border:1px solid #D8E0EA; border-radius:999px; padding:3px 9px; font-size:11px; line-height:1.3; font-weight:700; }"
        ".week-cell { min-width:42px; height:44px; text-align:center; padding:5px; background:#fff; }"
        ".week-cell .pcm-pill { min-width:32px; justify-content:center; padding:3px 6px; font-size:10px; }"
        "</style>"
        "<div class='mapa-wrap'>"
        "<table class='mapa-table'>"
        + "".join(linhas)
        + "</table>"
        "</div>"
    )
    return tabela


def render():
    page_header(
        "Mapa de 52 Semanas",
        "Grade anual para visualizar distribuição, status e concentração de manutenções por semana.",
    )

    legenda = " ".join(_criar_badge(status) + f" {STATUS_NOMES[status]}" for status in STATUS_NOMES)
    st.markdown(f"<div class='pcm-section'><strong>Legenda:</strong> {legenda}</div>", unsafe_allow_html=True)

    ano_atual = _date.today().year
    anos_disponiveis = list(range(ano_atual - 1, ano_atual + 6))

    section("Geracao e filtros")
    col_ano, col_gerar = st.columns([1, 2])

    with col_ano:
        ano = st.selectbox(
            "Ano",
            anos_disponiveis,
            index=anos_disponiveis.index(ano_atual)
        )

    with col_gerar:
        session = SessionLocal()
        try:
            total_existente = (
                session.query(Ocorrencia)
                .filter(Ocorrencia.ano == ano)
                .count()
            )
        finally:
            session.close()

        if total_existente > 0:
            st.warning(
                f"Já existe um plano gerado para {ano} com {total_existente} ocorrências. "
                "Gerar novamente substitui o plano atual."
            )
            gerar = st.button("Regerar plano anual", type="primary", key="btn_confirmar_gerar")
        else:
            gerar = st.button("Gerar plano anual", type="primary", key="btn_gerar_plano")

    if gerar:
        with st.spinner("Gerando plano anual com distribuição inteligente..."):
            resultado = gerar_plano_anual(ano)
            if resultado.get("erro"):
                st.error(resultado["erro"])
                return
            ocorrencias = resultado.get("ocorrencias_geradas", 0)
            st.success(
                f"Plano {ano} gerado com {ocorrencias} ocorrências respeitando espaçamento mínimo e restrições."
            )
            st.rerun()

    session = SessionLocal()
    try:
        equipamentos = (
            session.query(Equipamento)
            .order_by(Equipamento.codigo)
            .all()
        )
        equipamento_options = ["Todos"] + [
            f"{equipamento.codigo} - {equipamento.descricao}"
            for equipamento in equipamentos
        ]
        disciplinas = [
            d[0]
            for d in session.query(Plano.disciplina)
            .filter(Plano.disciplina != None)
            .distinct()
            .order_by(Plano.disciplina)
            .all()
            if d[0]
        ]

        filtro_col1, filtro_col2 = st.columns(2)
        equipamento_filtro = filtro_col1.selectbox(
            "Filtrar por equipamento",
            equipamento_options,
            index=0,
            key="mapa_filtro_equipamento",
        )
        disciplina_filtro = filtro_col2.selectbox(
            "Filtrar por disciplina",
            ["Todas"] + disciplinas,
            index=0,
            key="mapa_filtro_disciplina",
        )
        equipamento_codigo_pdf = None
        if equipamento_filtro != "Todos":
            equipamento_codigo_pdf = equipamento_filtro.split(" - ", 1)[0]
        try:
            st.download_button(
                "Baixar Mapa 52 Semanas PDF",
                data=gerar_pdf_mapa_52w(
                    ano,
                    equipamento_codigo=equipamento_codigo_pdf,
                    disciplina=disciplina_filtro,
                ),
                file_name=f"planejai_mapa_52s_{ano}.pdf",
                mime="application/pdf",
            )
        except RuntimeError as exc:
            st.warning(str(exc))

        query_planos = session.query(Plano).filter(Plano.status == "Ativo")
        if equipamento_filtro != "Todos":
            codigo_equipamento = equipamento_filtro.split(" - ", 1)[0]
            query_planos = (
                query_planos
                .join(Equipamento, Plano.equipamento_id == Equipamento.id)
                .filter(Equipamento.codigo == codigo_equipamento)
            )
        if disciplina_filtro != "Todas":
            query_planos = query_planos.filter(Plano.disciplina == disciplina_filtro)

        planos = query_planos.order_by(Plano.nome).all()
        plano_ids = [plano.id for plano in planos]

        query_ocorrencias = session.query(Ocorrencia).filter(Ocorrencia.ano == ano)
        if plano_ids:
            query_ocorrencias = query_ocorrencias.filter(Ocorrencia.plano_id.in_(plano_ids))
        else:
            query_ocorrencias = query_ocorrencias.filter(False)
        ocorrencias = query_ocorrencias.all()

        ocorrencias_por_plano = {}
        for oc in ocorrencias:
            ocorrencias_por_plano.setdefault(oc.plano_id, []).append(oc)

        if planos:
            total_ocs = sum(len(ocs) for ocs in ocorrencias_por_plano.values())
            realizadas = sum(1 for oc in ocorrencias if oc.status == "Realizado")
            atrasadas = sum(1 for oc in ocorrencias if status_ocorrencia(oc.status, oc.ano, oc.semana) == "Atrasado")

            col1, col2, col3 = st.columns(3)
            col1.metric("Ocorrências", total_ocs)
            col2.metric("Realizadas", realizadas)
            col3.metric("Atrasadas", atrasadas, delta_color="inverse")

            section("Distribuicao anual")
            st.markdown(_montar_tabela(planos, ocorrencias_por_plano, ano), unsafe_allow_html=True)
        else:
            st.info("Nenhum plano ativo encontrado. Cadastre planos na página de Planos de Manutenção.")
    finally:
        session.close()
