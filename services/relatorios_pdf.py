from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from io import BytesIO
from typing import Callable, Iterable

from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Equipamento, Ocorrencia, Plano
from services.dashboard import calcular_indicadores
from services.status import status_ocorrencia


BRAND = {
    "dark": "#1E293B",
    "text": "#172033",
    "muted": "#64748B",
    "border": "#D8E0EA",
    "bg": "#F4F6F9",
    "blue": "#38BDF8",
    "green": "#34D399",
    "purple": "#7C3AED",
    "copper": "#D97706",
    "red": "#EF4444",
    "gray": "#94A3B8",
}

STATUS_CORES = {
    "Programado": BRAND["blue"],
    "Realizado": BRAND["green"],
    "Reprogramado": BRAND["copper"],
    "Cancelado": BRAND["gray"],
    "Atrasado": BRAND["red"],
}

STATUS_SIGLAS = {
    "Programado": "P",
    "Realizado": "R",
    "Reprogramado": "RP",
    "Cancelado": "C",
    "Atrasado": "A",
}


def _rl():
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError("A biblioteca reportlab nao esta instalada. Rode: pip install -r requirements.txt") from exc

    return {
        "colors": colors,
        "TA_CENTER": TA_CENTER,
        "A4": A4,
        "landscape": landscape,
        "getSampleStyleSheet": getSampleStyleSheet,
        "ParagraphStyle": ParagraphStyle,
        "Flowable": Flowable,
        "mm": mm,
        "PageBreak": PageBreak,
        "Paragraph": Paragraph,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Spacer": Spacer,
        "Table": Table,
        "TableStyle": TableStyle,
    }


def _hex_cor(rl, hex_color: str):
    return rl["colors"].HexColor(hex_color)


def _styles(rl):
    base = rl["getSampleStyleSheet"]()
    paragraph_style = rl["ParagraphStyle"]
    return {
        "title": paragraph_style(
            "PlanejAITitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=_hex_cor(rl, BRAND["dark"]),
            spaceAfter=8,
        ),
        "subtitle": paragraph_style(
            "PlanejAISubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=_hex_cor(rl, BRAND["muted"]),
            spaceAfter=8,
        ),
        "section": paragraph_style(
            "PlanejAISection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=_hex_cor(rl, BRAND["text"]),
            spaceBefore=8,
            spaceAfter=5,
        ),
        "small": paragraph_style(
            "PlanejAISmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=_hex_cor(rl, BRAND["text"]),
        ),
        "tiny": paragraph_style(
            "PlanejAITiny",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=5.8,
            leading=6.6,
            textColor=_hex_cor(rl, BRAND["text"]),
        ),
        "tiny_center": paragraph_style(
            "PlanejAITinyCenter",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=5.3,
            leading=6,
            alignment=rl["TA_CENTER"],
            textColor=_hex_cor(rl, BRAND["text"]),
        ),
    }


def _doc(rl, buffer: BytesIO, pagesize, title: str, margin_mm: float = 10):
    mm = rl["mm"]
    return rl["SimpleDocTemplate"](
        buffer,
        pagesize=pagesize,
        title=title,
        leftMargin=margin_mm * mm,
        rightMargin=margin_mm * mm,
        topMargin=margin_mm * mm,
        bottomMargin=margin_mm * mm,
    )


def _header(rl, styles, titulo: str, subtitulo: str) -> list:
    paragraph = rl["Paragraph"]
    spacer = rl["Spacer"]
    return [
        paragraph(titulo, styles["title"]),
        paragraph(f"{subtitulo}<br/>Emitido em {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["subtitle"]),
        spacer(1, 4),
    ]


def _table(rl, data: list[list], col_widths: list[float] | None = None, font_size: int = 7):
    table = rl["Table"](data, colWidths=col_widths, repeatRows=1)
    colors = rl["colors"]
    table.setStyle(
        rl["TableStyle"](
            [
                ("BACKGROUND", (0, 0), (-1, 0), _hex_cor(rl, BRAND["dark"])),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), font_size),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), font_size),
                ("TEXTCOLOR", (0, 1), (-1, -1), _hex_cor(rl, BRAND["text"])),
                ("GRID", (0, 0), (-1, -1), 0.25, _hex_cor(rl, BRAND["border"])),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _hex_cor(rl, BRAND["bg"])]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _filtros_texto(**filtros) -> str:
    partes = []
    for chave, valor in filtros.items():
        if isinstance(valor, list):
            valor = ", ".join(valor) if valor else "Todos"
        elif valor in (None, "", "Todos", "Todas"):
            valor = "Todos"
        partes.append(f"{chave}: {valor}")
    return " | ".join(partes)


def _query_ocorrencias(
    ano: int,
    semana: int | str | None = None,
    equipamento_codigo: str | None = None,
    disciplina: str | None = None,
) -> list[Ocorrencia]:
    session = SessionLocal()
    try:
        query = (
            session.query(Ocorrencia)
            .join(Plano, Ocorrencia.plano_id == Plano.id)
            .join(Equipamento, Plano.equipamento_id == Equipamento.id)
            .options(joinedload(Ocorrencia.plano).joinedload(Plano.equipamento))
            .filter(Ocorrencia.ano == ano)
        )
        if semana not in (None, "Todas"):
            query = query.filter(Ocorrencia.semana == int(semana))
        if equipamento_codigo:
            query = query.filter(Equipamento.codigo == equipamento_codigo)
        if disciplina and disciplina != "Todas":
            query = query.filter(Plano.disciplina == disciplina)
        return query.order_by(Ocorrencia.semana, Equipamento.codigo, Plano.nome).all()
    finally:
        session.close()


def _query_ocorrencias_dashboard(ano: int, disciplinas: list[str], tipos: list[str], areas: list[str]) -> list[Ocorrencia]:
    session = SessionLocal()
    try:
        query = (
            session.query(Ocorrencia)
            .join(Plano, Ocorrencia.plano_id == Plano.id)
            .join(Equipamento, Plano.equipamento_id == Equipamento.id)
            .options(joinedload(Ocorrencia.plano).joinedload(Plano.equipamento))
            .filter(Ocorrencia.ano == ano)
        )
        if disciplinas:
            query = query.filter(Plano.disciplina.in_(disciplinas))
        if tipos:
            query = query.filter(Plano.tipo_intervencao.in_(tipos))
        if areas:
            query = query.filter(Equipamento.area.in_(areas))
        return query.order_by(Ocorrencia.semana, Equipamento.codigo, Plano.nome).all()
    finally:
        session.close()


def _canvas_flowable(rl, width: float, height: float, draw_fn: Callable) -> object:
    flowable_base = rl["Flowable"]

    class CanvasFlowable(flowable_base):
        def wrap(self, availWidth, availHeight):
            return width, height

        def draw(self):
            draw_fn(self.canv, width, height)

    return CanvasFlowable()


def _draw_text(canv, x: float, y: float, text: str, size: float = 8, color: str = BRAND["text"], bold: bool = False):
    canv.setFillColor(color)
    canv.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    canv.drawString(x, y, str(text))


def _draw_center(canv, x: float, y: float, text: str, size: float = 8, color: str = BRAND["text"], bold: bool = False):
    canv.setFillColor(color)
    canv.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    canv.drawCentredString(x, y, str(text))


def _card_grid(rl, items: list[tuple[str, str, str]], width: float, height: float):
    colors = rl["colors"]

    def draw(canv, w, h):
        cols = 4
        gap = 8
        card_w = (w - gap * (cols - 1)) / cols
        card_h = (h - gap) / 2
        for i, (label, value, color) in enumerate(items):
            row = i // cols
            col = i % cols
            x = col * (card_w + gap)
            y = h - (row + 1) * card_h - row * gap
            canv.setFillColor(colors.white)
            canv.setStrokeColor(_hex_cor(rl, BRAND["border"]))
            canv.roundRect(x, y, card_w, card_h, 7, stroke=1, fill=1)
            canv.setFillColor(_hex_cor(rl, color))
            canv.roundRect(x + 8, y + card_h - 13, 24, 5, 2, stroke=0, fill=1)
            _draw_text(canv, x + 8, y + card_h - 28, label, 7, BRAND["muted"], True)
            _draw_text(canv, x + 8, y + 14, value, 15, BRAND["text"], True)

    return _canvas_flowable(rl, width, height, draw)


def _bar_chart(rl, title: str, data: list[tuple[str, float]], width: float, height: float, color: str = BRAND["blue"], max_items: int = 12):
    colors = rl["colors"]
    data = data[:max_items]

    def draw(canv, w, h):
        canv.setFillColor(colors.white)
        canv.setStrokeColor(_hex_cor(rl, BRAND["border"]))
        canv.roundRect(0, 0, w, h, 7, stroke=1, fill=1)
        _draw_text(canv, 10, h - 18, title, 9, BRAND["text"], True)
        if not data:
            _draw_center(canv, w / 2, h / 2, "Sem dados", 9, BRAND["muted"], False)
            return
        left = 34
        bottom = 28
        plot_w = w - left - 14
        plot_h = h - bottom - 34
        max_val = max([value for _, value in data] + [1])
        bar_gap = 2
        bar_w = max(4, (plot_w - bar_gap * (len(data) - 1)) / len(data))
        canv.setStrokeColor(_hex_cor(rl, "#EDF1F6"))
        for i in range(4):
            y = bottom + plot_h * i / 3
            canv.line(left, y, left + plot_w, y)
        for i, (label, value) in enumerate(data):
            bar_h = plot_h * (value / max_val if max_val else 0)
            x = left + i * (bar_w + bar_gap)
            canv.setFillColor(_hex_cor(rl, color))
            canv.rect(x, bottom, bar_w, bar_h, stroke=0, fill=1)
            _draw_center(canv, x + bar_w / 2, 12, label[:8], 5.2, BRAND["muted"], False)
        _draw_text(canv, 8, bottom + plot_h - 4, f"{max_val:.0f}", 5.5, BRAND["muted"], False)

    return _canvas_flowable(rl, width, height, draw)


def _horizontal_bar_chart(rl, title: str, data: list[tuple[str, float]], width: float, height: float, color: str = BRAND["dark"], max_items: int = 8):
    colors = rl["colors"]
    data = data[:max_items]

    def draw(canv, w, h):
        canv.setFillColor(colors.white)
        canv.setStrokeColor(_hex_cor(rl, BRAND["border"]))
        canv.roundRect(0, 0, w, h, 7, stroke=1, fill=1)
        _draw_text(canv, 10, h - 18, title, 9, BRAND["text"], True)
        if not data:
            _draw_center(canv, w / 2, h / 2, "Sem dados", 9, BRAND["muted"], False)
            return
        max_val = max([value for _, value in data] + [1])
        left = 78
        top = h - 34
        row_h = (h - 44) / max(len(data), 1)
        for i, (label, value) in enumerate(data):
            y = top - (i + 1) * row_h + 4
            bar_w = (w - left - 20) * (value / max_val if max_val else 0)
            _draw_text(canv, 10, y + 2, label[:18], 5.8, BRAND["muted"], False)
            canv.setFillColor(_hex_cor(rl, color))
            canv.roundRect(left, y, bar_w, max(5, row_h - 8), 2, stroke=0, fill=1)
            _draw_text(canv, left + bar_w + 4, y + 2, f"{value:.0f}", 5.6, BRAND["text"], True)

    return _canvas_flowable(rl, width, height, draw)


def _donut_chart(rl, title: str, data: list[tuple[str, float, str]], width: float, height: float):
    colors = rl["colors"]

    def draw(canv, w, h):
        canv.setFillColor(colors.white)
        canv.setStrokeColor(_hex_cor(rl, BRAND["border"]))
        canv.roundRect(0, 0, w, h, 7, stroke=1, fill=1)
        _draw_text(canv, 10, h - 18, title, 9, BRAND["text"], True)
        total = sum(value for _, value, _ in data)
        if total <= 0:
            _draw_center(canv, w / 2, h / 2, "Sem dados", 9, BRAND["muted"], False)
            return
        cx = 54
        cy = h / 2 - 8
        radius = 34
        start = 90
        for label, value, color in data:
            extent = 360 * value / total
            canv.setFillColor(_hex_cor(rl, color))
            canv.wedge(cx - radius, cy - radius, cx + radius, cy + radius, start, extent, stroke=0, fill=1)
            start += extent
        canv.setFillColor(colors.white)
        canv.circle(cx, cy, radius * 0.54, stroke=0, fill=1)
        _draw_center(canv, cx, cy - 3, f"{total:.0f}", 10, BRAND["text"], True)
        y = h - 38
        for label, value, color in data[:6]:
            canv.setFillColor(_hex_cor(rl, color))
            canv.rect(105, y, 7, 7, stroke=0, fill=1)
            _draw_text(canv, 118, y, f"{label}: {value:.0f}", 6.3, BRAND["text"], False)
            y -= 12

    return _canvas_flowable(rl, width, height, draw)


def _dashboard_visual_page(rl, indicadores: dict, ocorrencias: list[Ocorrencia], width: float) -> list:
    spacer = rl["Spacer"]
    page_break = rl["PageBreak"]
    absolutos = indicadores["absolutos"]
    kpis = indicadores["kpis"]
    cards = [
        ("Eficiencia", f"{kpis['eficiencia']:.0%}", BRAND["blue"]),
        ("Aderencia", f"{kpis['aderencia']:.0%}", BRAND["green"]),
        ("Backlog", f"{absolutos['hh_atrasado']:.1f} HH", BRAND["red"]),
        ("Cancelamento", f"{kpis['cancelamento']:.0%}", BRAND["gray"]),
        ("HH Planejado", f"{absolutos['hh_planejado']:.1f}", BRAND["dark"]),
        ("HH Executado", f"{absolutos['hh_executado']:.1f}", BRAND["green"]),
        ("HH Reprogramado", f"{absolutos['hh_reprogramado']:.1f}", BRAND["copper"]),
        ("Atividades", str(absolutos["total_atividades"]), BRAND["purple"]),
    ]

    por_semana: dict[int, float] = defaultdict(float)
    por_status: Counter[str] = Counter()
    por_disciplina: dict[str, float] = defaultdict(float)
    por_equipamento: dict[str, float] = defaultdict(float)
    for oc in ocorrencias:
        plano = oc.plano
        equipamento = plano.equipamento if plano else None
        status = status_ocorrencia(oc.status, oc.ano, oc.semana)
        por_semana[oc.semana] += oc.hh_previsto or 0.0
        por_status[status] += 1
        por_disciplina[plano.disciplina if plano else "-"] += oc.hh_previsto or 0.0
        por_equipamento[equipamento.codigo if equipamento else "-"] += oc.hh_previsto or 0.0

    semanas = [(f"S{i}", por_semana.get(i, 0.0)) for i in range(1, 53)]
    disciplina_top = sorted(por_disciplina.items(), key=lambda item: item[1], reverse=True)
    equipamento_top = sorted(por_equipamento.items(), key=lambda item: item[1], reverse=True)
    status_data = [(status, count, STATUS_CORES.get(status, BRAND["gray"])) for status, count in por_status.items()]

    half = (width - 8) / 2
    return [
        _card_grid(rl, cards, width, 112),
        spacer(1, 8),
        _bar_chart(rl, "HH planejado por semana", semanas, width, 178, BRAND["blue"], max_items=52),
        spacer(1, 8),
        rl["Table"](
            [[
                _donut_chart(rl, "Status das ocorrencias", status_data, half, 150),
                _horizontal_bar_chart(rl, "HH por disciplina", disciplina_top, half, 150, BRAND["purple"], max_items=6),
            ]],
            colWidths=[half, half],
        ),
        spacer(1, 8),
        _horizontal_bar_chart(rl, "Equipamentos com maior HH", equipamento_top, width, 155, BRAND["dark"], max_items=10),
        page_break(),
    ]


def gerar_pdf_dashboard(ano: int, disciplinas: list[str] | None = None, tipos: list[str] | None = None, areas: list[str] | None = None) -> bytes:
    rl = _rl()
    styles = _styles(rl)
    buffer = BytesIO()
    doc = _doc(rl, buffer, rl["A4"], "Dashboard Executivo PlanejAI")
    story = _header(
        rl,
        styles,
        "Dashboard Executivo - PlanejAI",
        _filtros_texto(Ano=ano, Disciplina=disciplinas or [], Tipo=tipos or [], Area=areas or []),
    )

    indicadores = calcular_indicadores(ano, disciplinas or [], tipos or [], areas or [])
    kpis = indicadores["kpis"]
    absolutos = indicadores["absolutos"]
    ocorrencias = _query_ocorrencias_dashboard(ano, disciplinas or [], tipos or [], areas or [])

    story.extend(_dashboard_visual_page(rl, indicadores, ocorrencias, doc.width))

    story.append(rl["Paragraph"]("Tabelas de consulta", styles["title"]))
    story.append(rl["Paragraph"]("Indicadores principais", styles["section"]))
    kpi_data = [
        ["Indicador", "Valor", "Indicador", "Valor"],
        ["Eficiencia", f"{kpis['eficiencia']:.0%}", "Aderencia", f"{kpis['aderencia']:.0%}"],
        ["Backlog", f"{absolutos['hh_atrasado']:.1f} HH", "Cancelamento", f"{kpis['cancelamento']:.0%}"],
        ["HH Planejado", f"{absolutos['hh_planejado']:.1f}", "HH Executado", f"{absolutos['hh_executado']:.1f}"],
        ["HH Reprogramado", f"{absolutos['hh_reprogramado']:.1f}", "Atividades", str(absolutos["total_atividades"])],
    ]
    story.append(_table(rl, kpi_data, font_size=8))

    por_status = Counter(status_ocorrencia(oc.status, oc.ano, oc.semana) for oc in ocorrencias)
    por_disciplina: dict[str, float] = defaultdict(float)
    por_semana: dict[int, float] = defaultdict(float)
    por_equipamento: dict[str, float] = defaultdict(float)
    for oc in ocorrencias:
        plano = oc.plano
        equipamento = plano.equipamento if plano else None
        por_disciplina[plano.disciplina if plano else "-"] += oc.hh_previsto or 0.0
        por_semana[oc.semana] += oc.hh_previsto or 0.0
        por_equipamento[equipamento.codigo if equipamento else "-"] += oc.hh_previsto or 0.0

    story.append(rl["Paragraph"]("Alertas executivos", styles["section"]))
    semana_top = sorted(por_semana.items(), key=lambda item: item[1], reverse=True)[:6]
    equipamento_top = sorted(por_equipamento.items(), key=lambda item: item[1], reverse=True)[:6]
    alertas = [
        ["Semanas mais carregadas", "HH", "Equipamentos com maior HH", "HH"],
    ]
    max_linhas = max(len(semana_top), len(equipamento_top), 1)
    for i in range(max_linhas):
        s = semana_top[i] if i < len(semana_top) else ("-", 0)
        e = equipamento_top[i] if i < len(equipamento_top) else ("-", 0)
        alertas.append([f"S{s[0]}" if s[0] != "-" else "-", f"{s[1]:.1f}", e[0], f"{e[1]:.1f}"])
    story.append(_table(rl, alertas, font_size=7))

    story.append(rl["Paragraph"]("Composicao", styles["section"]))
    composicao = [["Status", "Qtd.", "Disciplina", "HH"]]
    disciplina_top = sorted(por_disciplina.items(), key=lambda item: item[1], reverse=True)
    status_items = list(por_status.items())
    max_linhas = max(len(status_items), len(disciplina_top), 1)
    for i in range(max_linhas):
        status = status_items[i] if i < len(status_items) else ("-", 0)
        disciplina_item = disciplina_top[i] if i < len(disciplina_top) else ("-", 0)
        composicao.append([status[0], str(status[1]), disciplina_item[0], f"{disciplina_item[1]:.1f}"])
    story.append(_table(rl, composicao, font_size=7))

    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_backlog(ano: int) -> bytes:
    rl = _rl()
    styles = _styles(rl)
    buffer = BytesIO()
    doc = _doc(rl, buffer, rl["A4"], "Backlog e Atrasos PlanejAI")
    story = _header(rl, styles, "Backlog e Atrasos - PlanejAI", _filtros_texto(Ano=ano))

    ocorrencias = [
        oc for oc in _query_ocorrencias(ano)
        if status_ocorrencia(oc.status, oc.ano, oc.semana) == "Atrasado"
    ]
    total_hh = sum(oc.hh_previsto or 0.0 for oc in ocorrencias)
    story.append(rl["Paragraph"](f"Total atrasado: {len(ocorrencias)} ocorrencia(s) | {total_hh:.1f} HH", styles["section"]))
    data = [["Semana", "Equipamento", "Plano", "Disciplina", "HH", "Status"]]
    for oc in ocorrencias[:120]:
        plano = oc.plano
        equipamento = plano.equipamento if plano else None
        data.append([
            f"S{oc.semana}",
            equipamento.codigo if equipamento else "-",
            plano.nome if plano else "-",
            plano.disciplina if plano else "-",
            f"{oc.hh_previsto or 0.0:.1f}",
            status_ocorrencia(oc.status, oc.ano, oc.semana),
        ])
    if len(data) == 1:
        data.append(["-", "-", "Nenhuma ocorrencia atrasada encontrada.", "-", "-", "-"])
    story.append(_table(rl, data, font_size=6.5))
    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_ocorrencias_semana(ano: int, semana: int | str, equipamento_codigo: str | None = None) -> bytes:
    rl = _rl()
    styles = _styles(rl)
    buffer = BytesIO()
    doc = _doc(rl, buffer, rl["A4"], "Ocorrencias da Semana PlanejAI")
    story = _header(
        rl,
        styles,
        "Ocorrencias da Semana - PlanejAI",
        _filtros_texto(Ano=ano, Semana=semana, Equipamento=equipamento_codigo or "Todos"),
    )
    ocorrencias = _query_ocorrencias(ano, semana=semana, equipamento_codigo=equipamento_codigo)
    data = [["Semana", "Equipamento", "Plano", "Disciplina", "HH", "Status"]]
    for oc in ocorrencias[:160]:
        plano = oc.plano
        equipamento = plano.equipamento if plano else None
        data.append([
            f"S{oc.semana}",
            equipamento.codigo if equipamento else "-",
            plano.nome if plano else "-",
            plano.disciplina if plano else "-",
            f"{oc.hh_previsto or 0.0:.1f}",
            status_ocorrencia(oc.status, oc.ano, oc.semana),
        ])
    if len(data) == 1:
        data.append(["-", "-", "Nenhuma ocorrencia encontrada para os filtros.", "-", "-", "-"])
    story.append(_table(rl, data, font_size=6.5))
    doc.build(story)
    return buffer.getvalue()


def _planos_mapa(ano: int, equipamento_codigo: str | None, disciplina: str | None) -> tuple[list[Plano], dict[int, list[Ocorrencia]]]:
    session = SessionLocal()
    try:
        query_planos = (
            session.query(Plano)
            .options(joinedload(Plano.equipamento))
            .filter(Plano.status == "Ativo")
        )
        if equipamento_codigo:
            query_planos = query_planos.join(Equipamento, Plano.equipamento_id == Equipamento.id).filter(Equipamento.codigo == equipamento_codigo)
        if disciplina and disciplina != "Todas":
            query_planos = query_planos.filter(Plano.disciplina == disciplina)
        planos = query_planos.order_by(Plano.nome).all()
        plano_ids = [plano.id for plano in planos]
        if not plano_ids:
            return [], {}
        ocorrencias = (
            session.query(Ocorrencia)
            .filter(Ocorrencia.ano == ano, Ocorrencia.plano_id.in_(plano_ids))
            .all()
        )
        por_plano: dict[int, list[Ocorrencia]] = defaultdict(list)
        for oc in ocorrencias:
            por_plano[oc.plano_id].append(oc)
        return planos, por_plano
    finally:
        session.close()


def gerar_pdf_mapa_52w(ano: int, equipamento_codigo: str | None = None, disciplina: str | None = None) -> bytes:
    rl = _rl()
    styles = _styles(rl)
    buffer = BytesIO()
    doc = _doc(rl, buffer, rl["landscape"](rl["A4"]), "Mapa de 52 Semanas PlanejAI", margin_mm=5)
    story = _header(
        rl,
        styles,
        "Mapa de 52 Semanas - PlanejAI",
        _filtros_texto(Ano=ano, Equipamento=equipamento_codigo or "Todos", Disciplina=disciplina or "Todas"),
    )
    story.append(
        rl["Paragraph"](
            "Legenda: P=Programado | R=Realizado | RP=Reprogramado | C=Cancelado | A=Atrasado",
            styles["subtitle"],
        )
    )

    planos, ocorrencias_por_plano = _planos_mapa(ano, equipamento_codigo, disciplina)
    if not planos:
        story.append(rl["Paragraph"]("Nenhum plano ativo encontrado para os filtros selecionados.", styles["section"]))
        doc.build(story)
        return buffer.getvalue()

    page_break = rl["PageBreak"]
    table_style = rl["TableStyle"]
    colors = rl["colors"]
    table_cls = rl["Table"]
    paragraph = rl["Paragraph"]
    mm = rl["mm"]
    plano_width = 50 * mm
    week_width = 4.05 * mm
    col_widths = [plano_width] + [week_width] * 52
    linhas_por_pagina = 28

    for inicio in range(0, len(planos), linhas_por_pagina):
        bloco = planos[inicio:inicio + linhas_por_pagina]
        data = [["Plano"] + [f"S{i}" for i in range(1, 53)]]
        estilos = [
            ("BACKGROUND", (0, 0), (-1, 0), _hex_cor(rl, BRAND["dark"])),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 5.2),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 5.0),
            ("GRID", (0, 0), (-1, -1), 0.10, _hex_cor(rl, BRAND["border"])),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0.8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0.8),
            ("TOPPADDING", (0, 0), (-1, -1), 1.6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
        ]
        for row_index, plano in enumerate(bloco, start=1):
            equipamento = plano.equipamento
            label = f"{plano.nome or '-'}<br/><font color='{BRAND['muted']}'>{equipamento.codigo if equipamento else '-'} | {plano.disciplina or '-'}</font>"
            mapa = {oc.semana: oc for oc in ocorrencias_por_plano.get(plano.id, [])}
            row = [paragraph(label, styles["tiny"])]
            for semana in range(1, 53):
                oc = mapa.get(semana)
                if not oc:
                    row.append("")
                    continue
                status = status_ocorrencia(oc.status, oc.ano, oc.semana)
                row.append(paragraph(STATUS_SIGLAS.get(status, status[:1]), styles["tiny_center"]))
                estilos.append(("BACKGROUND", (semana, row_index), (semana, row_index), _hex_cor(rl, STATUS_CORES.get(status, BRAND["gray"]))))
                estilos.append(("TEXTCOLOR", (semana, row_index), (semana, row_index), colors.white))
            data.append(row)
        table = table_cls(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(table_style(estilos))
        story.append(table)
        if inicio + linhas_por_pagina < len(planos):
            story.append(page_break())

    doc.build(story)
    return buffer.getvalue()
