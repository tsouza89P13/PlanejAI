from datetime import date, timedelta
from html import escape

import streamlit as st

from componentes.ui import page_header, section, status_badge
from database import SessionLocal
from models import RestricaoCalendario


TIPOS = ["Feriado", "Grande Parada", "Férias", "Evento"]


def _resetar_form():
    st.session_state["cal_form_count"] += 1
    st.rerun()


def _editar_restricao(restricao_id: int) -> None:
    st.session_state["restricao_edit_id"] = restricao_id
    st.session_state["cal_form_count"] += 1


def _remover_restricao(restricao_id: int) -> None:
    st.session_state["restricao_delete_id"] = restricao_id


def _semanas_afetadas(data_inicio: date, data_fim: date) -> list[int]:
    semanas = set()
    data_atual = data_inicio
    while data_atual <= data_fim:
        semanas.add(data_atual.isocalendar()[1])
        data_atual += timedelta(days=1)
    return sorted(semanas)


def render():
    page_header(
        "Calendário de Restrição",
        "Bloqueios, feriados, grandes paradas e eventos que impactam a distribuição do plano anual.",
    )

    defaults = {
        "cal_form_count": 0,
        "restricao_edit_id": None,
        "restricao_delete_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    session = SessionLocal()
    try:
        if st.session_state["restricao_delete_id"]:
            restricao_remover = session.get(RestricaoCalendario, st.session_state["restricao_delete_id"])
            if restricao_remover:
                st.error(
                    "Confirmar remoção da restrição: "
                    f"{restricao_remover.data_inicio.strftime('%d/%m/%Y')} a "
                    f"{restricao_remover.data_fim.strftime('%d/%m/%Y')} | {restricao_remover.tipo}"
                )
                confirmar_col, cancelar_col = st.columns([1, 5])
                if confirmar_col.button("Confirmar remoção", key="confirm_delete_restricao_top", type="primary"):
                    try:
                        session.delete(restricao_remover)
                        session.commit()
                        st.success("Restrição removida com sucesso.")
                        st.session_state["restricao_delete_id"] = None
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao remover restrição: {str(e)}")
                if cancelar_col.button("Cancelar", key="cancel_delete_restricao_top"):
                    st.session_state["restricao_delete_id"] = None
                    st.rerun()

        restricao_selecionada = None
        if st.session_state["restricao_edit_id"]:
            restricao_selecionada = session.get(RestricaoCalendario, st.session_state["restricao_edit_id"])

        with st.expander("Cadastrar ou editar restrição", expanded=True):
            with st.form("form_restricao", clear_on_submit=False):
                count = st.session_state["cal_form_count"]
                col_a, col_b = st.columns(2)
                with col_a:
                    data_inicio = st.date_input(
                        "Data início",
                        value=restricao_selecionada.data_inicio if restricao_selecionada else date.today(),
                        key=f"cal_data_inicio_{count}",
                    )
                    data_fim = st.date_input(
                        "Data fim",
                        value=restricao_selecionada.data_fim if restricao_selecionada else data_inicio,
                        key=f"cal_data_fim_{count}",
                    )
                with col_b:
                    tipo = st.selectbox(
                        "Tipo",
                        TIPOS,
                        index=TIPOS.index(restricao_selecionada.tipo)
                        if restricao_selecionada and restricao_selecionada.tipo in TIPOS
                        else 0,
                        key=f"cal_tipo_{count}",
                    )
                    bloqueia_execucao = st.checkbox(
                        "Bloqueia execução",
                        value=restricao_selecionada.bloqueia_execucao if restricao_selecionada else False,
                        key=f"cal_bloqueia_{count}",
                    )
                descricao = st.text_input(
                    "Descrição",
                    value=restricao_selecionada.descricao if restricao_selecionada else "",
                    key=f"cal_descricao_{count}",
                )
                submitted = st.form_submit_button("Salvar restrição", type="primary")

                if submitted:
                    if data_fim < data_inicio:
                        st.warning("A data fim não pode ser anterior à data início.")
                    else:
                        restricao = restricao_selecionada or RestricaoCalendario()
                        restricao.data_inicio = data_inicio
                        restricao.data_fim = data_fim
                        restricao.tipo = tipo
                        restricao.descricao = descricao.strip() if descricao else None
                        restricao.bloqueia_execucao = bloqueia_execucao
                        session.add(restricao)

                        try:
                            session.commit()
                            st.success("Restrição salva com sucesso.")
                            st.session_state["restricao_edit_id"] = None
                            _resetar_form()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Erro ao salvar: {str(e)}")

        section("Registros cadastrados")
        restricoes = (
            session.query(RestricaoCalendario)
            .order_by(RestricaoCalendario.ano, RestricaoCalendario.data_inicio)
            .all()
        )
        if restricoes:
            header = st.columns([0.7, 1, 1, 1.1, 2, 1.3, 1, 1.8])
            for col, label in zip(
                header,
                ["Ano", "Início", "Fim", "Tipo", "Descrição", "Semanas", "Execução", "Ações"],
            ):
                col.markdown(f"**{label}**")

            for restricao in restricoes:
                semanas = _semanas_afetadas(restricao.data_inicio, restricao.data_fim)
                cols = st.columns([0.7, 1, 1, 1.1, 2, 1.3, 1, 1.8])
                cols[0].write(str(restricao.ano or "-"))
                cols[1].write(restricao.data_inicio.strftime("%d/%m/%Y"))
                cols[2].write(restricao.data_fim.strftime("%d/%m/%Y"))
                cols[3].write(restricao.tipo or "-")
                cols[4].write(escape(restricao.descricao or "-"))
                cols[5].write(", ".join(f"S{s}" for s in semanas))
                cols[6].markdown(
                    status_badge(
                        "Bloqueia" if restricao.bloqueia_execucao else "Livre",
                        "Atrasado" if restricao.bloqueia_execucao else "Realizado",
                    ),
                    unsafe_allow_html=True,
                )
                with cols[7]:
                    a1, a2 = st.columns(2)
                    a1.button("Editar", key=f"edit_restr_{restricao.id}", on_click=_editar_restricao, args=(restricao.id,))
                    a2.button("Remover", key=f"delete_restr_{restricao.id}", on_click=_remover_restricao, args=(restricao.id,))
        else:
            st.info("Nenhuma restrição cadastrada ainda.")
    finally:
        session.close()
