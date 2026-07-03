import io
import zipfile

from ..models import Project


def build_zip(project: Project) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for artifact in project.artifacts:
            archive.writestr(f"docs/{artifact.phase.upper()}.md", artifact.content)
        for file in project.files:
            archive.writestr(file.path, file.content)
    return buffer.getvalue()
