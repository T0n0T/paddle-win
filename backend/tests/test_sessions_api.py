from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import create_sessions_router
from app.server import create_app
from app.services.artifacts import ArtifactStore
from app.workbench import InMemorySessionStore, WorkbenchService


class InvalidPayloadLLMService:
    def generate_text(self, image_path: Path, prompt: str) -> str:
        del image_path, prompt
        return "not-json"


class ValidPayloadLLMService:
    def generate_text(self, image_path: Path, prompt: str) -> str:
        del image_path, prompt
        return (
            '{"form_json":{"title":"客户登记表","sections":[{"id":"basic","title":"基础信息"}],'
            '"fields":[{"id":"name","section_id":"basic","label":"姓名","type":"text","required":true}]},'
            '"html":"<form>v1</form>",'
            '"change_summary":{"user_intent":"初始化","applied":["生成首版"],"warnings":[],'
            '"unresolved":[],"touched_field_ids":[]}}'
        )


class FailingLLMService:
    def generate_text(self, image_path: Path, prompt: str) -> str:
        del image_path, prompt
        raise ValueError("upstream llm request failed")


class FakeOCRService:
    def run(self, image_path: Path) -> tuple[dict, list[dict]]:
        return (
            {"engine": "fake-ocr", "pages": 1, "image_name": image_path.name},
            [{"text": image_path.stem, "bbox": [], "block_type": "image"}],
        )


def make_image_upload() -> tuple[str, bytes, str]:
    return ("form.png", b"fake-image", "image/png")


def write_prompt_files(tmp_path: Path) -> tuple[Path, Path]:
    init_prompt_path = tmp_path / "workbench_init.md"
    init_prompt_path.write_text("OCR: {{OCR_JSON}}", encoding="utf-8")
    edit_prompt_path = tmp_path / "workbench_edit.md"
    edit_prompt_path.write_text("消息: {{USER_MESSAGE}}", encoding="utf-8")
    return init_prompt_path, edit_prompt_path


def test_create_session_and_get_session_snapshot(tmp_path: Path) -> None:
    client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))

    created = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )

    assert created.status_code == 200
    created_payload = created.json()
    assert created_payload["version"] == 1
    assert created_payload["run_id"]
    assert created_payload["source_image_name"] == "form.png"
    assert "image_path" not in created_payload
    assert "ocr_json_path" not in created_payload
    assert created_payload["current_html"] == "<form>v1</form>"
    assert created_payload["current_form_json"]["fields"][0]["label"] == "姓名"

    fetched = client.get(f"/api/sessions/{created_payload['session_id']}")

    assert fetched.status_code == 200
    fetched_payload = fetched.json()
    assert fetched_payload["session_id"] == created_payload["session_id"]
    assert fetched_payload["run_id"] == created_payload["run_id"]
    assert fetched_payload["source_image_name"] == "form.png"
    assert fetched_payload["turns"][0]["user_message"] == "初始化"
    assert fetched_payload["turns"][0]["assistant_message"] is None


def test_send_message_updates_session_snapshot(tmp_path: Path) -> None:
    client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))
    created = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )
    session_id = created.json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"message": "请新增备注字段"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 2
    assert payload["run_id"] == created.json()["run_id"]
    assert payload["source_image_name"] == "form.png"
    assert payload["current_html"] == "<form>v2</form>"
    assert payload["current_form_json"]["title"] == "客户登记表 v2"
    assert payload["summary"]["touched_field_ids"] == ["remark"]
    assert payload["turns"][-1]["user_message"] == "请新增备注字段"
    assert payload["turns"][-1]["assistant_message"] == "新增备注字段"


def test_fake_mode_is_isolated_per_session_within_same_client(tmp_path: Path) -> None:
    client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))

    first_created = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )
    second_created = client.post(
        "/api/sessions",
        files={"image": ("second.png", b"fake-image-2", "image/png")},
    )

    assert first_created.status_code == 200
    assert second_created.status_code == 200
    assert first_created.json()["current_html"] == "<form>v1</form>"
    assert second_created.json()["current_html"] == "<form>v1</form>"

    first_message = client.post(
        f"/api/sessions/{first_created.json()['session_id']}/messages",
        json={"message": "请新增备注字段"},
    )
    second_message = client.post(
        f"/api/sessions/{second_created.json()['session_id']}/messages",
        json={"message": "请新增备注字段"},
    )

    assert first_message.status_code == 200
    assert second_message.status_code == 200
    assert first_message.json()["current_html"] == "<form>v2</form>"
    assert second_message.json()["current_html"] == "<form>v2</form>"


def test_rollback_restores_previous_snapshot(tmp_path: Path) -> None:
    client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))
    created = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )
    session_id = created.json()["session_id"]
    client.post(
        f"/api/sessions/{session_id}/messages",
        json={"message": "请新增备注字段"},
    )

    response = client.post(f"/api/sessions/{session_id}/rollback")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 1
    assert payload["run_id"] == created.json()["run_id"]
    assert payload["source_image_name"] == "form.png"
    assert payload["current_html"] == "<form>v1</form>"
    assert len(payload["turns"]) == 1


def test_default_app_persists_session_across_app_instances(tmp_path: Path) -> None:
    first_client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))

    created = first_client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )

    assert created.status_code == 200
    session_id = created.json()["session_id"]

    second_client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))
    fetched = second_client.get(f"/api/sessions/{session_id}")

    assert fetched.status_code == 200
    assert fetched.json()["session_id"] == session_id


def test_default_app_uses_settings_backed_file_session_store(tmp_path: Path) -> None:
    from app.config import Settings

    session_root = tmp_path / "configured-sessions"
    settings = Settings(_env_file=None, workbench_session_root=session_root)
    client = TestClient(
        create_app(
            fake_mode=True,
            settings=settings,
        )
    )

    created = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )

    assert created.status_code == 200
    assert any(session_root.iterdir())


def test_create_session_requires_image_file(tmp_path: Path) -> None:
    client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))

    response = client.post("/api/sessions", files={})

    assert response.status_code == 422


def test_create_session_rejects_non_image_upload(tmp_path: Path) -> None:
    client = TestClient(create_app(fake_mode=True, session_root=tmp_path / "sessions"))

    response = client.post(
        "/api/sessions",
        files={"image": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "uploaded file must be an image"}


def test_missing_session_routes_return_404() -> None:
    client = TestClient(create_app(fake_mode=True, session_root=Path("/tmp/missing-session-tests")))

    get_response = client.get("/api/sessions/missing")
    message_response = client.post(
        "/api/sessions/missing/messages",
        json={"message": "hello"},
    )
    rollback_response = client.post("/api/sessions/missing/rollback")

    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "session not found"}
    assert message_response.status_code == 404
    assert message_response.json() == {"detail": "session not found"}
    assert rollback_response.status_code == 404
    assert rollback_response.json() == {"detail": "session not found"}


def test_cors_preflight_allows_local_frontend_origin() -> None:
    client = TestClient(create_app(fake_mode=True, session_root=Path("/tmp/cors-session-tests")))

    response = client.options(
        "/api/sessions",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_invalid_payload_errors_return_422_with_explicit_detail(tmp_path: Path) -> None:
    init_prompt_path, edit_prompt_path = write_prompt_files(tmp_path)
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=InvalidPayloadLLMService(),
        init_prompt_path=init_prompt_path,
        edit_prompt_path=edit_prompt_path,
        artifact_store=ArtifactStore(tmp_path / "runs"),
        ocr_service=FakeOCRService(),
    )
    app = FastAPI()
    app.include_router(create_sessions_router(service))
    client = TestClient(app)

    response = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "model response was not valid JSON"}


def test_unexpected_internal_validation_errors_return_500(tmp_path: Path) -> None:
    init_prompt_path, edit_prompt_path = write_prompt_files(tmp_path)
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=ValidPayloadLLMService(),
        init_prompt_path=init_prompt_path,
        edit_prompt_path=edit_prompt_path,
        artifact_store=ArtifactStore(tmp_path / "runs"),
        ocr_service=FakeOCRService(),
    )

    def explode(_: str) -> dict[str, object]:
        raise TypeError("validator exploded")

    service._parse_payload = explode  # type: ignore[method-assign]

    app = FastAPI()
    app.include_router(create_sessions_router(service))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )

    assert response.status_code == 500


def test_create_session_returns_stable_500_when_llm_request_fails(tmp_path: Path) -> None:
    init_prompt_path, edit_prompt_path = write_prompt_files(tmp_path)
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=FailingLLMService(),
        init_prompt_path=init_prompt_path,
        edit_prompt_path=edit_prompt_path,
        artifact_store=ArtifactStore(tmp_path / "runs"),
        ocr_service=FakeOCRService(),
    )
    app = FastAPI()
    app.include_router(create_sessions_router(service))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/sessions",
        files={"image": make_image_upload()},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "初始化失败：首轮表单重建未完成"}
