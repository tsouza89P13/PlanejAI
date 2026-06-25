from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from componentes.ui import page_header, section
from services.assistente import (
    PROVEDORES,
    chave_configurada,
    excluir_historico,
    listar_historico,
    modelo_id_por_rotulo,
    modelo_padrao,
    modelos_disponiveis,
    provedor_padrao,
    remover_chave,
    responder,
    salvar_chave,
)


def _render_contexto(contexto: list[dict]) -> None:
    for item in contexto:
        dados = item.get("dados", {})
        registros = dados.get("registros")
        if registros:
            st.markdown(f"**Dados consultados: `{item.get('nome')}`**")
            st.dataframe(pd.DataFrame(registros), use_container_width=True, hide_index=True)


def _render_historico() -> None:
    historico = listar_historico(15)
    if not historico:
        st.info("Nenhuma conversa salva ainda.")
        return

    for item in historico:
        with st.expander(f"{item.criado_em.strftime('%d/%m/%Y %H:%M')} | {item.pergunta[:90]}"):
            st.markdown(f"**Pergunta:** {item.pergunta}")
            st.markdown(f"**Resposta:** {item.resposta}")
            st.caption(f"Provedor: {item.provedor} | Modelo: {item.modelo} | Ferramentas: {item.ferramentas_usadas or '-'}")
            if st.button("Excluir chat", key=f"excluir_chat_{item.id}"):
                if excluir_historico(item.id):
                    st.success("Chat excluído do histórico.")
                    st.rerun()
                else:
                    st.warning("Não encontrei esse chat para excluir.")


def render():
    page_header(
        "Assistente PlanejAI",
        "Faça perguntas sobre a carteira PCM. O assistente consulta o banco local usando apenas ferramentas de leitura.",
    )

    section("Configuração da IA")
    provedor_inicial = provedor_padrao()
    provedor = st.selectbox(
        "Provedor",
        list(PROVEDORES.keys()),
        index=list(PROVEDORES.keys()).index(provedor_inicial),
        key="ia_provedor",
    )
    opcoes_modelo = modelos_disponiveis(provedor)
    modelo_escolhido = st.selectbox(
        "Modelo",
        opcoes_modelo,
        index=0,
        key=f"ia_modelo_select_{provedor}",
    )
    if modelo_escolhido == "Personalizado":
        modelo = st.text_input(
            "Nome do modelo personalizado",
            value=modelo_padrao(provedor),
            key=f"ia_modelo_custom_{provedor}",
            help="Use esta opção apenas se souber exatamente o nome técnico do modelo.",
        )
    else:
        modelo = modelo_id_por_rotulo(provedor, modelo_escolhido)
    st.info(
        "A disponibilidade de modelos depende da sua conta no provedor. "
        "Se a API retornar erro de modelo indisponível, escolha outro modelo da lista ou use Personalizado."
    )

    configurada = chave_configurada(provedor)
    if provedor == "Jovem Aprendiz (IA Simulada)":
        st.success("Modo gratuito de validação: não usa API externa e não gera custo.")
    else:
        st.caption("Status da chave: configurada nesta máquina." if configurada else "Status da chave: não configurada.")
        with st.expander("Gerenciar chave API", expanded=not configurada):
            api_key = st.text_input(f"Chave API do {provedor}", type="password", key=f"ia_key_{provedor}")
            col_salvar, col_remover = st.columns([1, 1])
            if col_salvar.button("Salvar chave localmente", type="primary", key=f"salvar_key_{provedor}"):
                if not api_key.strip():
                    st.warning("Informe uma chave API antes de salvar.")
                else:
                    salvar_chave(provedor, api_key)
                    st.success("Chave salva localmente em .streamlit/secrets.toml.")
                    st.rerun()
            if col_remover.button("Remover chave salva", key=f"remover_key_{provedor}", disabled=not configurada):
                remover_chave(provedor)
                st.success("Chave removida desta máquina.")
                st.rerun()

    section("Pergunte ao PlanejAI")
    exemplos = [
        "Quais ocorrências estão atrasadas em 2026?",
        "Qual equipamento tem maior backlog?",
        "Resumo da semana 26 de 2026.",
        "Existe alguma disciplina sobrecarregada?",
        "Quais equipamentos estão sem plano?",
        "Quais semanas estão mais carregadas?",
        "Como cadastro um equipamento?",
        "Como funciona o grupo de parada?",
        "Para que servem janela início, janela fim e prioridade?",
    ]
    pergunta = st.text_area(
        "Pergunta",
        placeholder="Ex.: Quais atividades estão atrasadas nesta semana?",
        height=110,
        key="ia_pergunta",
    )
    with st.expander("Exemplos de perguntas"):
        for exemplo in exemplos:
            st.markdown(f"- {exemplo}")

    if st.button("Enviar pergunta", type="primary", disabled=not configurada):
        if not pergunta.strip():
            st.warning("Digite uma pergunta para o assistente.")
        else:
            with st.spinner("Consultando dados locais e gerando resposta..."):
                try:
                    resultado = responder(pergunta, provedor=provedor, modelo=modelo)
                except Exception as e:
                    st.error(f"Erro ao consultar o assistente: {str(e)}")
                else:
                    st.markdown("### Resposta")
                    st.markdown(resultado["resposta"])
                    st.caption("Ferramentas usadas: " + ", ".join(resultado["ferramentas"]))
                    _render_contexto(resultado["contexto"])

    section("Histórico salvo")
    _render_historico()
