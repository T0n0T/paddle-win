import pytest

from app.workbench.models import ChangeSummary, FormDocument, SessionSnapshot


def test_form_document_requires_unique_field_ids() -> None:
    with pytest.raises(ValueError, match="duplicate field id"):
        FormDocument(
            title="客户登记表",
            sections=[{"id": "basic", "title": "基础信息"}],
            fields=[
                {
                    "id": "phone",
                    "section_id": "basic",
                    "label": "电话",
                    "type": "text",
                    "required": False,
                },
                {
                    "id": "phone",
                    "section_id": "basic",
                    "label": "备用电话",
                    "type": "text",
                    "required": False,
                },
            ],
        )


def test_session_snapshot_requires_current_state_to_match_latest_turn() -> None:
    with pytest.raises(ValueError, match="latest turn"):
        SessionSnapshot(
            session_id="session-1",
            version=1,
            image_path="/tmp/form.png",
            ocr_json_path="/tmp/ocr.json",
            current_form_json={
                "title": "客户登记表 v2",
                "sections": [{"id": "basic", "title": "基础信息"}],
                "fields": [
                    {
                        "id": "name",
                        "section_id": "basic",
                        "label": "姓名",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
            current_html="<form>v2</form>",
            summary={"user_intent": "更新标题"},
            turns=[
                {
                    "assistant_message": "生成首版",
                    "form_document": {
                        "title": "客户登记表",
                        "sections": [{"id": "basic", "title": "基础信息"}],
                        "fields": [
                            {
                                "id": "name",
                                "section_id": "basic",
                                "label": "姓名",
                                "type": "text",
                                "required": True,
                            }
                        ],
                    },
                    "html": "<form>v1</form>",
                    "summary": ChangeSummary(user_intent="初始化"),
                }
            ],
        )
