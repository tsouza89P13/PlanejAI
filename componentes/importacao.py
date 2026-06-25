import streamlit as st

from componentes.ui import page_header, section
from database import SessionLocal
from services.importacao import (
    gerar_template_equipamentos,
    gerar_template_planos,
    importar_equipamentos,
    importar_planos,
)


def _resultado_importacao(resultado: dict, entidade: str) -> None:
    st.markdown("#### Resultado da importação")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Criados", resultado["criados"])
    col_b.metric("Atualizados", resultado["atualizados"])
    col_c.metric("Erros", len(resultado["erros"]))

    total = resultado["criados"] + resultado["atualizados"]
    if total > 0:
        st.success(f"{total} {entidade}(s) processado(s) com sucesso.")

    if resultado["erros"]:
        st.warning("Linhas com erro. Corrija o arquivo e reimporte:")
        for erro in resultado["erros"]:
            st.markdown(f"- {erro}")


def _card_equipamentos() -> None:
    with st.container(border=True):
        st.subheader("Equipamentos")
        st.caption("Cadastre ou atualize a base de ativos antes de carregar planos vinculados.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Template**")
            st.caption("Baixe o modelo oficial para manter códigos, áreas e criticidade padronizados.")
            if st.button("Preparar template de equipamentos"):
                template_bytes = gerar_template_equipamentos()
                st.download_button(
                    label="Baixar template de equipamentos",
                    data=template_bytes,
                    file_name="template_equipamentos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        with col2:
            st.markdown("**Importação**")
            arquivo_eq = st.file_uploader(
                "Arquivo de equipamentos",
                type=["xlsx"],
                key="upload_equipamentos",
            )
            if arquivo_eq and st.button("Importar equipamentos", type="primary", key="btn_importar_eq"):
                with st.spinner("Importando equipamentos..."):
                    session = SessionLocal()
                    try:
                        resultado = importar_equipamentos(arquivo_eq.getvalue(), session)
                    finally:
                        session.close()

                _resultado_importacao(resultado, "equipamento")


def _card_planos() -> None:
    with st.container(border=True):
        st.subheader("Planos de Manutenção")
        st.caption("Importe os equipamentos primeiro. O código do equipamento no Excel precisa existir no banco.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Template**")
            st.caption("Use o modelo para frequência, disciplina, HH, janelas e grupo de parada.")
            if st.button("Preparar template de planos"):
                template_bytes = gerar_template_planos()
                st.download_button(
                    label="Baixar template de planos",
                    data=template_bytes,
                    file_name="template_planos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        with col2:
            st.markdown("**Importação**")
            arquivo_pl = st.file_uploader(
                "Arquivo de planos",
                type=["xlsx"],
                key="upload_planos",
            )
            if arquivo_pl and st.button("Importar planos", type="primary", key="btn_importar_pl"):
                with st.spinner("Importando planos..."):
                    session = SessionLocal()
                    try:
                        resultado = importar_planos(arquivo_pl.getvalue(), session)
                    finally:
                        session.close()

                _resultado_importacao(resultado, "plano")


def render():
    page_header(
        "Importação via Excel",
        "Entrada assistida para carregar equipamentos e planos mantendo a integridade da carteira PCM.",
    )

    st.info(
        "Baixe o template, preencha com seus dados e envie o arquivo preenchido. "
        "Fórmulas são aceitas: o sistema lê o valor calculado da célula."
    )

    section("Fluxo recomendado", "1. Equipamentos primeiro. 2. Planos depois. 3. Gere o mapa anual após validar os cadastros.")
    _card_equipamentos()
    _card_planos()
