from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Project, User
from ..schemas import ArtifactOut, GeneratedFileOut, ProjectCreate, ProjectOut
from ..services.packaging import build_zip
from ..services.pipeline import run_pipeline

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_owned_project(project_id: int, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = Project(owner_id=current_user.id, name=payload.name, idea=payload.idea)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Project).where(Project.owner_id == current_user.id).order_by(Project.id.desc())
    ).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_project(project_id, current_user, db)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(project_id, current_user, db)
    db.delete(project)
    db.commit()


@router.post("/{project_id}/run", response_model=ProjectOut, status_code=status.HTTP_202_ACCEPTED)
def run_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(project_id, current_user, db)
    if project.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Pipeline is already running")
    project.status = "running"
    project.current_phase = "vision"
    project.error = ""
    db.commit()
    db.refresh(project)
    background_tasks.add_task(run_pipeline, project.id)
    return project


@router.get("/{project_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(project_id, current_user, db)
    return project.artifacts


@router.get("/{project_id}/files", response_model=list[GeneratedFileOut])
def list_files(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(project_id, current_user, db)
    return project.files


@router.get("/{project_id}/download")
def download_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(project_id, current_user, db)
    if project.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Project is not completed yet")
    payload = build_zip(project)
    filename = f"project-{project.id}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
