"""Тесты геопроверки мест в itinerary."""

from app.services.verify_places import (
    harden_itinerary,
    is_soft_place,
    mark_unverified_in_text,
    verify_itinerary_places,
)

ITIN = """## День 1 — 2026-07-12 — обзор

### 09:00–11:00 — Батумский бульвар
Прогулка.

### 11:30–13:00 — Музей единорогов Ноябрьска
Выставка.

### 14:00–15:00 — Кафе на набережной
Обед.

## Запасной план на плохую погоду
Кафе.
"""


def test_soft_places():
    assert is_soft_place("Кафе на набережной")
    assert is_soft_place("Прогулка по центру")
    assert not is_soft_place("Музей единорогов Ноябрьска")


def test_verify_finds_fake(monkeypatch):
    report = verify_itinerary_places(ITIN, "Батуми")
    assert "Музей единорогов Ноябрьска" in report["unverified_places"]
    assert report["soft_count"] >= 1


def test_mark_unverified():
    marked = mark_unverified_in_text(ITIN, ["Музей единорогов Ноябрьска"])
    assert "уточнить на месте" in marked
    assert "Батумский бульвар" in marked


def test_harden_marks_without_llm():
    text, report = harden_itinerary(ITIN, "Батуми", fix_fn=None)
    assert "уточнить на месте" in text
    assert report.get("marked") is True


def test_harden_with_llm_fix():
    def fix_fn(itinerary, destination, bad):
        assert "Музей единорогов Ноябрьска" in bad
        return """## День 1 — 2026-07-12 — обзор

### 09:00–11:00 — Батумский бульвар
Прогулка.

### 11:30–13:00 — Кафе в центре
Обед.

## Запасной план на плохую погоду
Кафе.
"""

    text, report = harden_itinerary(ITIN, "Батуми", fix_fn=fix_fn)
    assert "единорогов" not in text
    assert report.get("llm_fix_applied") is True
    assert "уточнить" not in text or report.get("marked") is False
