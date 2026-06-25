from datetime import date as _date
from html import escape

import streamlit as st

from componentes.ui import html_table, page_header, section, status_badge
from database import SessionLocal
from models import CapacidadeEquipe
from services.capacidade import calcular_dimensionamento, capacidade_disponivel_por_disciplina, hh_necessario_por_disciplina


ano_atual = _date.today().year
anos_disponiveis = list(range(ano_atual - 1, ano_atual + 6))
DISCIPLINAS = ["Mecânica", "Elétrica", "Lubrificação"]


def _resetar_form():
    st.session_state["cap_form_count"] += 1
    st.rerun()


def _editar_capacidade(registro_id: int) -> None:
    st.session_state["capacidade_edit_id"] = registro_id
    st.session_state["cap_form_count"] += 1


def _remover_capacidade(registro_id: int) -> None:
    st.session_state["capacidade_delete_id"] = registro_id


def render():
    page_header(
        "Capacidade das Equipes",
        "Dimensionamento semanal por disciplina para comparar demanda planejada, disponibilidade e necessidade de equipe.",
    )

    defaults = {
        "cap_form_count": 0,
        "capacidade_edit_id": None,
        "capacidade_delete_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    session = SessionLocal()
    try:
        if st.session_state["capacidade_delete_id"]:
            registro_remover = session.get(CapacidadeEquipe, st.session_state["capacidade_delete_id"])
            if registro_remover:
                st.error(f"Confirmar remoção da capacidade: {registro_remover.disciplina} - {registro_remover.ano}")
                confirmar_col, cancelar_col = st.columns([1, 5])
                if confirmar_col.button("Confirmar remoção", key="confirm_delete_capacidade_top", type="primary"):
                    try:
                        session.delete(registro_remover)
                        session.commit()
                        st.success("Registro de capacidade removido com sucesso.")
                        st.session_state["capacidade_delete_id"] = None
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao remover registro: {str(e)}")
                if cancelar_col.button("Cancelar", key="cancel_delete_capacidade_top"):
                    st.session_state["capacidade_delete_id"] = None
                    st.rerun()

        ano = st.selectbox(
            "Ano de referência",
            anos_disponiveis,
            index=anos_disponiveis.index(ano_atual) if ano_atual in anos_disponiveis else 1,
            key="cap_ano_select",
        )

        capacidade_selecionada = session.get(CapacidadeEquipe, st.session_state["capacidade_edit_id"]) if st.session_state["capacidade_edit_id"] else None

        with st.expander("Cadastrar capacidade de equipe", expanded=True):
            with st.form("form_capacidade", clear_on_submit=False):
                count = st.session_state["cap_form_count"]
                col_a, col_b, col_c = st.columns(3)
                disciplina = col_a.selectbox(
                    "Disciplina",
                    DISCIPLINAS,
                    index=DISCIPLINAS.index(capacidade_selecionada.disciplina) if capacidade_selecionada and capacidade_selecionada.disciplina in DISCIPLINAS else 0,
                    key=f"cap_disciplina_{count}",
                )
                num_colaboradores = col_b.number_input(
                    "Colaboradores",
                    min_value=1,
                    value=capacidade_selecionada.num_colaboradores if capacidade_selecionada else 1,
                    key=f"cap_colaboradores_{count}",
                )
                eficiencia = col_c.slider(
                    "Eficiência",
                    min_value=0.1,
                    max_value=1.0,
                    value=capacidade_selecionada.eficiencia if capacidade_selecionada else 0.7,
                    step=0.05,
                    key=f"cap_eficiencia_{count}",
                )

                if st.form_submit_button("Salvar capacidade", type="primary"):
                    registro_existente = (
                        session.query(CapacidadeEquipe)
                        .filter(CapacidadeEquipe.ano == ano, CapacidadeEquipe.disciplina == disciplina)
                        .first()
                    )
                    if capacidade_selecionada and registro_existente and registro_existente.id != capacidade_selecionada.id:
                        st.error("Já existe capacidade cadastrada para esta disciplina e ano.")
                        return

                    registro = capacidade_selecionada or registro_existente
                    if not registro:
                        registro = CapacidadeEquipe()
                    registro.ano = ano
                    registro.disciplina = disciplina
                    registro.num_colaboradores = num_colaboradores
                    registro.eficiencia = eficiencia
                    session.add(registro)
                    try:
                        session.commit()
                        st.success("Capacidade salva com sucesso.")
                        st.session_state["capacidade_edit_id"] = None
                        _resetar_form()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao salvar: {str(e)}")

        section("Análise de capacidade")
        hh_necessario = hh_necessario_por_disciplina(ano)
        hh_disponivel = capacidade_disponivel_por_disciplina(ano)
        rows = []
        for disciplina in DISCIPLINAS:
            necessario = hh_necessario.get(disciplina, 0.0)
            disponivel = hh_disponivel.get(disciplina, 0.0)
            registro = session.query(CapacidadeEquipe).filter(CapacidadeEquipe.ano == ano, CapacidadeEquipe.disciplina == disciplina).order_by(CapacidadeEquipe.id.desc()).first()
            eficiencia = registro.eficiencia if registro else 0.0
            colaboradores = registro.num_colaboradores if registro else 0
            sugestao = calcular_dimensionamento(necessario, eficiencia) if eficiencia else 0
            situacao_ok = colaboradores >= sugestao and disponivel >= necessario
            rows.append(
                [
                    escape(disciplina),
                    f"{necessario:.1f}",
                    f"{disponivel:.1f}",
                    str(colaboradores),
                    f"{eficiencia * 100:.0f}%" if eficiencia else "-",
                    str(sugestao),
                    status_badge("OK" if situacao_ok else "Atenção", "OK" if situacao_ok else "Atenção"),
                ]
            )

        st.markdown(
            html_table(
                ["Disciplina", "HH Necessário/sem", "HH Disponível/sem", "Colaboradores", "Eficiência", "Sugestão", "Situação"],
                rows,
            ),
            unsafe_allow_html=True,
        )

        section("Capacidades registradas")
        registros = session.query(CapacidadeEquipe).filter(CapacidadeEquipe.ano == ano).order_by(CapacidadeEquipe.disciplina).all()
        if registros:
            header = st.columns([2, 1.2, 1.2, 1, 1.8])
            for col, label in zip(header, ["Disciplina", "Colaboradores", "Eficiência", "Ano", "Ações"]):
                col.markdown(f"**{label}**")

            for registro in registros:
                cols = st.columns([2, 1.2, 1.2, 1, 1.8])
                cols[0].write(registro.disciplina or "-")
                cols[1].write(registro.num_colaboradores)
                cols[2].write(f"{registro.eficiencia:.0%}")
                cols[3].write(registro.ano)
                with cols[4]:
                    a1, a2 = st.columns(2)
                    a1.button("Editar", key=f"edit_capacidade_{registro.id}", on_click=_editar_capacidade, args=(registro.id,))
                    a2.button("Remover", key=f"delete_capacidade_{registro.id}", on_click=_remover_capacidade, args=(registro.id,))
        else:
            st.info("Nenhuma capacidade registrada para o ano selecionado.")

    finally:
        session.close()
