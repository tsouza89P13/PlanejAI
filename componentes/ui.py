from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st


COLORS = {
    "bg": "#F4F6F9",
    "surface": "#FFFFFF",
    "surface_dark": "#1E293B",
    "surface_soft": "#E8EEF6",
    "border": "#D8E0EA",
    "text": "#172033",
    "muted": "#64748B",
    "blue": "#38BDF8",
    "green": "#34D399",
    "purple": "#7C3AED",
    "copper": "#D97706",
    "red": "#EF4444",
    "yellow": "#FACC15",
}


STATUS_COLORS = {
    "Programado": "#38BDF8",
    "Realizado": "#34D399",
    "Reprogramado": "#D97706",
    "Cancelado": "#94A3B8",
    "Atrasado": "#EF4444",
    "Ativo": "#34D399",
    "Inativo": "#94A3B8",
    "Alta": "#EF4444",
    "Média": "#D97706",
    "Baixa": "#38BDF8",
    "OK": "#34D399",
    "Atenção": "#FACC15",
}


def apply_theme() -> None:
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :root {{
                --pcm-bg: {COLORS["bg"]};
                --pcm-surface: {COLORS["surface"]};
                --pcm-dark: {COLORS["surface_dark"]};
                --pcm-border: {COLORS["border"]};
                --pcm-text: {COLORS["text"]};
                --pcm-muted: {COLORS["muted"]};
                --pcm-blue: {COLORS["blue"]};
                --pcm-green: {COLORS["green"]};
                --pcm-red: {COLORS["red"]};
                --pcm-yellow: {COLORS["yellow"]};
            }}

            html, body, [class*="css"] {{
                font-family: "Inter", "Segoe UI", sans-serif;
            }}

            .stApp {{
                background:
                    linear-gradient(180deg, rgba(30,41,59,0.05), rgba(244,246,249,0) 280px),
                    var(--pcm-bg);
                color: var(--pcm-text);
            }}

            .stApp, .stApp p, .stApp span, .stApp label,
            .stApp div[data-testid="stMarkdownContainer"],
            .stApp div[data-testid="stMarkdownContainer"] * {{
                color: var(--pcm-text);
            }}

            section[data-testid="stSidebar"] {{
                background: var(--pcm-dark);
                border-right: 1px solid rgba(255,255,255,0.08);
            }}

            section[data-testid="stSidebar"] * {{
                color: #E5EDF7 !important;
            }}

            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3,
            section[data-testid="stSidebar"] p {{
                color: #F8FAFC !important;
            }}

            section[data-testid="stSidebar"] .stButton button {{
                width: 100%;
                justify-content: flex-start;
                background: rgba(255,255,255,0.02);
                border: 2px solid #40516A;
                border-radius: 8px;
                color: #E5EDF7 !important;
                box-shadow: none;
                font-weight: 900;
                min-height: 44px;
                padding: 9px 12px;
                margin: 4px 0;
            }}

            section[data-testid="stSidebar"] .stButton button:hover {{
                background: rgba(56,189,248,0.12);
                border-color: #38BDF8;
                color: #FFFFFF !important;
            }}

            section[data-testid="stSidebar"] .stButton button[kind="primary"] {{
                background: #2563EB;
                border-color: #BAE6FD;
                color: #FFFFFF !important;
                box-shadow: 0 8px 20px rgba(56,189,248,0.22);
            }}

            section[data-testid="stSidebar"] .stButton button p,
            section[data-testid="stSidebar"] .stButton button span {{
                color: inherit !important;
                font-weight: 900 !important;
            }}

            .sidebar-group-title {{
                margin: 18px 0 6px;
                color: #93A4B8 !important;
                font-size: .75rem;
                font-weight: 850;
                letter-spacing: .08em;
                text-transform: uppercase;
            }}

            section[data-testid="stSidebar"] [role="radiogroup"] label {{
                border-radius: 8px;
                padding: 8px 10px;
                margin: 2px 0;
            }}

            section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
                background: rgba(255,255,255,0.08);
            }}

            .block-container {{
                padding-top: 1.4rem;
                padding-bottom: 3rem;
                max-width: 1480px;
            }}

            h1, h2, h3 {{
                color: var(--pcm-text);
                letter-spacing: 0;
            }}

            h1 {{
                font-size: 2rem;
                font-weight: 800;
                margin-bottom: .2rem;
            }}

            h2 {{
                font-size: 1.35rem;
                font-weight: 750;
            }}

            h3 {{
                font-size: 1.05rem;
                font-weight: 700;
            }}

            div[data-testid="stMetric"] {{
                background: var(--pcm-surface);
                border: 1px solid var(--pcm-border);
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 8px 24px rgba(15,23,42,0.05);
            }}

            div[data-testid="stMetricLabel"],
            div[data-testid="stMetricLabel"] *,
            div[data-testid="stMetricLabel"] p {{
                color: var(--pcm-muted);
                font-weight: 650;
                font-size: .82rem;
            }}

            div[data-testid="stMetricValue"],
            div[data-testid="stMetricValue"] * {{
                color: var(--pcm-text);
                font-weight: 800;
            }}

            div[data-testid="stWidgetLabel"],
            div[data-testid="stWidgetLabel"] *,
            label[data-testid="stWidgetLabel"],
            label[data-testid="stWidgetLabel"] * {{
                color: var(--pcm-muted);
                font-weight: 700;
            }}

            div[data-baseweb="input"],
            div[data-baseweb="select"] > div,
            div[data-baseweb="textarea"],
            div[data-testid="stNumberInput"] div[data-baseweb="input"] {{
                background: #FFFFFF;
                border-color: var(--pcm-border);
                color: var(--pcm-text);
            }}

            div[data-baseweb="input"] input,
            div[data-baseweb="textarea"] textarea,
            div[data-baseweb="select"] span,
            div[data-baseweb="select"] input {{
                color: var(--pcm-text);
                background: #FFFFFF;
                caret-color: var(--pcm-text);
            }}

            div[data-baseweb="select"] svg,
            div[data-testid="stNumberInput"] svg {{
                color: var(--pcm-muted);
                fill: var(--pcm-muted);
            }}

            div[data-baseweb="select"] [aria-disabled="true"],
            input::placeholder,
            textarea::placeholder {{
                color: #475569 !important;
                opacity: 1 !important;
                font-weight: 600;
            }}

            div[data-testid="stNumberInput"] button {{
                background: #FFFFFF;
                color: var(--pcm-text);
                border-color: var(--pcm-border);
            }}

            div[data-testid="stFileUploader"] section {{
                background: #FFFFFF;
                border: 1px solid var(--pcm-border);
                border-radius: 8px;
                min-height: 52px;
                padding: 10px 14px;
            }}

            div[data-testid="stFileUploader"] section * {{
                color: var(--pcm-text) !important;
            }}

            div[data-testid="stFileUploader"] button {{
                background: #FFFFFF;
                color: var(--pcm-text);
                border: 1px solid var(--pcm-border);
                border-radius: 8px;
            }}

            .row-table-header {{
                background: #E8EEF6;
                border: 1px solid var(--pcm-border);
                border-radius: 8px 8px 0 0;
                padding: 10px 12px;
                margin-top: 10px;
            }}

            .row-table-header [data-testid="column"] * {{
                color: #172033 !important;
                font-size: .76rem;
                font-weight: 900;
                letter-spacing: .06em;
                text-transform: uppercase;
            }}

            .row-table-row {{
                background: #FFFFFF;
                border-left: 1px solid var(--pcm-border);
                border-right: 1px solid var(--pcm-border);
                border-bottom: 1px solid #EDF1F6;
                padding: 8px 12px;
            }}

            .row-table-row [data-testid="column"] {{
                display: flex;
                align-items: center;
            }}

            .row-table-row p,
            .row-table-row span {{
                color: #172033 !important;
                font-size: .88rem;
            }}

            .stButton button, .stDownloadButton button, div[data-testid="stFormSubmitButton"] button {{
                border-radius: 8px;
                border: 1px solid var(--pcm-border);
                font-weight: 700;
                min-height: 2.55rem;
                background: #FFFFFF;
                color: var(--pcm-text);
            }}

            .stButton button[kind="primary"], div[data-testid="stFormSubmitButton"] button[kind="primary"] {{
                background: var(--pcm-dark);
                border-color: var(--pcm-dark);
                color: #FFFFFF;
            }}

            .stButton button[kind="primary"] *,
            div[data-testid="stFormSubmitButton"] button[kind="primary"] * {{
                color: #FFFFFF;
            }}

            div[data-testid="stExpander"] {{
                background: var(--pcm-surface);
                border: 1px solid var(--pcm-border);
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(15,23,42,0.04);
                overflow: hidden;
            }}

            div[data-testid="stExpander"] details,
            div[data-testid="stExpander"] summary {{
                background: #FFFFFF;
                color: var(--pcm-text);
            }}

            div[data-testid="stExpander"] summary *,
            div[data-testid="stExpander"] div[role="button"] * {{
                color: var(--pcm-text);
                font-weight: 750;
            }}

            div[data-testid="stForm"] {{
                background: #FFFFFF;
                border: 0;
            }}

            div[data-testid="stAlert"] {{
                border-radius: 8px;
                border: 1px solid var(--pcm-border);
            }}

            .pcm-hero {{
                background: linear-gradient(135deg, #1E293B 0%, #263A55 58%, #0F172A 100%);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                padding: 22px 24px;
                margin-bottom: 18px;
                box-shadow: 0 14px 34px rgba(15,23,42,0.16);
            }}

            .pcm-hero h1 {{
                color: #FFFFFF !important;
                font-weight: 900 !important;
                margin: 0 0 4px 0;
            }}

            .pcm-hero p {{
                color: #C9D6E6 !important;
                margin: 0;
                max-width: 920px;
                line-height: 1.55;
            }}

            div[data-testid="stMarkdownContainer"] .pcm-hero h1,
            div[data-testid="stMarkdownContainer"] .pcm-hero h1 *,
            div[data-testid="stMarkdownContainer"] .pcm-hero p,
            div[data-testid="stMarkdownContainer"] .pcm-hero p * {{
                color: #FFFFFF !important;
            }}

            div[data-testid="stMarkdownContainer"] .pcm-hero p,
            div[data-testid="stMarkdownContainer"] .pcm-hero p * {{
                color: #D7E3F2 !important;
                font-weight: 650 !important;
            }}

            .pcm-section {{
                background: var(--pcm-surface);
                border: 1px solid var(--pcm-border);
                border-radius: 8px;
                padding: 18px;
                margin: 14px 0;
                box-shadow: 0 8px 24px rgba(15,23,42,0.04);
            }}

            .pcm-section h3 {{
                margin-top: 0;
            }}

            .pcm-muted {{
                color: var(--pcm-muted);
            }}

            .pcm-pill {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                min-height: 24px;
                padding: 3px 9px;
                border-radius: 999px;
                font-size: .78rem;
                font-weight: 750;
                border: 1px solid rgba(15,23,42,.08);
                white-space: nowrap;
            }}

            .pcm-table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                overflow: hidden;
                border: 1px solid var(--pcm-border);
                border-radius: 8px;
                background: white;
                font-size: .9rem;
            }}

            .pcm-table th {{
                background: #E8EEF6;
                color: #243044;
                text-align: left;
                padding: 10px 12px;
                font-size: .78rem;
                text-transform: uppercase;
                letter-spacing: .04em;
                border-bottom: 1px solid var(--pcm-border);
            }}

            .pcm-table td {{
                padding: 11px 12px;
                border-bottom: 1px solid #EDF1F6;
                vertical-align: top;
            }}

            .pcm-table tr:last-child td {{
                border-bottom: 0;
            }}

            .pcm-table tr:hover td {{
                background: #F8FAFC;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="pcm-hero">
            <h1>{escape(title)}</h1>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p class='pcm-muted'>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(f"<h2>{escape(title)}</h2>{subtitle_html}", unsafe_allow_html=True)


def status_badge(label: str, tone: str | None = None) -> str:
    color = STATUS_COLORS.get(tone or label, COLORS["muted"])
    text_color = "#0F172A" if color == COLORS["yellow"] else "#FFFFFF"
    return (
        f"<span class='pcm-pill' style='background:{color};color:{text_color};'>"
        f"{escape(str(label))}</span>"
    )


def mini_badge(label: str, color: str) -> str:
    text_color = "#0F172A" if color.lower() in {"#facc15", "#fde047"} else "#FFFFFF"
    return (
        f"<span class='pcm-pill' style='background:{color};color:{text_color};'>"
        f"{escape(str(label))}</span>"
    )


def html_table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    header_html = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    row_html = []
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        row_html.append(f"<tr>{cells}</tr>")
    return (
        "<table class='pcm-table'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table>"
    )
