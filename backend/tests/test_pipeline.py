import ast
import io
import time
import zipfile

from app.services.engine import TemplateEngine, detect_entities
from app.services.verifier import verify_files

IDEA = {"name": "Cloth Market", "idea": "Хочу сделать маркетплейс одежды с заказами"}
PHASES = ["vision", "roadmap", "architecture", "structure", "code", "verify"]


def _run_to_completion(client, headers, project_id, timeout=30):
    response = client.post(f"/api/projects/{project_id}/run", headers=headers)
    assert response.status_code == 202, response.text
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/projects/{project_id}", headers=headers).json()["status"]
        if status in ("completed", "failed"):
            return status
        time.sleep(0.2)
    raise AssertionError("Pipeline did not finish in time")


def test_detect_entities():
    assert detect_entities("маркетплейс одежды") == ["product", "order"]
    assert detect_entities("блог о котах") == ["post", "comment"]
    assert detect_entities("что-то непонятное") == ["item"]


def test_template_engine_generates_valid_python():
    files = TemplateEngine().generate_code("Test App", "трекер задач")
    assert "app/main.py" in files
    for path, content in files.items():
        if path.endswith(".py"):
            ast.parse(content)


def test_verifier_flags_broken_code():
    ok, report = verify_files({"app/main.py": "def broken(:"})
    assert not ok
    assert "SyntaxError" in report


def test_full_pipeline_and_download(client, auth_headers):
    project_id = client.post("/api/projects", json=IDEA, headers=auth_headers).json()["id"]

    status = _run_to_completion(client, auth_headers, project_id)
    assert status == "completed"

    artifacts = client.get(f"/api/projects/{project_id}/artifacts", headers=auth_headers).json()
    assert [a["phase"] for a in artifacts] == PHASES

    files = client.get(f"/api/projects/{project_id}/files", headers=auth_headers).json()
    paths = {f["path"] for f in files}
    assert {"app/main.py", "requirements.txt", "Dockerfile", "README.md"} <= paths

    download = client.get(f"/api/projects/{project_id}/download", headers=auth_headers)
    assert download.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(download.content))
    names = set(archive.namelist())
    assert "app/main.py" in names
    assert "docs/VISION.md" in names


def test_download_before_completion_conflict(client, auth_headers):
    project_id = client.post("/api/projects", json=IDEA, headers=auth_headers).json()["id"]
    response = client.get(f"/api/projects/{project_id}/download", headers=auth_headers)
    assert response.status_code == 409
