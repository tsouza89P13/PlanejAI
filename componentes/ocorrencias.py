from datetime import date
from html import escape

import streamlit as st
from sqlalchemy.orm import joinedload

from componentes.ui import page_header, section, status_badge
from database import SessionLocal
from models import Equipamento, HistoricoAlteracao, Ocorrencia, Plano
from services.historico import registrar_historico
from services.relatorios_pdf import gerar_pdf_ocorrencias_semana
from services.status import status_ocorrencia


def render():
    page_header(
        "Execução de Ocorrências",
        "Fila operacional para realizar, reprogramar ou cancelar atividades geradas no plano anual.",
    )

    hoje = date.today()
    ano_atual = hoje.year
    semana_atual = hoje.isocalendar()[1]

    section("Filtros")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        anos_disponiveis = list(range(ano_atual - 1, ano_atual + 6))
        ano = st.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_atual), key="oc_filtro_ano")

    with col2:
        semana = st.selectbox("Semana", ["Todas"] + list(range(1, 53)), index=semana_atual, key="oc_filtro_semana")

    with col3:
        session_temp = SessionLocal()
        equipamentos = (
            session_temp.query(Equipamento)
            .filter(Equipamento.status == "Ativo")
            .order_by(Equipamento.codigo)
            .all()
        )
        session_temp.close()
        opcoes_equipamento = ["Todos"] + [f"{e.codigo} - {e.descricao}" for e in equipamentos]
        equipamento_selecionado = st.selectbox("Equipamento", opcoes_equipamento, index=0, key="oc_filtro_equipamento")

    session = SessionLocal()
    try:
        query = (
            session.query(Ocorrencia)
            .join(Plano, Ocorrencia.plano_id == Plano.id)
            .join(Equipamento, Plano.equipamento_id == Equipamento.id)
            .options(joinedload(Ocorrencia.plano).joinedload(Plano.equipamento))
            .filter(Ocorrencia.ano == ano)
        )

        if semana != "Todas":
            query = query.filter(Ocorrencia.semana == semana)

        if equipamento_selecionado != "Todos":
            codigo_eq = equipamento_selecionado.split(" - ")[0]
            query = query.filter(Equipamento.codigo == codigo_eq)
        else:
            codigo_eq = None

        ocorrencias = query.order_by(Ocorrencia.semana, Plano.nome).all()

        if not ocorrencias:
            st.info("Nenhuma ocorrência encontrada para os filtros selecionados.")
            return

        total = len(ocorrencias)
        por_status = {
            "Programado": 0,
            "Realizado": 0,
            "Atrasado": 0,
            "Reprogramado": 0,
            "Cancelado": 0,
        }
        hh_atrasado = 0.0

        for oc in ocorrencias:
            status_exibir = status_ocorrencia(oc.status, oc.ano, oc.semana, hoje)
            if status_exibir == "Atrasado":
                hh_atrasado += oc.hh_previsto or 0.0
            por_status[status_exibir] = por_status.get(status_exibir, 0) + 1

        pct_conclusao = round((por_status["Realizado"] / total * 100) if total else 0)

        section("Resumo da fila")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total", total)
        c2.metric("Realizadas", por_status["Realizado"])
        c3.metric("Programadas", por_status["Programado"])
        c4.metric("Atrasadas", por_status["Atrasado"], delta=f"{hh_atrasado:.1f} HH", delta_color="inverse")
        c5.metric("Canceladas", por_status["Cancelado"])

        st.progress(pct_conclusao / 100, text=f"Conclusão: {pct_conclusao}%")
        try:
            st.download_button(
                "Baixar ocorrências em PDF",
                data=gerar_pdf_ocorrencias_semana(ano, semana, equipamento_codigo=codigo_eq),
                file_name=f"planejai_ocorrencias_{ano}_s{semana}.pdf",
                mime="application/pdf",
            )
        except RuntimeError as exc:
            st.warning(str(exc))

        section("Ocorrências")

        for oc in ocorrencias:
            plano = oc.plano
            equipamento = plano.equipamento if plano else None
            status_visual = oc.status
            status_visual = status_ocorrencia(oc.status, oc.ano, oc.semana, hoje)

            with st.container(border=True):
                col_info, col_status, col_hh, col_acoes = st.columns([4, 1, 1, 2])

                with col_info:
                    st.markdown(
                        f"**{escape(plano.nome if plano else '-')}**  \n"
                        f"{escape(equipamento.codigo if equipamento else '-')} | "
                        f"Semana {oc.semana}/{ano} | "
                        f"{escape(plano.disciplina if plano else '-')}"
                    )

                with col_status:
                    st.markdown(status_badge(status_visual), unsafe_allow_html=True)

                with col_hh:
                    st.metric("HH", f"{oc.hh_previsto or 0:.1f}")

                with col_acoes:
                    b1, b2, b3 = st.columns(3)
                    if status_visual not in ("Realizado", "Cancelado"):
                        if b1.button("OK", key=f"realizar_{oc.id}", help="Marcar como realizado"):
                            st.session_state[f"oc_acao_{oc.id}"] = "realizar"
                            st.rerun()
                        if b2.button("Rep", key=f"reprog_{oc.id}", help="Reprogramar"):
                            st.session_state[f"oc_acao_{oc.id}"] = "reprogramar"
                            st.rerun()
                        if b3.button("Can", key=f"cancelar_{oc.id}", help="Cancelar"):
                            st.session_state[f"oc_acao_{oc.id}"] = "cancelar"
                            st.rerun()

                acao = st.session_state.get(f"oc_acao_{oc.id}")
                if acao == "realizar":
                    with st.form(key=f"form_realizar_{oc.id}"):
                        hh_real = st.number_input("HH realizado", min_value=0.0, step=0.5, value=oc.hh_previsto or 0.0)
                        data_real = st.date_input("Data de realização", value=hoje)
                        obs = st.text_area("Observação")
                        col_s, col_c = st.columns(2)
                        salvar = col_s.form_submit_button("Salvar", type="primary")
                        cancelar_form = col_c.form_submit_button("Cancelar")
                        if salvar:
                            registrar_historico(session, oc.id, "status", oc.status, "Realizado")
                            registrar_historico(session, oc.id, "hh_realizado", str(oc.hh_realizado or ''), str(hh_real))
                            registrar_historico(session, oc.id, "data_realizado", str(oc.data_realizado or ''), str(data_real))
                            oc.status = "Realizado"
                            oc.hh_realizado = hh_real
                            oc.data_realizado = data_real
                            oc.observacao = obs if obs else None
                            session.commit()
                            st.session_state.pop(f"oc_acao_{oc.id}", None)
                            st.success("Ocorrência realizada com sucesso.")
                            st.rerun()
                        if cancelar_form:
                            st.session_state.pop(f"oc_acao_{oc.id}", None)
                            st.rerun()

                elif acao == "reprogramar":
                    with st.form(key=f"form_reprog_{oc.id}"):
                        nova_semana = st.number_input("Nova semana", min_value=1, max_value=52, value=oc.semana)
                        motivo = st.text_area("Motivo da reprogramação")
                        col_s, col_c = st.columns(2)
                        salvar = col_s.form_submit_button("Salvar", type="primary")
                        cancelar_form = col_c.form_submit_button("Cancelar")
                        if salvar:
                            registrar_historico(session, oc.id, "status", oc.status, "Reprogramado")
                            registrar_historico(session, oc.id, "semana", str(oc.semana), str(nova_semana))
                            oc.status = "Reprogramado"
                            oc.semana = nova_semana
                            oc.observacao = motivo if motivo else None
                            session.commit()
                            st.session_state.pop(f"oc_acao_{oc.id}", None)
                            st.success("Ocorrência reprogramada com sucesso.")
                            st.rerun()
                        if cancelar_form:
                            st.session_state.pop(f"oc_acao_{oc.id}", None)
                            st.rerun()

                elif acao == "cancelar":
                    st.warning(f"Confirmar cancelamento de '{plano.nome if plano else 'ocorrência'}' na semana {oc.semana}?")
                    col_s, col_c = st.columns(2)
                    if col_s.button("Confirmar", key=f"conf_cancel_{oc.id}"):
                        registrar_historico(session, oc.id, "status", oc.status, "Cancelado")
                        oc.status = "Cancelado"
                        session.commit()
                        st.session_state.pop(f"oc_acao_{oc.id}", None)
                        st.success("Ocorrência cancelada.")
                        st.rerun()
                    if col_c.button("Voltar", key=f"volta_cancel_{oc.id}"):
                        st.session_state.pop(f"oc_acao_{oc.id}", None)
                        st.rerun()

                historicos = session.query(HistoricoAlteracao).filter(HistoricoAlteracao.ocorrencia_id == oc.id).order_by(HistoricoAlteracao.alterado_em.desc()).all()
                with st.expander(f"Histórico ({len(historicos)})"):
                    if historicos:
                        for h in historicos:
                            st.markdown(
                                f"**{h.alterado_em.strftime('%d/%m/%Y %H:%M')}** "
                                f"| {escape(h.campo or '-')} : `{escape(h.valor_anterior or '')}` -> `{escape(h.valor_novo or '')}`"
                            )
                    else:
                        st.info("Sem histórico para esta ocorrência.")

    finally:
        session.close()
