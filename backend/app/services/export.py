"""Сборка Markdown-экспорта поездки."""

from ..models import Trip

PHASE_ORDER = ["brief", "itinerary", "budget", "checklist"]


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
