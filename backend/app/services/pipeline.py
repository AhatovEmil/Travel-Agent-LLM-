"""Оркестрация конвейера агента: 6 фаз от идеи до проверенного кода."""

import logging

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Artifact, GeneratedFile, Project
from .engine import get_engine
from .verifier import verify_files

logger = logging.getLogger(__name__)

PHASES = ["vision", "roadmap", "architecture", "structure", "code", "verify"]

PHASE_TITLES = {
    "vision": "Project Vision",
    "roadmap": "Roadmap",
    "architecture": "Architecture",
    "structure": "Project Structure",
    "code": "Code Generation",
    "verify": "Verification Report",
}


def _save_artifact(db: Session, project: Project, phase: str, content: str) -> None:
    db.add(
        Artifact(
            project_id=project.id,
            phase=phase,
            title=PHASE_TITLES[phase],
            content=content,
        )
    )
    db.commit()


def run_pipeline(project_id: int) -> None:
    """Выполняется в фоне. Ошибки не поднимаются наружу — фиксируются в статусе проекта."""
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if project is None:
            return

        # Повторный запуск: очищаем прошлые результаты.
        for artifact in list(project.artifacts):
            db.delete(artifact)
        for file in list(project.files):
            db.delete(file)
        project.status = "running"
        project.error = ""
        db.commit()

        engine = get_engine()

        generators = {
            "vision": engine.generate_vision,
            "roadmap": engine.generate_roadmap,
            "architecture": engine.generate_architecture,
            "structure": engine.generate_structure,
        }
        for phase in ["vision", "roadmap", "architecture", "structure"]:
            project.current_phase = phase
            db.commit()
            _save_artifact(db, project, phase, generators[phase](project.name, project.idea))

        project.current_phase = "code"
        db.commit()
        files = engine.generate_code(project.name, project.idea)
        for path, content in files.items():
            db.add(GeneratedFile(project_id=project.id, path=path, content=content))
        db.commit()
        _save_artifact(
            db,
            project,
            "code",
            "# Code Generation\n\nСгенерированы файлы:\n\n"
            + "\n".join(f"- `{p}`" for p in sorted(files)),
        )

        project.current_phase = "verify"
        db.commit()
        ok, report = verify_files(files)
        _save_artifact(db, project, "verify", report)

        if ok:
            project.status = "completed"
        else:
            project.status = "failed"
            project.error = "Верификация сгенерированного кода не пройдена, см. отчёт verify."
        db.commit()
    except Exception as exc:  # noqa: BLE001 — фоновая задача обязана зафиксировать любую ошибку
        logger.exception("Pipeline failed for project %s", project_id)
        db.rollback()
        project = db.get(Project, project_id)
        if project is not None:
            project.status = "failed"
            project.error = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()
