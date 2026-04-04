from pathlib import Path

from app.workbench.models import ChangeSummary, FormDocument
from app.workbench.store import InMemorySessionStore


def make_form_document(title: str = "客户登记表") -> FormDocument:
    return FormDocument(
        title=title,
        sections=[{"id": "basic", "title": "基础信息"}],
        fields=[
            {
                "id": "name",
                "section_id": "basic",
                "label": "姓名",
                "type": "text",
                "required": True,
            }
        ],
    )


def make_summary(user_intent: str, touched_field_ids: list[str] | None = None) -> ChangeSummary:
    return ChangeSummary(
        user_intent=user_intent,
        applied=[user_intent],
        warnings=[],
        unresolved=[],
        touched_field_ids=touched_field_ids or [],
    )


def test_store_create_returns_deepcopy_isolated_snapshot() -> None:
    store = InMemorySessionStore()
    session = store.create(
        image_path=Path("/tmp/form.png"),
        ocr_json_path=Path("/tmp/ocr.json"),
        form_document=make_form_document(),
        html="<form>v1</form>",
        summary=make_summary("初始化"),
    )

    session.current_form_json.title = "被污染的标题"
    session.summary.applied.append("伪造修改")
    session.turns[0].html = "<form>tampered</form>"

    stored_snapshot = store._history[session.session_id][-1]

    assert stored_snapshot.current_form_json.title == "客户登记表"
    assert stored_snapshot.summary.applied == ["初始化"]
    assert stored_snapshot.turns[0].html == "<form>v1</form>"


def test_store_append_turn_creates_version_two_and_returns_isolated_snapshot() -> None:
    store = InMemorySessionStore()
    session = store.create(
        image_path=Path("/tmp/form.png"),
        ocr_json_path=Path("/tmp/ocr.json"),
        form_document=make_form_document(),
        html="<form>v1</form>",
        summary=make_summary("初始化"),
    )

    updated = store.append_turn(
        session_id=session.session_id,
        user_message="请新增备注字段",
        assistant_message="已新增备注",
        form_document=make_form_document("客户登记表 v2"),
        html="<form>v2</form>",
        summary=make_summary("新增备注", ["remark"]),
    )

    assert updated.version == 2
    assert len(updated.turns) == 2
    assert updated.turns[0].user_message == "初始化"
    assert updated.turns[0].assistant_message is None
    assert updated.turns[0].form_document.title == "客户登记表"
    assert updated.turns[1].user_message == "请新增备注字段"
    assert updated.turns[1].assistant_message == "已新增备注"
    assert updated.turns[1].form_document.title == "客户登记表 v2"

    updated.turns[0].form_document.title = "被污染的首轮"
    updated.turns[1].assistant_message = "被污染的回复"
    updated.current_html = "<form>tampered</form>"

    stored_snapshot = store._history[session.session_id][-1]

    assert stored_snapshot.turns[0].form_document.title == "客户登记表"
    assert stored_snapshot.turns[1].assistant_message == "已新增备注"
    assert stored_snapshot.current_html == "<form>v2</form>"


def test_store_can_rollback_to_previous_version() -> None:
    store = InMemorySessionStore()
    session = store.create(
        image_path=Path("/tmp/form.png"),
        ocr_json_path=Path("/tmp/ocr.json"),
        form_document=make_form_document(),
        html="<form>v1</form>",
        summary=make_summary("初始化"),
    )
    updated = store.append_turn(
        session_id=session.session_id,
        user_message="请新增备注字段",
        assistant_message="已新增备注",
        form_document=make_form_document("客户登记表 v2"),
        html="<form>v2</form>",
        summary=make_summary("新增备注", ["remark"]),
    )

    rolled_back = store.rollback(updated.session_id)

    assert rolled_back.version == 1
    assert rolled_back.current_html == "<form>v1</form>"
    assert len(rolled_back.turns) == 1
