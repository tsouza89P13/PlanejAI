import streamlit as st

from componentes.ui import page_header, section, status_badge
from database import SessionLocal
from models import Equipamento


def _resetar_form():
    st.session_state["eq_form_count"] += 1
    st.rerun()


def _editar_equipamento(equipamento_id: int) -> None:
    st.session_state["equipamento_edit_id"] = equipamento_id
    st.session_state["eq_form_count"] += 1


def _remover_equipamento(equipamento_id: int) -> None:
    st.session_state["equipamento_delete_id"] = equipamento_id


def render():
    page_header(
        "Equipamentos",
        "Base de ativos usada para vincular planos, calcular capacidade e organizar a carteira por área.",
    )

    defaults = {
        "eq_form_count": 0,
        "equipamento_edit_id": None,
        "equipamento_delete_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    session = SessionLocal()
    try:
        if st.session_state["equipamento_delete_id"]:
            equipamento_remover = session.get(Equipamento, st.session_state["equipamento_delete_id"])
            if equipamento_remover:
                total_planos = len(equipamento_remover.planos)
                st.error(
                    f"Confirmar remoção do equipamento: {equipamento_remover.codigo} - {equipamento_remover.descricao}. "
                    f"Existem {total_planos} plano(s) vinculado(s) a este equipamento. "
                    "Ao confirmar, todos os planos vinculados e seus registros de ocorrências também serão apagados."
                )
                entendeu = st.checkbox(
                    "Entendo que os planos vinculados e seus registros serão apagados junto com o equipamento.",
                    key=f"entende_delete_equipamento_{equipamento_remover.id}",
                )
                confirmar_col, cancelar_col = st.columns([1, 5])
                if confirmar_col.button(
                    "Confirmar remoção",
                    key="confirm_delete_equipamento_top",
                    type="primary",
                    disabled=not entendeu,
                ):
                    try:
                        session.delete(equipamento_remover)
                        session.commit()
                        st.success("Equipamento removido com sucesso.")
                        st.session_state["equipamento_delete_id"] = None
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao remover equipamento: {str(e)}")
                if cancelar_col.button("Cancelar", key="cancel_delete_equipamento_top"):
                    st.session_state["equipamento_delete_id"] = None
                    st.rerun()

        equipamento_selecionado = session.get(Equipamento, st.session_state["equipamento_edit_id"]) if st.session_state["equipamento_edit_id"] else None

        with st.expander("Cadastrar ou editar equipamento", expanded=True):
            with st.form("form_equipamento", clear_on_submit=False):
                count = st.session_state["eq_form_count"]
                col_a, col_b = st.columns(2)
                with col_a:
                    codigo = st.text_input("Código", value=equipamento_selecionado.codigo if equipamento_selecionado else "", max_chars=50, key=f"eq_codigo_{count}")
                    descricao = st.text_input("Descrição", value=equipamento_selecionado.descricao if equipamento_selecionado else "", key=f"eq_descricao_{count}")
                    local = st.text_input("Local", value=equipamento_selecionado.local if equipamento_selecionado else "", key=f"eq_local_{count}")
                with col_b:
                    area = st.text_input("Área", value=equipamento_selecionado.area if equipamento_selecionado else "", key=f"eq_area_{count}")
                    criticidade = st.selectbox(
                        "Criticidade",
                        ["Alta", "Média", "Baixa"],
                        index=["Alta", "Média", "Baixa"].index(equipamento_selecionado.criticidade) if equipamento_selecionado and equipamento_selecionado.criticidade in ["Alta", "Média", "Baixa"] else 0,
                        key=f"eq_criticidade_{count}",
                    )
                    status = st.selectbox(
                        "Status",
                        ["Ativo", "Inativo"],
                        index=["Ativo", "Inativo"].index(equipamento_selecionado.status) if equipamento_selecionado and equipamento_selecionado.status in ["Ativo", "Inativo"] else 0,
                        key=f"eq_status_{count}",
                    )

                if st.form_submit_button("Salvar equipamento", type="primary"):
                    codigo_limpo = codigo.strip() if codigo else ""
                    descricao_limpa = descricao.strip() if descricao else ""
                    if not codigo_limpo or not descricao_limpa:
                        st.warning("Código e descrição são obrigatórios.")
                    else:
                        duplicado = session.query(Equipamento).filter(Equipamento.codigo == codigo_limpo).first()
                        if duplicado and (not equipamento_selecionado or duplicado.id != equipamento_selecionado.id):
                            st.error("Já existe um equipamento cadastrado com este código.")
                            return

                        equipamento = equipamento_selecionado or Equipamento()
                        equipamento.codigo = codigo_limpo
                        equipamento.descricao = descricao_limpa
                        equipamento.local = local.strip() if local else None
                        equipamento.area = area.strip() if area else None
                        equipamento.criticidade = criticidade
                        equipamento.status = status
                        session.add(equipamento)
                        try:
                            session.commit()
                            st.success("Equipamento salvo com sucesso.")
                            st.session_state["equipamento_edit_id"] = None
                            _resetar_form()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Erro ao salvar: {str(e)}")

        section("Registros cadastrados")
        equipamentos = session.query(Equipamento).order_by(Equipamento.codigo).all()
        if equipamentos:
            header = st.columns([1.2, 2.2, 1.3, 1.2, 1, 1, 1.8])
            for col, label in zip(header, ["Código", "Descrição", "Local", "Área", "Criticidade", "Status", "Ações"]):
                col.markdown(f"**{label}**")

            for equipamento in equipamentos:
                cols = st.columns([1.2, 2.2, 1.3, 1.2, 1, 1, 1.8])
                cols[0].write(equipamento.codigo or "-")
                cols[1].write(equipamento.descricao or "-")
                cols[2].write(equipamento.local or "-")
                cols[3].write(equipamento.area or "-")
                cols[4].markdown(status_badge(equipamento.criticidade or "-"), unsafe_allow_html=True)
                cols[5].markdown(status_badge(equipamento.status or "-"), unsafe_allow_html=True)
                with cols[6]:
                    a1, a2 = st.columns(2)
                    a1.button("Editar", key=f"edit_equip_{equipamento.id}", on_click=_editar_equipamento, args=(equipamento.id,))
                    a2.button("Remover", key=f"delete_equip_{equipamento.id}", on_click=_remover_equipamento, args=(equipamento.id,))
        else:
            st.info("Nenhum equipamento cadastrado ainda.")

    finally:
        session.close()
