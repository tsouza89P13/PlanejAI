import streamlit as st

from componentes.ui import page_header, section, status_badge
from database import SessionLocal
from models import Equipamento, Plano


TIPOS_INTERVENCAO = ["Inspeção", "Preventiva", "Preditiva"]
DISCIPLINAS = ["Mecânica", "Elétrica", "Lubrificação"]
FREQUENCIAS = ["Diária", "Semanal", "Quinzenal", "Mensal", "Bimestral", "Trimestral", "Quadrimestral", "Semestral", "Anual"]


def _resetar_form_plano():
    st.session_state["pl_modo"] = "novo"
    st.session_state["pl_dados_clone"] = None
    st.session_state["pl_form_count"] += 1
    st.rerun()


def _valor_opcao(valor: str | None, opcoes: list[str], padrao: str) -> int:
    return opcoes.index(valor) if valor in opcoes else opcoes.index(padrao)


def _clonar_plano(dados: dict) -> None:
    st.session_state["pl_modo"] = "clonar"
    st.session_state["pl_dados_clone"] = dados
    st.session_state["plano_edit_id"] = None
    st.session_state["pl_form_count"] += 1


def _editar_plano(plano_id: int) -> None:
    st.session_state["pl_modo"] = "editar"
    st.session_state["plano_edit_id"] = plano_id
    st.session_state["pl_form_count"] += 1


def _remover_plano(plano_id: int) -> None:
    st.session_state["plano_delete_id"] = plano_id


def render():
    page_header(
        "Planos de Manutenção",
        "Cadastro da carteira preventiva com frequência, disciplina, HH, prioridade e janela de execução.",
    )

    defaults = {
        "pl_form_count": 0,
        "plano_edit_id": None,
        "plano_delete_id": None,
        "pl_modo": "novo",
        "pl_dados_clone": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    session = SessionLocal()
    try:
        if st.session_state["plano_delete_id"]:
            plano_remover = session.get(Plano, st.session_state["plano_delete_id"])
            if plano_remover:
                st.error(f"Confirmar remoção do plano: {plano_remover.nome}")
                confirmar_col, cancelar_col = st.columns([1, 5])
                if confirmar_col.button("Confirmar remoção", key="confirm_delete_plano_top", type="primary"):
                    try:
                        session.delete(plano_remover)
                        session.commit()
                        st.success("Plano removido com sucesso.")
                        st.session_state["plano_delete_id"] = None
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao remover plano: {str(e)}")
                if cancelar_col.button("Cancelar", key="cancel_delete_plano_top"):
                    st.session_state["plano_delete_id"] = None
                    st.rerun()

        equipamentos = session.query(Equipamento).filter(Equipamento.status == "Ativo").order_by(Equipamento.codigo).all()
        equipamento_options = {f"{eq.codigo} - {eq.descricao}": eq.id for eq in equipamentos}

        plano_selecionado = session.get(Plano, st.session_state["plano_edit_id"]) if st.session_state["plano_edit_id"] else None
        modo = st.session_state.get("pl_modo", "novo")
        clone = st.session_state.get("pl_dados_clone", {}) or {}
        count = st.session_state["pl_form_count"]
        titulo = "Clonar plano" if modo == "clonar" else "Editar plano" if modo == "editar" else "Cadastrar novo plano"

        with st.expander(titulo, expanded=True):
            with st.form("form_plano", clear_on_submit=False):
                equipamento_choices = ["Selecione"] + list(equipamento_options.keys())
                selected_index = 0
                if plano_selecionado and plano_selecionado.equipamento:
                    selecionado = f"{plano_selecionado.equipamento.codigo} - {plano_selecionado.equipamento.descricao}"
                    if selecionado not in equipamento_choices:
                        equipamento_choices.append(selecionado)
                        equipamento_options[selecionado] = plano_selecionado.equipamento.id
                    selected_index = equipamento_choices.index(selecionado)

                col_a, col_b = st.columns(2)
                with col_a:
                    equipamento_selecionado = st.selectbox("Equipamento", equipamento_choices, index=0 if modo == "clonar" else selected_index, key=f"pl_equipamento_{count}")
                    nome = st.text_input("Nome do plano", value=clone.get("nome", "") if modo == "clonar" else (plano_selecionado.nome if plano_selecionado else ""), key=f"pl_nome_{count}")
                    descricao = st.text_area("Descrição", value=clone.get("descricao", "") if modo == "clonar" else (plano_selecionado.descricao if plano_selecionado else ""), key=f"pl_descricao_{count}")
                    grupo_parada = st.text_input("Grupo de parada", value=clone.get("grupo_parada", "") if modo == "clonar" else (plano_selecionado.grupo_parada or "" if plano_selecionado else ""), key=f"pl_grupo_parada_{count}")

                with col_b:
                    tipo_intervencao = st.selectbox("Tipo de intervenção", TIPOS_INTERVENCAO, index=_valor_opcao(clone.get("tipo_intervencao", plano_selecionado.tipo_intervencao if plano_selecionado else None), TIPOS_INTERVENCAO, "Inspeção"), key=f"pl_tipo_intervencao_{count}")
                    disciplina = st.selectbox("Disciplina responsável", DISCIPLINAS, index=_valor_opcao(clone.get("disciplina", plano_selecionado.disciplina if plano_selecionado else None), DISCIPLINAS, "Mecânica"), key=f"pl_disciplina_{count}")
                    frequencia = st.selectbox("Frequência", FREQUENCIAS, index=_valor_opcao(clone.get("frequencia", plano_selecionado.frequencia if plano_selecionado else None), FREQUENCIAS, "Mensal"), key=f"pl_frequencia_{count}")
                    duracao_hh = st.number_input("Duração (HH)", min_value=0.0, value=clone.get("duracao_hh", plano_selecionado.duracao_hh if plano_selecionado else 4.0), step=0.5, key=f"pl_duracao_{count}")

                col_c, col_d, col_e = st.columns(3)
                prioridade = col_c.slider("Prioridade", min_value=1, max_value=5, value=clone.get("prioridade", plano_selecionado.prioridade if plano_selecionado else 3), key=f"pl_prioridade_{count}")
                janela_inicio = col_d.number_input("Janela início", min_value=1, max_value=52, value=clone.get("janela_inicio", plano_selecionado.janela_inicio if plano_selecionado else 1), key=f"pl_janela_inicio_{count}")
                janela_fim = col_e.number_input("Janela fim", min_value=1, max_value=52, value=clone.get("janela_fim", plano_selecionado.janela_fim if plano_selecionado else 52), key=f"pl_janela_fim_{count}")
                status = st.selectbox("Status", ["Ativo", "Inativo"], index=_valor_opcao(clone.get("status", plano_selecionado.status if plano_selecionado else None), ["Ativo", "Inativo"], "Ativo"), key=f"pl_status_{count}")

                if st.form_submit_button("Salvar plano", type="primary"):
                    nome_limpo = nome.strip() if nome else ""
                    if equipamento_selecionado == "Selecione":
                        st.error("Selecione o equipamento do novo plano.")
                    elif not nome_limpo:
                        st.warning("Informe o nome do plano.")
                    elif duracao_hh <= 0:
                        st.warning("A duração em HH deve ser maior que zero.")
                    elif janela_inicio > janela_fim:
                        st.warning("A janela de início não pode ser maior que a janela fim.")
                    else:
                        equipamento_id = equipamento_options[equipamento_selecionado]
                        duplicado = (
                            session.query(Plano)
                            .filter(Plano.equipamento_id == equipamento_id, Plano.nome == nome_limpo)
                            .first()
                        )
                        if duplicado and (modo != "editar" or not plano_selecionado or duplicado.id != plano_selecionado.id):
                            st.error("Já existe um plano com este nome para o equipamento selecionado.")
                            return

                        plano = plano_selecionado if modo == "editar" and plano_selecionado else Plano()
                        plano.equipamento_id = equipamento_id
                        plano.nome = nome_limpo
                        plano.descricao = descricao.strip()
                        plano.tipo_intervencao = tipo_intervencao
                        plano.disciplina = disciplina
                        plano.frequencia = frequencia
                        plano.duracao_hh = duracao_hh
                        plano.prioridade = prioridade
                        plano.grupo_parada = grupo_parada.strip() if grupo_parada else None
                        plano.janela_inicio = janela_inicio
                        plano.janela_fim = janela_fim
                        plano.status = status
                        session.add(plano)
                        try:
                            session.commit()
                            st.success("Plano salvo com sucesso.")
                            st.session_state["plano_edit_id"] = None
                            _resetar_form_plano()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Erro ao salvar: {str(e)}")

        section("Planos cadastrados", "Filtre por área e equipamento para revisar a carteira existente.")
        col1, col2 = st.columns(2)
        areas = sorted({e.area for e in session.query(Equipamento).all() if e.area})
        area_options = ["Todas"] + areas
        area_default = st.session_state.get("pl_filtro_area", "Todas")
        if area_default not in area_options:
            area_default = "Todas"
        area_filtro = col1.selectbox("Área", area_options, index=area_options.index(area_default), key="pl_filtro_area")

        query_eq = session.query(Equipamento)
        if area_filtro != "Todas":
            query_eq = query_eq.filter(Equipamento.area == area_filtro)
        equipamentos_filtro = query_eq.order_by(Equipamento.codigo).all()
        opcoes_eq = ["Todos"] + [f"{e.codigo} - {e.descricao}" for e in equipamentos_filtro]
        eq_default = st.session_state.get("pl_filtro_equipamento", "Todos")
        if eq_default not in opcoes_eq:
            eq_default = "Todos"
        eq_filtro = col2.selectbox("Equipamento", opcoes_eq, index=opcoes_eq.index(eq_default), key="pl_filtro_equipamento")

        query_planos = session.query(Plano).join(Equipamento, Plano.equipamento_id == Equipamento.id)
        if area_filtro != "Todas":
            query_planos = query_planos.filter(Equipamento.area == area_filtro)
        if eq_filtro != "Todos":
            query_planos = query_planos.filter(Equipamento.codigo == eq_filtro.split(" - ")[0])

        planos = query_planos.order_by(Plano.nome).all()
        st.caption(f"{len(planos)} plano(s) encontrado(s)")
        if planos:
            header = st.columns([1.6, 2.4, 1, 1, 1, 2.6])
            for col, label in zip(header, ["Equipamento", "Plano", "Frequência", "Janela", "Status", "Ações"]):
                col.markdown(f"**{label}**")

            for plano in planos:
                cols = st.columns([1.6, 2.4, 1, 1, 1, 2.6])
                cols[0].write(plano.equipamento.codigo if plano.equipamento else "-")
                cols[1].write(plano.nome)
                cols[2].write(plano.frequencia or "-")
                cols[3].write(f"S{plano.janela_inicio}-S{plano.janela_fim}")
                cols[4].markdown(status_badge(plano.status or "-"), unsafe_allow_html=True)
                with cols[5]:
                    a1, a2, a3 = st.columns(3)
                    dados_clone = {
                        "nome": plano.nome,
                        "descricao": plano.descricao,
                        "tipo_intervencao": plano.tipo_intervencao,
                        "disciplina": plano.disciplina,
                        "frequencia": plano.frequencia,
                        "duracao_hh": plano.duracao_hh,
                        "prioridade": plano.prioridade,
                        "grupo_parada": plano.grupo_parada,
                        "janela_inicio": plano.janela_inicio,
                        "janela_fim": plano.janela_fim,
                        "status": plano.status,
                    }
                    a1.button("Clonar", key=f"clonar_{plano.id}", on_click=_clonar_plano, args=(dados_clone,))
                    a2.button("Editar", key=f"edit_plano_{plano.id}", on_click=_editar_plano, args=(plano.id,))
                    a3.button("Remover", key=f"delete_plano_{plano.id}", on_click=_remover_plano, args=(plano.id,))
        else:
            st.info("Nenhum plano cadastrado ainda.")

    finally:
        session.close()
