import streamlit as st

from componentes import (
    assistente,
    capacidade,
    calendario,
    dashboard,
    equipamentos,
    importacao,
    mapa_semanas,
    ocorrencias,
    planos,
)
from componentes.ui import apply_theme


st.set_page_config(
    page_title="PlanejAI",
    layout="wide",
    initial_sidebar_state="expanded",
)

GESTAO = {
    "Dashboard": dashboard,
    "Mapa de 52 Semanas": mapa_semanas,
}

INPUTS = {
    "Equipamentos": equipamentos,
    "Planos de Manutenção": planos,
    "Importação via Excel": importacao,
    "Calendário de Restrição": calendario,
    "Capacidade de Equipe": capacidade,
    "Execução de Ocorrência": ocorrencias,
}

IA = {
    "Assistente PlanejAI": assistente,
}

MENU = {**GESTAO, **INPUTS, **IA}


def _nav_button(label: str) -> None:
    active = st.session_state.get("pagina_atual", "Dashboard") == label
    if st.sidebar.button(
        label,
        key=f"nav_{label}",
        use_container_width=True,
        type="primary" if active else "secondary",
    ):
        st.session_state["pagina_atual"] = label
        st.rerun()


def main():
    apply_theme()
    if "pagina_atual" not in st.session_state:
        st.session_state["pagina_atual"] = "Dashboard"

    st.sidebar.markdown("## PlanejAI")
    st.sidebar.caption("Planejamento, capacidade e execução de manutenção.")

    st.sidebar.markdown("<div class='sidebar-group-title'>Gestão</div>", unsafe_allow_html=True)
    for label in GESTAO:
        _nav_button(label)

    st.sidebar.markdown("<div class='sidebar-group-title'>Inputs</div>", unsafe_allow_html=True)
    for label in INPUTS:
        _nav_button(label)

    st.sidebar.markdown("<div class='sidebar-group-title'>IA</div>", unsafe_allow_html=True)
    for label in IA:
        _nav_button(label)

    st.sidebar.markdown("---")
    st.sidebar.caption("Ambiente local")

    componente = MENU[st.session_state["pagina_atual"]]
    componente.render()


if __name__ == "__main__":
    main()
