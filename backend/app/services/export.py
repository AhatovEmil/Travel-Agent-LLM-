"""Сборка Markdown и PDF экспорта поездки."""

from __future__ import annotations

import os
import re
from pathlib import Path

from fpdf import FPDF

from ..models import Trip
from .parse import extract_days_count, extract_destination, parse_itinerary_days

PHASE_ORDER = ["brief", "itinerary", "budget", "checklist"]

# Coastal palette
TEAL = (13, 122, 122)
TEAL_DARK = (8, 90, 92)
TEAL_SOFT = (220, 236, 238)
TEAL_MID = (90, 168, 170)
SAND = (228, 212, 188)
SUNSET = (212, 137, 106)
INK = (10, 42, 50)
MUTED = (90, 116, 128)
WHITE = (255, 255, 255)
LINE = (200, 214, 220)
CARD = (248, 251, 252)
PAGE_BG = (245, 249, 250)

_ROOT = Path(__file__).resolve().parents[3]
_IMAGE_DIR = _ROOT / "frontend" / "public" / "images"

_FONT_CANDIDATES = [
    (os.environ.get("PDF_FONT_PATH", ""), os.environ.get("PDF_FONT_BOLD_PATH", "")),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
    (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", ""),
]

_SEA = ("море", "пляж", "батуми", "сочи", "крым", "ялта", "бали", "пхукет", "beach", "sea")
_CITY = ("париж", "рим", "лондон", "берлин", "москв", "петербург", "стамбул", "город", "музей")
_NATURE = ("алтай", "горы", "природ", "байкал", "кавказ", "озеро", "mountain", "hiking")


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


def _find_fonts() -> tuple[Path, Path | None]:
    for regular_raw, bold_raw in _FONT_CANDIDATES:
        if not regular_raw:
            continue
        regular = Path(regular_raw)
        if not regular.is_file():
            continue
        bold = Path(bold_raw) if bold_raw else None
        if bold is not None and not bold.is_file():
            bold = None
        return regular, bold
    raise FileNotFoundError(
        "Не найден TTF-шрифт для PDF. Установите Arial/DejaVu или задайте PDF_FONT_PATH."
    )


def _cover_image(destination: str, name: str, brief: str) -> Path | None:
    text = f"{destination} {name} {brief}".lower()
    if any(w in text for w in _SEA):
        name_key = "dest-sea.jpg"
    elif any(w in text for w in _NATURE):
        name_key = "dest-nature.jpg"
    elif any(w in text for w in _CITY):
        name_key = "dest-city.jpg"
    else:
        name_key = "dash-horizon.jpg"
    path = _IMAGE_DIR / name_key
    return path if path.is_file() else None


def _strip_inline_md(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _shorten(text: str, max_chars: int = 220) -> str:
    text = _strip_inline_md(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rsplit(" ", 1)[0]
    return (cut or text[: max_chars - 1]) + "…"


def _brief_summary(brief: str) -> str:
    lines = [ln.strip() for ln in brief.strip().splitlines() if ln.strip()]
    joined = " ".join(lines) if lines else brief.strip()
    return _shorten(joined, 260)


def _day_number(title: str, index: int) -> str:
    match = re.search(r"День\s*(\d+)", title, re.I)
    if match:
        return match.group(1)
    return str(index + 1)


def _day_subtitle(title: str) -> str:
    # "День 1 — 2026-07-12 — обзор" → keep human part
    parts = re.split(r"\s*[—–-]\s*", title, maxsplit=2)
    if len(parts) >= 3:
        return parts[-1].strip()
    if len(parts) == 2 and not re.match(r"\d{4}-\d{2}-\d{2}", parts[1]):
        return parts[1].strip()
    return title


def _parse_md_blocks(content: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for raw in content.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if re.match(r"^#{1,3}\s+", line):
            blocks.append(("heading", _strip_inline_md(re.sub(r"^#{1,3}\s+", "", line))))
            continue
        check = re.match(r"^\s*[-*]\s+\[[ xX]\]\s*(.+)$", line)
        if check:
            blocks.append(("check", _strip_inline_md(check.group(1))))
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            text = _strip_inline_md(bullet.group(1))
            kind = "total" if re.search(r"итого|всего|total", text, re.I) else "bullet"
            blocks.append((kind, text))
            continue
        if line.lstrip().startswith(">"):
            blocks.append(("para", _strip_inline_md(re.sub(r"^\s*>\s?", "", line))))
            continue
        text = _strip_inline_md(re.sub(r"^#{1,6}\s*", "", line))
        kind = "total" if re.search(r"итого|всего|total", text, re.I) else "para"
        blocks.append((kind, text))
    return blocks


class TripPDF(FPDF):
    def __init__(self, trip_name: str):
        super().__init__()
        self.trip_name = trip_name
        self._has_bold = False
        self.set_auto_page_break(auto=True, margin=24)
        self.set_margins(16, 18, 16)

    def register_fonts(self, regular: Path, bold: Path | None) -> None:
        self.add_font("TripFont", fname=str(regular))
        if bold is not None:
            self.add_font("TripFont", style="B", fname=str(bold))
            self._has_bold = True

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_draw_color(*LINE)
        self.set_line_width(0.25)
        self.line(16, self.get_y(), self.w - 16, self.get_y())
        self.ln(2)
        self.set_font("TripFont", size=8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Travel Agent  ·  {self.trip_name}  ·  {self.page_no()}", align="C")
        self.set_text_color(*INK)

    def font_regular(self, size: float) -> None:
        self.set_font("TripFont", size=size)

    def font_bold(self, size: float) -> None:
        if self._has_bold:
            self.set_font("TripFont", style="B", size=size)
        else:
            self.set_font("TripFont", size=size)

    def ensure_space(self, h: float) -> None:
        if self.get_y() + h > self.page_break_trigger:
            self.add_page()

    def paint_page_wash(self) -> None:
        self.set_fill_color(*PAGE_BG)
        self.rect(0, 0, self.w, self.h, style="F")

    def draw_waves(self, y_base: float, color: tuple[int, int, int], amp: float = 8) -> None:
        """Simple scalloped band using overlapping ellipses."""
        self.set_fill_color(*color)
        x = -10
        while x < self.w + 20:
            self.ellipse(x, y_base, 36, amp * 2, style="F")
            x += 22

    def pill(self, text: str, fill: tuple[int, int, int], text_color: tuple[int, int, int] = WHITE) -> None:
        self.font_bold(9)
        w = self.get_string_width(text) + 10
        h = 7
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(*fill)
        self.rounded_rect(x, y, w, h, 2, style="F")
        self.set_text_color(*text_color)
        self.set_xy(x, y + 1)
        self.cell(w, 5, text, align="C")
        self.set_xy(x + w + 4, y)
        self.set_text_color(*INK)

    def rounded_rect(self, x, y, w, h, r, style="") -> None:
        # fpdf2 has rounded_rect in recent versions; fallback to rect
        try:
            super().rounded_rect(x, y, w, h, r, style=style)
        except Exception:
            self.rect(x, y, w, h, style=style)

    def muted_box(self, text: str) -> None:
        self.ensure_space(16)
        x, w = self.l_margin, self.epw
        y0 = self.get_y()
        self.set_xy(x + 5, y0 + 3)
        self.font_regular(9)
        self.set_text_color(*MUTED)
        self.multi_cell(w - 8, 4.8, text)
        y1 = self.get_y() + 3
        self.set_fill_color(*TEAL_SOFT)
        self.rounded_rect(x, y0, w, max(y1 - y0, 12), 3, style="F")
        self.set_fill_color(*SUNSET)
        self.rect(x, y0, 2.2, max(y1 - y0, 12), style="F")
        self.set_xy(x + 5, y0 + 3)
        self.set_text_color(*MUTED)
        self.multi_cell(w - 8, 4.8, text)
        self.set_y(y1 + 2)
        self.set_text_color(*INK)

    def section_banner(self, title: str, subtitle: str = "") -> None:
        self.ensure_space(28)
        x, w = self.l_margin, self.epw
        y = self.get_y()
        self.set_fill_color(*TEAL)
        self.rounded_rect(x, y, w, 18 if subtitle else 14, 3, style="F")
        self.set_fill_color(*SUNSET)
        self.rect(x, y, 3.5, 18 if subtitle else 14, style="F")
        self.set_xy(x + 8, y + 3)
        self.set_text_color(*WHITE)
        self.font_bold(13)
        self.cell(0, 6, title)
        if subtitle:
            self.set_xy(x + 8, y + 10)
            self.font_regular(8)
            self.cell(0, 4, subtitle)
        self.set_y(y + (22 if subtitle else 18))
        self.set_text_color(*INK)

    def day_header(self, title: str, date_str: str | None, index: int) -> None:
        self.ensure_space(28)
        x, w = self.l_margin, self.epw
        y = self.get_y()
        num = _day_number(title, index)
        subtitle = _day_subtitle(title)

        # card background
        self.set_fill_color(*TEAL_SOFT)
        self.rounded_rect(x, y, w, 22, 4, style="F")

        # big day badge
        self.set_fill_color(*TEAL)
        self.rounded_rect(x + 3, y + 3, 16, 16, 3, style="F")
        self.set_text_color(*WHITE)
        self.font_bold(14)
        self.set_xy(x + 3, y + 6)
        self.cell(16, 8, num, align="C")

        self.set_xy(x + 24, y + 4)
        self.set_text_color(*TEAL_DARK)
        self.font_bold(12)
        self.cell(0, 6, f"День {num}" + (f"  ·  {date_str}" if date_str else ""))
        self.set_xy(x + 24, y + 12)
        self.font_regular(9)
        self.set_text_color(*MUTED)
        self.cell(0, 5, subtitle[:70])
        self.set_y(y + 26)
        self.set_text_color(*INK)

    def slot_row(self, start: str, end: str, place: str, body: str, *, last: bool = False) -> None:
        time_label = f"{start}–{end}"
        self.ensure_space(26)
        x = self.l_margin
        y0 = self.get_y()
        rail_x = x + 4

        # measure content height roughly
        self.set_xy(x + 34, y0 + 3)
        self.font_bold(10)
        # placeholder measure via multi_cell in off mode isn't easy; draw then measure

        # timeline rail
        self.set_fill_color(*TEAL)
        self.ellipse(rail_x - 1.6, y0 + 5, 5, 5, style="F")
        self.set_fill_color(*WHITE)
        self.ellipse(rail_x - 0.4, y0 + 6.2, 2.6, 2.6, style="F")

        # card
        card_x = x + 12
        card_w = self.epw - 12
        self.set_xy(card_x + 4, y0 + 3)
        self.font_bold(9)
        self.set_text_color(*SUNSET)
        self.cell(30, 5, time_label)
        self.set_text_color(*INK)
        self.font_bold(10)
        self.set_xy(card_x + 36, y0 + 2.5)
        self.multi_cell(card_w - 40, 5.5, place)
        y_mid = self.get_y()
        if body:
            self.set_xy(card_x + 4, y_mid + 0.5)
            self.font_regular(8.5)
            self.set_text_color(*MUTED)
            self.multi_cell(card_w - 8, 4.2, _shorten(body, 180))
            self.set_text_color(*INK)
        y1 = self.get_y() + 3
        h = max(y1 - y0, 16)

        # paint card behind (redraw order: bg then content)
        self.set_fill_color(*CARD)
        self.set_draw_color(*LINE)
        self.set_line_width(0.2)
        self.rounded_rect(card_x, y0, card_w, h, 3, style="FD")
        self.set_fill_color(*SAND)
        self.rect(card_x, y0, 2.5, h, style="F")

        # redraw content on top of card
        self.set_xy(card_x + 4, y0 + 3)
        self.font_bold(9)
        self.set_text_color(*SUNSET)
        self.cell(30, 5, time_label)
        self.set_text_color(*INK)
        self.font_bold(10)
        self.set_xy(card_x + 36, y0 + 2.5)
        self.multi_cell(card_w - 40, 5.5, place)
        y_mid = self.get_y()
        if body:
            self.set_xy(card_x + 4, y_mid + 0.5)
            self.font_regular(8.5)
            self.set_text_color(*MUTED)
            self.multi_cell(card_w - 8, 4.2, _shorten(body, 180))
            self.set_text_color(*INK)

        # connector line to next slot
        if not last:
            self.set_draw_color(*TEAL_MID)
            self.set_line_width(0.7)
            self.line(rail_x + 0.9, y0 + 10, rail_x + 0.9, y0 + h + 2)

        self.set_y(y0 + h + 4)

    def checkbox_line(self, text: str, *, alt: bool = False) -> None:
        self.ensure_space(10)
        x, y = self.l_margin, self.get_y()
        h = 9
        if alt:
            self.set_fill_color(*TEAL_SOFT)
            self.rounded_rect(x, y, self.epw, h, 2, style="F")
        self.set_draw_color(*TEAL)
        self.set_line_width(0.45)
        self.rounded_rect(x + 2, y + 2.2, 4.2, 4.2, 0.8)
        self.set_xy(x + 9, y + 1.5)
        self.font_regular(10)
        self.set_text_color(*INK)
        self.cell(self.epw - 10, 6, _shorten(text, 90))
        self.set_y(y + h + 1)

    def bullet_line(self, text: str) -> None:
        self.ensure_space(8)
        self.font_regular(10)
        self.set_text_color(*INK)
        self.set_fill_color(*TEAL)
        x, y = self.get_x(), self.get_y()
        self.ellipse(x + 1, y + 2, 2.2, 2.2, style="F")
        self.set_xy(x + 6, y)
        self.multi_cell(self.epw - 6, 5.2, text)
        self.ln(0.8)

    def render_md_section(self, content: str, *, as_checklist: bool = False) -> None:
        alt = False
        for kind, text in _parse_md_blocks(content):
            if not text:
                continue
            if kind == "heading":
                self.ensure_space(12)
                self.font_bold(11)
                self.set_text_color(*TEAL)
                self.multi_cell(0, 7, text)
                self.ln(1)
                self.set_text_color(*INK)
            elif kind == "check" or (as_checklist and kind in ("bullet", "para")):
                self.checkbox_line(text, alt=alt)
                alt = not alt
            elif kind == "total":
                self.ensure_space(12)
                x, y = self.l_margin, self.get_y()
                self.set_fill_color(*TEAL)
                self.rounded_rect(x, y, self.epw, 10, 3, style="F")
                self.set_xy(x + 4, y + 2)
                self.font_bold(10)
                self.set_text_color(*WHITE)
                self.cell(0, 6, text)
                self.set_y(y + 13)
                self.set_text_color(*INK)
            elif kind == "bullet":
                self.bullet_line(text)
            else:
                self.font_regular(10)
                self.multi_cell(0, 5.5, text)
                self.ln(1)

    def toc_row(self, index: int, label: str, hint: str = "") -> None:
        self.ensure_space(14)
        x, y = self.l_margin, self.get_y()
        self.set_fill_color(*CARD)
        self.rounded_rect(x, y, self.epw, 12, 3, style="F")
        self.set_fill_color(*TEAL)
        self.rounded_rect(x + 2, y + 2, 8, 8, 2, style="F")
        self.set_text_color(*WHITE)
        self.font_bold(9)
        self.set_xy(x + 2, y + 3)
        self.cell(8, 6, str(index), align="C")
        self.set_xy(x + 13, y + 2)
        self.set_text_color(*INK)
        self.font_bold(10)
        self.cell(0, 5, label)
        if hint:
            self.set_xy(x + 13, y + 7)
            self.font_regular(7.5)
            self.set_text_color(*MUTED)
            self.cell(0, 3.5, hint)
        self.set_y(y + 14)
        self.set_text_color(*INK)


def build_trip_pdf(trip: Trip) -> bytes:
    regular, bold = _find_fonts()
    by_phase = {a.phase: a for a in trip.artifacts}
    destination = extract_destination(trip.brief, trip.name)
    days_count = extract_days_count(trip.brief)
    start = trip.start_date.isoformat() if trip.start_date else None

    itinerary = by_phase.get("itinerary")
    days = (
        parse_itinerary_days(itinerary.content, start_date=trip.start_date)
        if itinerary
        else []
    )
    budget = by_phase.get("budget")
    checklist = by_phase.get("checklist")
    brief_art = by_phase.get("brief")
    cover_img = _cover_image(destination, trip.name, trip.brief)

    pdf = TripPDF(trip.name)
    pdf.register_fonts(regular, bold)

    # ——— Cover ———
    pdf.add_page()
    # sky wash
    pdf.set_fill_color(180, 214, 222)
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")
    pdf.set_fill_color(*TEAL_DARK)
    pdf.rect(0, 0, pdf.w, 8, style="F")

    if cover_img is not None:
        # full-bleed-ish hero photo
        pdf.image(str(cover_img), x=0, y=8, w=pdf.w, h=92)
        # dark veil for title readability
        pdf.set_fill_color(8, 40, 48)
        # approximate translucent veil via solid dark band at bottom of image
        pdf.set_fill_color(10, 42, 50)
        pdf.rect(0, 68, pdf.w, 32, style="F")
        pdf.draw_waves(95, (180, 214, 222), amp=10)
        title_y = 72
    else:
        pdf.set_fill_color(*TEAL)
        pdf.rect(0, 8, pdf.w, 88, style="F")
        pdf.set_fill_color(*SUNSET)
        pdf.ellipse(pdf.w - 55, 18, 38, 38, style="F")
        pdf.set_fill_color(255, 230, 180)
        pdf.ellipse(pdf.w - 48, 24, 24, 24, style="F")
        pdf.draw_waves(88, (180, 214, 222), amp=12)
        title_y = 28

    pdf.set_xy(18, title_y)
    pdf.set_text_color(*WHITE)
    pdf.font_regular(10)
    pdf.cell(0, 5, "TRAVEL AGENT")
    pdf.set_xy(18, title_y + 7)
    pdf.font_bold(22)
    pdf.multi_cell(pdf.w - 40, 9, trip.name)

    pdf.set_y(108)
    pdf.set_text_color(*INK)
    # meta pills
    pdf.set_x(18)
    pdf.pill(destination[:28], TEAL)
    if start:
        pdf.pill(f"с {start}", SUNSET)
    pdf.pill(f"{days_count} дн.", TEAL_DARK)
    pdf.ln(12)

    pdf.set_x(18)
    pdf.font_regular(10)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.epw - 4, 5.5, _brief_summary(trip.brief))
    pdf.ln(4)
    pdf.muted_box(
        "Черновик: цены, адреса и часы работы ориентировочные — сверьте перед поездкой."
    )

    if brief_art and brief_art.content.strip():
        pdf.ln(3)
        pdf.section_banner("Кратко о поездке", "главное из brief")
        shown = 0
        for kind, text in _parse_md_blocks(brief_art.content):
            if kind == "heading":
                continue
            if shown >= 6:
                break
            if kind in ("bullet", "check"):
                pdf.bullet_line(_shorten(text, 150))
            else:
                pdf.font_regular(9.5)
                pdf.set_text_color(*MUTED)
                pdf.multi_cell(0, 5, _shorten(text, 160))
                pdf.set_text_color(*INK)
                pdf.ln(1)
            shown += 1

    # ——— TOC ———
    pdf.add_page()
    pdf.paint_page_wash()
    pdf.set_y(18)
    pdf.section_banner("Маршрут документа", "куда смотреть")
    toc_i = 1
    if days:
        for day in days:
            hint = f"{len(day.get('slots') or [])} точек" if day.get("slots") else ""
            if day.get("date"):
                hint = f"{day['date']}" + (f" · {hint}" if hint else "")
            pdf.toc_row(toc_i, day["title"][:55], hint)
            toc_i += 1
    elif itinerary:
        pdf.toc_row(toc_i, "План по дням")
        toc_i += 1
    if budget:
        pdf.toc_row(toc_i, "Бюджет", "ориентиры по тратам")
        toc_i += 1
    if checklist:
        pdf.toc_row(toc_i, "Чеклист", "что взять с собой")

    # ——— Days ———
    if days:
        pdf.add_page()
        pdf.paint_page_wash()
        pdf.set_y(18)
        pdf.section_banner("План по дням", f"{len(days)} дн. · слоты по времени")
        for di, day in enumerate(days):
            pdf.day_header(day["title"], day.get("date"), di)
            slots = day.get("slots") or []
            if slots:
                for si, slot in enumerate(slots):
                    pdf.slot_row(
                        slot["start"],
                        slot["end"],
                        slot["place"],
                        slot.get("body") or "",
                        last=si == len(slots) - 1,
                    )
            else:
                body = day.get("content") or ""
                for kind, text in _parse_md_blocks(body):
                    if kind == "heading":
                        pdf.font_bold(10)
                        pdf.set_text_color(*TEAL)
                        pdf.multi_cell(0, 6, text)
                        pdf.set_text_color(*INK)
                        pdf.ln(1)
                    elif kind in ("bullet", "check"):
                        pdf.bullet_line(_shorten(text, 180))
                    else:
                        pdf.font_regular(9)
                        pdf.set_text_color(*MUTED)
                        pdf.multi_cell(0, 5, _shorten(text, 220))
                        pdf.set_text_color(*INK)
                        pdf.ln(1)
            pdf.ln(4)
            # soft page break between long days
            if di < len(days) - 1 and pdf.get_y() > pdf.h * 0.62:
                pdf.add_page()
                pdf.paint_page_wash()
                pdf.set_y(18)
    elif itinerary:
        pdf.add_page()
        pdf.paint_page_wash()
        pdf.set_y(18)
        pdf.section_banner("План по дням")
        pdf.render_md_section(itinerary.content)

    # ——— Budget ———
    if budget:
        pdf.add_page()
        pdf.paint_page_wash()
        pdf.set_y(18)
        pdf.section_banner("Бюджет", "цифры ориентировочные")
        pdf.render_md_section(budget.content)

    # ——— Checklist ———
    if checklist:
        pdf.add_page()
        pdf.paint_page_wash()
        pdf.set_y(18)
        pdf.section_banner("Чеклист", "распечатайте и отмечайте")
        pdf.render_md_section(checklist.content, as_checklist=True)

    out = pdf.output()
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")
