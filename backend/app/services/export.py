"""Сборка Markdown и PDF экспорта поездки."""

from __future__ import annotations

import os
import re
from pathlib import Path

from fpdf import FPDF

from ..models import Trip

PHASE_ORDER = ["brief", "itinerary", "budget", "checklist"]

_FONT_CANDIDATES = [
    os.environ.get("PDF_FONT_PATH", ""),
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def build_trip_markdown(trip: Trip) -> str:
    parts = [
        f"# {trip.name}",
        "",
        f"> {trip.brief.strip()}",
        "",
        "_Черновик от Travel Agent. Цены и адреса ориентировочные — проверяйте перед поездкой._",
        "",
    ]
    by_phase = {a.phase: a for a in trip.artifacts}
    for phase in PHASE_ORDER:
        artifact = by_phase.get(phase)
        if artifact is None:
            continue
        parts.append("---")
        parts.append("")
        parts.append(artifact.content.strip())
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def _find_font() -> Path:
    for raw in _FONT_CANDIDATES:
        if not raw:
            continue
        path = Path(raw)
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Не найден TTF-шрифт для PDF. Установите Arial/DejaVu или задайте PDF_FONT_PATH."
    )


def _strip_md(text: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^\s*[-*]\s+\[[ xX]\]\s*", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    return text.strip()


def build_trip_pdf(trip: Trip) -> bytes:
    font_path = _find_font()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.add_font("TripFont", fname=str(font_path))
    pdf.set_font("TripFont", size=16)
    pdf.multi_cell(0, 10, trip.name)
    pdf.ln(2)
    pdf.set_font("TripFont", size=10)
    pdf.multi_cell(0, 6, trip.brief.strip())
    pdf.ln(2)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0,
        5,
        "Черновик от Travel Agent. Цены и адреса ориентировочные — проверяйте перед поездкой.",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    by_phase = {a.phase: a for a in trip.artifacts}
    for phase in PHASE_ORDER:
        artifact = by_phase.get(phase)
        if artifact is None:
            continue
        pdf.set_font("TripFont", size=13)
        pdf.multi_cell(0, 8, artifact.title)
        pdf.ln(1)
        pdf.set_font("TripFont", size=10)
        body = _strip_md(artifact.content)
        for block in body.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            pdf.multi_cell(0, 5, block)
            pdf.ln(2)
        pdf.ln(3)

    out = pdf.output()
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")
