from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from database import SessionLocal
from models import AssistenteHistorico
from services.ferramentas_ia import selecionar_e_executar_ferramentas


ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"

PROVEDORES = {
    "Jovem Aprendiz (IA Simulada)": {
        "key_name": None,
        "default_model": "simulado-local",
        "models": [
            {"id": "simulado-local", "label": "simulado-local — gratuito, local e sem chamada de API"},
        ],
    },
    "OpenAI": {
        "key_name": "OPENAI_API_KEY",
        "default_model": "gpt-4.1-mini",
        "models": [
            {"id": "gpt-4.1-mini", "label": "gpt-4.1-mini — recomendado, rápido e econômico"},
            {"id": "gpt-4.1", "label": "gpt-4.1 — mais robusto para análises complexas"},
            {"id": "gpt-4o-mini", "label": "gpt-4o-mini — leve, rápido e compatível"},
            {"id": "gpt-4o", "label": "gpt-4o — geral e robusto, depende da conta"},
        ],
    },
    "Gemini": {
        "key_name": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
        "models": [
            {"id": "gemini-2.5-flash", "label": "gemini-2.5-flash — recomendado, rápido e econômico"},
            {"id": "gemini-2.5-pro", "label": "gemini-2.5-pro — mais robusto para análises complexas"},
            {"id": "gemini-1.5-flash", "label": "gemini-1.5-flash — compatível e leve"},
            {"id": "gemini-1.5-pro", "label": "gemini-1.5-pro — compatível e mais forte"},
        ],
    },
    "Claude": {
        "key_name": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-sonnet-latest",
        "models": [
            {"id": "claude-3-5-sonnet-latest", "label": "claude-3-5-sonnet-latest — recomendado, equilibrado e forte"},
            {"id": "claude-3-5-haiku-latest", "label": "claude-3-5-haiku-latest — rápido e econômico"},
            {"id": "claude-3-opus-latest", "label": "claude-3-opus-latest — mais robusto, se disponível na conta"},
        ],
    },
}


def _ler_secrets() -> dict[str, str]:
    if not SECRETS_PATH.exists():
        return {}
    dados: dict[str, str] = {}
    for linha in SECRETS_PATH.read_text(encoding="utf-8").splitlines():
        if "=" not in linha or linha.strip().startswith("#"):
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave:
            dados[chave] = valor
    return dados


def _gravar_secrets(dados: dict[str, str]) -> None:
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    linhas = [f'{chave} = "{valor}"' for chave, valor in sorted(dados.items()) if valor]
    SECRETS_PATH.write_text("\n".join(linhas) + ("\n" if linhas else ""), encoding="utf-8")


def chave_configurada(provedor: str) -> bool:
    config = PROVEDORES.get(provedor)
    if not config:
        return False
    if not config["key_name"]:
        return True
    return bool(_ler_secrets().get(config["key_name"]))


def salvar_chave(provedor: str, api_key: str) -> None:
    config = PROVEDORES[provedor]
    if not config["key_name"]:
        return
    dados = _ler_secrets()
    dados[config["key_name"]] = api_key.strip()
    dados["PLANEJAI_PROVIDER"] = provedor
    _gravar_secrets(dados)


def remover_chave(provedor: str) -> None:
    config = PROVEDORES[provedor]
    if not config["key_name"]:
        return
    dados = _ler_secrets()
    dados.pop(config["key_name"], None)
    _gravar_secrets(dados)


def provedor_padrao() -> str:
    dados = _ler_secrets()
    provedor = dados.get("PLANEJAI_PROVIDER", "OpenAI")
    return provedor if provedor in PROVEDORES else "OpenAI"


def modelo_padrao(provedor: str) -> str:
    return PROVEDORES[provedor]["default_model"]


def modelos_disponiveis(provedor: str) -> list[str]:
    return [*[modelo["label"] for modelo in PROVEDORES[provedor]["models"]], "Personalizado"]


def modelo_id_por_rotulo(provedor: str, rotulo: str) -> str:
    for modelo in PROVEDORES[provedor]["models"]:
        if modelo["label"] == rotulo:
            return modelo["id"]
    return modelo_padrao(provedor)


def _obter_api_key(provedor: str) -> str:
    config = PROVEDORES[provedor]
    if not config["key_name"]:
        return ""
    api_key = _ler_secrets().get(config["key_name"], "")
    if not api_key:
        raise ValueError(f"Chave API de {provedor} não configurada.")
    return api_key


def _prompt(pergunta: str, contexto: list[dict[str, Any]]) -> str:
    contexto_json = json.dumps(contexto, ensure_ascii=False, default=str)
    return f"""
Você é o Assistente PlanejAI, um analista de PCM e manutenção.
Responda em português do Brasil, com objetividade e linguagem profissional.

Regras:
- Use apenas os dados do contexto fornecido.
- Não invente números, registros ou conclusões.
- Não altere dados, não recomende executar SQL e não peça permissões de escrita.
- Se os dados forem insuficientes, diga claramente o que faltou.
- Sempre que houver registros, traga um resumo executivo e cite os principais itens.
- Se o contexto vier da ferramenta consultar_ajuda_sistema, responda como manual oficial do PlanejAI.
- Se o contexto vier da ferramenta pergunta_fora_escopo, não invente resposta: explique a limitação e sugira perguntas suportadas.
- Se o contexto vier da ferramenta consultar_limitacoes_sistema, responda como auditoria objetiva das fragilidades conhecidas.

Pergunta do usuário:
{pergunta}

Contexto consultado no banco local:
{contexto_json}
""".strip()


def _responder_openai(api_key: str, modelo: str, prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("A biblioteca openai não está instalada. Rode: pip install -r requirements.txt") from exc

    client = OpenAI(api_key=api_key)
    resposta = client.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": "Você responde como analista de planejamento de manutenção."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return resposta.choices[0].message.content or ""


def _responder_gemini(api_key: str, modelo: str, prompt: str) -> str:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("A biblioteca google-genai não está instalada. Rode: pip install -r requirements.txt") from exc

    client = genai.Client(api_key=api_key)
    resposta = client.models.generate_content(model=modelo, contents=prompt)
    return getattr(resposta, "text", "") or ""


def _responder_claude(api_key: str, modelo: str, prompt: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("A biblioteca anthropic não está instalada. Rode: pip install -r requirements.txt") from exc

    client = Anthropic(api_key=api_key)
    resposta = client.messages.create(
        model=modelo,
        max_tokens=1600,
        temperature=0.2,
        system="Você responde como analista de planejamento de manutenção.",
        messages=[{"role": "user", "content": prompt}],
    )
    partes = []
    for bloco in resposta.content:
        texto = getattr(bloco, "text", None)
        if texto:
            partes.append(texto)
    return "\n".join(partes)


def _responder_simulado(pergunta: str, contexto: list[dict[str, Any]]) -> str:
    linhas = ["**Resposta simulada com dados locais do PlanejAI.**", ""]
    for item in contexto:
        nome = item.get("nome")
        dados = item.get("dados", {})
        registros = dados.get("registros") or []

        if nome == "consultar_ajuda_sistema":
            linhas.append("Encontrei orientações de uso do sistema para sua pergunta:")
            for registro in registros:
                linhas.append(f"\n**{registro.get('titulo', 'Tópico')}**")
                for orientacao in registro.get("orientacoes", []):
                    linhas.append(f"- {orientacao}")
            continue

        if nome == "consultar_base_conhecimento":
            if registros:
                linhas.append("Consultei a base de conhecimento do PlanejAI e encontrei estes pontos:")
                for registro in registros:
                    linhas.append(f"\n**{registro.get('titulo', 'Tópico')}**")
                    linhas.append(str(registro.get("resposta", "")).strip())
            else:
                linhas.append("Não encontrei um trecho correspondente na base de conhecimento do PlanejAI.")
            continue

        if nome == "consultar_limitacoes_sistema":
            linhas.append("As principais fragilidades conhecidas do PlanejAI hoje são:")
            for registro in registros:
                linhas.append(
                    f"- **{registro.get('area', 'Sistema')}**: {registro.get('limitacao')} "
                    f"Impacto: {registro.get('impacto')}"
                )
            continue

        if nome == "pergunta_fora_escopo":
            linhas.append(dados.get("mensagem", "Não consegui responder essa pergunta com segurança."))
            sugestoes = dados.get("sugestoes") or []
            if sugestoes:
                linhas.append("\nPerguntas que eu consigo tratar melhor agora:")
                for sugestao in sugestoes:
                    linhas.append(f"- {sugestao}")
            continue

        if nome == "consultar_ranking_planos_por_equipamento":
            if not registros:
                linhas.append("Não encontrei planos cadastrados por equipamento para montar o ranking.")
            else:
                primeiro = registros[0]
                linhas.append(
                    "O equipamento com mais planos cadastrados é "
                    f"**{primeiro['equipamento']} - {primeiro['descricao']}**, "
                    f"com **{primeiro['total_planos']} plano(s)**, sendo "
                    f"**{primeiro['planos_ativos']} ativo(s)**."
                )
                linhas.append("\nPrincipais equipamentos no ranking:")
                for registro in registros[:5]:
                    linhas.append(
                        f"- {registro['equipamento']} | {registro['descricao']}: "
                        f"{registro['total_planos']} plano(s), {registro['planos_ativos']} ativo(s)"
                    )
            continue

        if nome == "consultar_ocorrencias_atrasadas":
            linhas.append(
                f"Foram encontradas **{dados.get('total', 0)} ocorrência(s) atrasada(s)** "
                f"em {dados.get('ano')}, totalizando **{dados.get('hh_total', 0.0):.1f} HH**."
            )
            por_disciplina = dados.get("por_disciplina") or {}
            if por_disciplina:
                linhas.append("Distribuição por disciplina:")
                for disciplina, total in por_disciplina.items():
                    linhas.append(f"- {disciplina}: {total}")
            continue

        if nome == "consultar_backlog_por_equipamento":
            if registros:
                primeiro = registros[0]
                linhas.append(
                    "No backlog, o equipamento mais impactado é "
                    f"**{primeiro['equipamento']} - {primeiro['descricao']}**, "
                    f"com **{primeiro['hh_atrasado']:.1f} HH atrasado(s)**."
                )
            continue

        if nome == "consultar_ocorrencias_por_semana":
            linhas.append(
                f"Na S{dados.get('semana')}/{dados.get('ano')}, encontrei "
                f"**{dados.get('total', 0)} ocorrência(s)**, somando "
                f"**{dados.get('hh_total', 0.0):.1f} HH previsto(s)**."
            )
            continue

        if nome == "consultar_capacidade_por_disciplina":
            linhas.append(f"Consultei a capacidade por disciplina em {dados.get('ano')}.")
            atencao = [r for r in registros if r.get("situacao") != "OK"]
            if atencao:
                linhas.append("Disciplinas que exigem atenção:")
                for registro in atencao:
                    linhas.append(
                        f"- {registro['disciplina']}: necessário {registro['hh_necessario_semana']:.1f} HH/sem, "
                        f"disponível {registro['hh_disponivel_semana']:.1f} HH/sem"
                    )
            else:
                linhas.append("Não identifiquei disciplina sobrecarregada nos dados consultados.")
            continue

        if nome == "consultar_equipamentos_sem_plano":
            linhas.append(f"Encontrei **{len(registros)} equipamento(s) sem plano vinculado**.")
            continue

        if nome == "consultar_concentracao_por_semana":
            if registros:
                primeiro = registros[0]
                linhas.append(
                    f"A semana mais carregada é a **S{primeiro['semana']}**, com "
                    f"**{primeiro['hh_previsto']:.1f} HH previsto(s)** e "
                    f"**{primeiro['ocorrencias']} ocorrência(s)**."
                )
            continue

        if nome == "consultar_restricoes_calendario":
            linhas.append(f"Encontrei **{len(registros)} restrição(ões)** no calendário de {dados.get('ano')}.")
            continue

        linhas.append(item.get("resumo", "Consulta realizada."))

    linhas.extend(
        [
            "",
            "_Observação: o Jovem Aprendiz não usa IA externa; ele resume consultas locais para validação sem custo._",
        ]
    )
    return "\n".join(linhas)


def responder(pergunta: str, provedor: str, modelo: str | None = None) -> dict[str, Any]:
    pergunta = pergunta.strip()
    if not pergunta:
        raise ValueError("Digite uma pergunta para o assistente.")
    if provedor not in PROVEDORES:
        raise ValueError("Provedor de IA inválido.")

    modelo = modelo or modelo_padrao(provedor)
    contexto = selecionar_e_executar_ferramentas(pergunta)

    if provedor == "Jovem Aprendiz (IA Simulada)":
        resposta = _responder_simulado(pergunta, contexto)
    else:
        prompt = _prompt(pergunta, contexto)
        api_key = _obter_api_key(provedor)
        if provedor == "OpenAI":
            resposta = _responder_openai(api_key, modelo, prompt)
        elif provedor == "Gemini":
            resposta = _responder_gemini(api_key, modelo, prompt)
        elif provedor == "Claude":
            resposta = _responder_claude(api_key, modelo, prompt)
        else:
            raise ValueError("Provedor de IA não suportado.")

    ferramentas = [item["nome"] for item in contexto]
    session = SessionLocal()
    try:
        historico = AssistenteHistorico(
            criado_em=datetime.utcnow(),
            provedor=provedor,
            modelo=modelo,
            pergunta=pergunta,
            resposta=resposta,
            ferramentas_usadas=", ".join(ferramentas),
            contexto_json=json.dumps(contexto, ensure_ascii=False, default=str),
        )
        session.add(historico)
        session.commit()
    finally:
        session.close()

    return {
        "resposta": resposta,
        "contexto": contexto,
        "ferramentas": ferramentas,
        "provedor": provedor,
        "modelo": modelo,
    }


def listar_historico(limite: int = 20) -> list[AssistenteHistorico]:
    session = SessionLocal()
    try:
        return (
            session.query(AssistenteHistorico)
            .order_by(AssistenteHistorico.criado_em.desc())
            .limit(limite)
            .all()
        )
    finally:
        session.close()


def excluir_historico(historico_id: int) -> bool:
    session = SessionLocal()
    try:
        historico = session.get(AssistenteHistorico, historico_id)
        if not historico:
            return False
        session.delete(historico)
        session.commit()
        return True
    finally:
        session.close()
