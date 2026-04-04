from pathlib import Path

import pytest

from app.workbench.models import CreateSessionRequest, EditMessageRequest
from app.workbench.service import WorkbenchService
from app.workbench.store import InMemorySessionStore


class FakeLLMService:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[tuple[Path, str]] = []

    def generate_text(self, image_path: Path, prompt: str) -> str:
        self.calls.append((image_path, prompt))
        return self.responses.pop(0)


def write_prompt_files(tmp_path: Path) -> tuple[Path, Path]:
    init_prompt = tmp_path / "workbench_init.md"
    init_prompt.write_text(
        "OCR:\n{{OCR_JSON}}\nJSON_PATH={{OCR_JSON_PATH}}\nIMAGE={{IMAGE_PATH}}",
        encoding="utf-8",
    )
    edit_prompt = tmp_path / "workbench_edit.md"
    edit_prompt.write_text(
        "MESSAGE={{USER_MESSAGE}}\nFORM={{CURRENT_FORM_JSON}}\nHTML={{CURRENT_HTML}}",
        encoding="utf-8",
    )
    return init_prompt, edit_prompt


def write_source_files(tmp_path: Path) -> tuple[Path, Path]:
    image_path = tmp_path / "form.png"
    image_path.write_bytes(b"fake-image")
    ocr_json_path = tmp_path / "ocr.json"
    ocr_json_path.write_text(
        '[{"text":"姓名","bbox":[0,0,10,10],"block_type":"text"}]',
        encoding="utf-8",
    )
    return image_path, ocr_json_path


def make_init_payload() -> str:
    return (
        '{"form_json":{"title":"客户登记表","sections":[{"id":"basic","title":"基础信息"}],'
        '"fields":[{"id":"name","section_id":"basic","label":"姓名","type":"text","required":true}]},'
        '"html":"<form>v1</form>",'
        '"change_summary":{"user_intent":"初始化","applied":["生成首版"],"warnings":[],'
        '"unresolved":[],"touched_field_ids":[]}}'
    )


def make_edit_payload() -> str:
    return (
        '{"form_json":{"title":"客户登记表 v2","sections":[{"id":"basic","title":"基础信息"}],'
        '"fields":[{"id":"name","section_id":"basic","label":"姓名","type":"text","required":true},'
        '{"id":"remark","section_id":"basic","label":"备注","type":"textarea","required":false}]},'
        '"html":"<form>v2</form>",'
        '"change_summary":{"user_intent":"新增备注","applied":["新增备注字段"],"warnings":[],'
        '"unresolved":[],"touched_field_ids":["remark"]}}'
    )


def test_create_session_builds_first_version(tmp_path: Path) -> None:
    image_path, ocr_json_path = write_source_files(tmp_path)
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    llm = FakeLLMService([make_init_payload()])
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=llm,
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
    )

    session = service.create_session(
        CreateSessionRequest(image_path=image_path, ocr_json_path=ocr_json_path)
    )

    assert session.version == 1
    assert session.image_path == image_path
    assert session.ocr_json_path == ocr_json_path
    assert session.current_html == "<form>v1</form>"
    assert session.current_form_json.fields[0].label == "姓名"
    assert session.summary.user_intent == "初始化"
    assert llm.calls == [
        (
            image_path,
            (
                "OCR:\n"
                '[{"text":"姓名","bbox":[0,0,10,10],"block_type":"text"}]\n'
                f"JSON_PATH={ocr_json_path}\n"
                f"IMAGE={image_path}"
            ),
        )
    ]


def test_send_message_uses_current_session_state_and_updates_snapshot(tmp_path: Path) -> None:
    image_path, ocr_json_path = write_source_files(tmp_path)
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    llm = FakeLLMService([make_init_payload(), make_edit_payload()])
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=llm,
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
    )
    session = service.create_session(
        CreateSessionRequest(image_path=image_path, ocr_json_path=ocr_json_path)
    )

    updated = service.send_message(
        session.session_id,
        EditMessageRequest(message="请新增备注字段"),
    )

    assert updated.version == 2
    assert updated.current_html == "<form>v2</form>"
    assert updated.current_form_json.title == "客户登记表 v2"
    assert updated.current_form_json.fields[-1].id == "remark"
    assert updated.summary.touched_field_ids == ["remark"]
    assert updated.turns[-1].user_message == "请新增备注字段"
    assert updated.turns[-1].assistant_message == "新增备注字段"
    assert llm.calls[-1] == (
        image_path,
        (
            "MESSAGE=请新增备注字段\n"
            'FORM={"title":"客户登记表","description":"","sections":[{"id":"basic","title":"基础信息"}],'
            '"fields":[{"id":"name","section_id":"basic","label":"姓名","type":"text","required":true,'
            '"placeholder":"","options":[],"layout_hint":{"width":"full","inline_with":null,"emphasis":"normal"}}]}\n'
            "HTML=<form>v1</form>"
        ),
    )


def test_send_message_prompt_rendering_preserves_placeholder_like_user_content(tmp_path: Path) -> None:
    image_path, ocr_json_path = write_source_files(tmp_path)
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    llm = FakeLLMService([make_init_payload(), make_edit_payload()])
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=llm,
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
    )
    session = service.create_session(
        CreateSessionRequest(image_path=image_path, ocr_json_path=ocr_json_path)
    )

    service.send_message(
        session.session_id,
        EditMessageRequest(message="请保留原文 {{CURRENT_HTML}}"),
    )

    assert llm.calls[-1] == (
        image_path,
        (
            "MESSAGE=请保留原文 {{CURRENT_HTML}}\n"
            'FORM={"title":"客户登记表","description":"","sections":[{"id":"basic","title":"基础信息"}],'
            '"fields":[{"id":"name","section_id":"basic","label":"姓名","type":"text","required":true,'
            '"placeholder":"","options":[],"layout_hint":{"width":"full","inline_with":null,"emphasis":"normal"}}]}\n'
            "HTML=<form>v1</form>"
        ),
    )


def test_send_message_retries_once_when_payload_invalid(tmp_path: Path) -> None:
    image_path, ocr_json_path = write_source_files(tmp_path)
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    llm = FakeLLMService(
        [
            make_init_payload(),
            '{"form_json":{},"html":"","change_summary":{}}',
            (
                '{"form_json":{"title":"客户登记表","sections":[],"fields":[]},'
                '"html":"<form>ok</form>",'
                '"change_summary":{"user_intent":"改标题","applied":["保留空字段"],'
                '"warnings":[],"unresolved":[],"touched_field_ids":[]}}'
            ),
        ]
    )
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=llm,
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
        max_validation_retries=1,
    )
    session = service.create_session(
        CreateSessionRequest(image_path=image_path, ocr_json_path=ocr_json_path)
    )

    updated = service.send_message(
        session.session_id,
        EditMessageRequest(message="改一下"),
    )

    assert updated.current_html == "<form>ok</form>"
    assert len(llm.calls) == 3


def test_unexpected_validation_type_error_is_not_wrapped_as_invalid_payload(
    tmp_path: Path,
) -> None:
    image_path, _ = write_source_files(tmp_path)
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    llm = FakeLLMService([make_init_payload()])
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=llm,
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
    )

    def explode(_: str) -> dict[str, object]:
        raise TypeError("validator exploded")

    service._parse_payload = explode  # type: ignore[method-assign]

    with pytest.raises(TypeError, match="validator exploded"):
        service._generate_validated_response(
            image_path=image_path,
            prompt="ignored",
        )


@pytest.mark.parametrize(
    ("response_text", "message"),
    [
        ("not-json", "model response was not valid JSON"),
        ('["not-an-object"]', "model response must be a JSON object"),
        ('{"html":"<form/>","change_summary":{}}', "model response missing required keys: form_json"),
    ],
)
def test_parse_payload_rejects_malformed_payloads(
    tmp_path: Path, response_text: str, message: str
) -> None:
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=FakeLLMService([]),
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
    )

    with pytest.raises(ValueError, match=message):
        service._parse_payload(response_text)


def test_send_message_raises_after_retry_budget_exhausted(tmp_path: Path) -> None:
    image_path, ocr_json_path = write_source_files(tmp_path)
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    llm = FakeLLMService(
        [
            make_init_payload(),
            '{"form_json":{},"html":"","change_summary":{}}',
            '{"form_json":{},"html":"","change_summary":{}}',
        ]
    )
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=llm,
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
        max_validation_retries=1,
    )
    session = service.create_session(
        CreateSessionRequest(image_path=image_path, ocr_json_path=ocr_json_path)
    )

    with pytest.raises(ValueError):
        service.send_message(session.session_id, EditMessageRequest(message="改一下"))

    assert len(llm.calls) == 3


def test_failed_retries_do_not_mutate_session_state(tmp_path: Path) -> None:
    image_path, ocr_json_path = write_source_files(tmp_path)
    init_prompt, edit_prompt = write_prompt_files(tmp_path)
    store = InMemorySessionStore()
    llm = FakeLLMService(
        [
            make_init_payload(),
            '{"form_json":{},"html":"","change_summary":{}}',
            '{"form_json":{},"html":"","change_summary":{}}',
        ]
    )
    service = WorkbenchService(
        store=store,
        llm_service=llm,
        init_prompt_path=init_prompt,
        edit_prompt_path=edit_prompt,
        max_validation_retries=1,
    )
    session = service.create_session(
        CreateSessionRequest(image_path=image_path, ocr_json_path=ocr_json_path)
    )

    with pytest.raises(ValueError):
        service.send_message(session.session_id, EditMessageRequest(message="改一下"))

    persisted = store.get(session.session_id)

    assert persisted.version == 1
    assert len(persisted.turns) == 1
    assert persisted.current_html == "<form>v1</form>"
    assert len(store._history[session.session_id]) == 1
