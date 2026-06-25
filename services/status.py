from __future__ import annotations

from datetime import date


STATUS_ATIVOS = {"Programado", "Reprogramado"}


def status_ocorrencia(status: str | None, ano: int, semana: int, hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    status_base = status or "Programado"
    if status_base in STATUS_ATIVOS and ano == hoje.year and semana < hoje.isocalendar()[1]:
        return "Atrasado"
    return status_base
