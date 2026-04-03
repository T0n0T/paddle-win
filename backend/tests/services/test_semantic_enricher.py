import base64
import json
from types import SimpleNamespace
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.semantic import SemanticFormModel
from app.services.llm.openai_client import (
    OpenAIResponsesClient,
    _extract_output_text,
    extract_structured_output,
    _normalize_raw_response_payload,
    build_responses_request,
)
from app.services.llm.semantic_enricher_cli import (
    extract_semantic_model_from_raw_response,
    run_prompt_tuning,
)
from app.services.llm.semantic_enricher import build_semantic_request
from app.services.ocr.layout_normalizer import LayoutSkeleton, TableRegion, TextBox


def sample_layout_skeleton() -> LayoutSkeleton:
    return LayoutSkeleton(
        page_count=1,
        image_size={"width": 800, "height": 600},
        text_boxes=[
            TextBox(
                box_id="box_1",
                text="工作负责人",
                bbox=[10.0, 10.0, 110.0, 40.0],
                confidence=0.99,
            )
        ],
        tables=[
            TableRegion(
                table_id="table_1",
                bbox=[20.0, 100.0, 420.0, 220.0],
                cells=[],
            )
        ],
        checkbox_regions=[],
        underline_fill_regions=[],
        reading_order=["box_1", "table_1"],
    )


def sample_semantic_payload() -> dict[str, object]:
    return {
        "form_meta": {
            "title": "配电第一种工作票",
            "document_type": "电力工作票",
            "document_number": "2017070007",
        },
        "sections": [
            {
                "key": "basic_info",
                "title": "基本信息",
                "field_keys": ["work_leader"],
                "order": 1,
                "section_type": "basic",
            }
        ],
        "fields": [
            {
                "key": "work_leader",
                "title": "工作负责人",
                "kind": "string",
                "section_key": "basic_info",
                "field_role": "person_name",
                "value": "闫丽亚",
                "confidence": 0.98,
                "evidence": [
                    {
                        "source_id": "box_1",
                        "source_type": "text_box",
                        "bbox": [10.0, 10.0, 110.0, 40.0],
                        "page": 1,
                    }
                ],
                "warnings": [],
            }
        ],
        "layout_hints": {
            "section_order": ["basic_info"],
            "preferred_columns": {"basic_info": 2},
            "section_spans": {"basic_info": "full"},
        },
        "warnings": [],
    }


def sample_raw_ocr_payload() -> dict[str, object]:
    return {
        "page_index": None,
        "overall_ocr_res": {
            "rec_texts": ["工作负责人", "闫丽亚"],
            "rec_scores": [0.97, 0.96],
            "rec_boxes": [
                [10.0, 10.0, 110.0, 40.0],
                [120.0, 10.0, 220.0, 40.0],
            ],
        },
        "table_res_list": [],
    }


def test_build_semantic_prompt_includes_layout_contract():
    request = build_semantic_request(
        sample_layout_skeleton(),
        image_path="backend/tests/fixtures/forms/work-ticket.jpg",
        raw_ocr_payload=sample_raw_ocr_payload(),
    )

    assert "SemanticFormModel" in request.instructions
    assert "table_columns" in request.instructions
    assert request.raw_ocr_json["overall_ocr_res"]["rec_texts"] == ["工作负责人", "闫丽亚"]
    assert request.layout_json["reading_order"] == ["box_1", "table_1"]


def test_build_responses_request_encodes_image_bytes(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    image_bytes = b"\xff\xd8\xff\xdbsample"
    image_path.write_bytes(image_bytes)

    request = build_semantic_request(
        sample_layout_skeleton(),
        image_path=image_path,
        raw_ocr_payload=sample_raw_ocr_payload(),
    )
    payload = build_responses_request(request, model="gpt-test")
    content = payload["input"][0]["content"]

    assert payload["model"] == "gpt-test"
    assert payload["instructions"] == request.instructions
    assert content[0]["type"] == "input_text"
    assert '"reading_order": [' in content[0]["text"]
    assert '"raw_ocr_json": {' in content[0]["text"]
    assert '"layout_json": {' in content[0]["text"]
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")
    encoded = content[1]["image_url"].split(",", 1)[1]
    assert base64.b64decode(encoded) == image_bytes


def test_openai_client_validates_structured_semantic_output(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-jpeg")
    fake_sdk = SimpleNamespace(
        responses=SimpleNamespace(
            create=lambda **_: SimpleNamespace(output_text=json.dumps(sample_semantic_payload()))
        )
    )
    client = OpenAIResponsesClient(model="gpt-test", sdk_client=fake_sdk)

    result = client.generate_structured(
        build_semantic_request(
            sample_layout_skeleton(),
            image_path=image_path,
            raw_ocr_payload=sample_raw_ocr_payload(),
        ),
        SemanticFormModel,
    )

    assert isinstance(result, SemanticFormModel)
    assert result.fields[0].key == "work_leader"


def test_openai_client_rejects_invalid_structured_semantic_output(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-jpeg")
    fake_sdk = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **_: SimpleNamespace(output_text='{"fields": []}'))
    )
    client = OpenAIResponsesClient(model="gpt-test", sdk_client=fake_sdk)

    with pytest.raises(ValidationError):
        client.generate_structured(
            build_semantic_request(
                sample_layout_skeleton(),
                image_path=image_path,
                raw_ocr_payload=sample_raw_ocr_payload(),
            ),
            SemanticFormModel,
        )


def test_openai_client_generate_structured_accepts_sse_text_payload(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-jpeg")
    sse_payload = "\n\n".join(
        [
            'event: response.created\ndata: {"type":"response.created"}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"{\\"form_meta\\": {\\"title\\": \\"配电第一种工作票\\", \\"document_type\\": \\"电力工作票\\", \\"document_number\\": \\"2017070007\\"}, "}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"\\"sections\\": [{\\"key\\": \\"basic_info\\", \\"title\\": \\"基本信息\\", \\"field_keys\\": [\\"work_leader\\"], \\"order\\": 1, \\"section_type\\": \\"basic\\"}], "}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"\\"fields\\": [{\\"key\\": \\"work_leader\\", \\"title\\": \\"工作负责人\\", \\"kind\\": \\"string\\", \\"section_key\\": \\"basic_info\\", \\"field_role\\": \\"person_name\\", \\"value\\": \\"闫丽亚\\", \\"confidence\\": 0.98, \\"evidence\\": [{\\"source_id\\": \\"box_1\\", \\"source_type\\": \\"text_box\\", \\"bbox\\": [10.0, 10.0, 110.0, 40.0], \\"page\\": 1}], \\"warnings\\": []}], "}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"\\"layout_hints\\": {\\"section_order\\": [\\"basic_info\\"], \\"preferred_columns\\": {\\"basic_info\\": 2}, \\"section_spans\\": {\\"basic_info\\": \\"full\\"}}, \\"warnings\\": []}"}',
            'event: response.completed\ndata: {"type":"response.completed"}',
        ]
    )
    fake_sdk = SimpleNamespace(responses=SimpleNamespace(create=lambda **_: sse_payload))
    client = OpenAIResponsesClient(model="gpt-test", sdk_client=fake_sdk)

    result = client.generate_structured(
        build_semantic_request(
            sample_layout_skeleton(),
            image_path=image_path,
            raw_ocr_payload=sample_raw_ocr_payload(),
        ),
        SemanticFormModel,
    )

    assert isinstance(result, SemanticFormModel)
    assert result.form_meta.document_number == "2017070007"


def test_extract_output_text_falls_back_to_output_message_content():
    response = SimpleNamespace(
        output_text=None,
        output=[
            SimpleNamespace(
                type="message",
                content=[
                    SimpleNamespace(type="output_text", text=json.dumps(sample_semantic_payload())),
                ],
            )
        ],
    )

    assert json.loads(_extract_output_text(response))["fields"][0]["key"] == "work_leader"


def test_extract_output_text_strips_markdown_code_fence():
    response = SimpleNamespace(
        output_text="```json\n" + json.dumps(sample_semantic_payload(), ensure_ascii=False, indent=2) + "\n```"
    )

    assert json.loads(_extract_output_text(response))["fields"][0]["key"] == "work_leader"


def test_normalize_raw_response_payload_extracts_final_text_from_sse_stream():
    raw_stream = "\n\n".join(
        [
            'event: response.created\ndata: {"type":"response.created"}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"{\\n"}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"  \\"foo\\": \\"bar\\"\\n"}',
            'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"}"}',
            'event: response.completed\ndata: {"type":"response.completed"}',
        ]
    )

    normalized = _normalize_raw_response_payload(raw_stream)

    assert normalized["response_format"] == "sse_text"
    assert normalized["output_text"] == '{\n  "foo": "bar"\n}'
    assert normalized["output_json"] == {"foo": "bar"}


def test_extract_structured_output_prefers_output_json_payload():
    payload = {
        "response_format": "sse_text",
        "output_text": '{"fields": []}',
        "output_json": sample_semantic_payload(),
    }

    result = extract_structured_output(payload, SemanticFormModel)

    assert isinstance(result, SemanticFormModel)
    assert result.fields[0].key == "work_leader"


def test_openai_client_uses_configured_base_url(monkeypatch: pytest.MonkeyPatch):
    init_kwargs: dict[str, object] = {}

    class FakeSDKClient:
        responses = SimpleNamespace(create=lambda **_: None)

    class FakeSettings:
        OPENAI_API_KEY = "test-key"
        OPENAI_BASE_URL = "https://example.com/v1"
        OPENAI_MODEL = "gpt-test"

    def fake_openai(**kwargs):
        init_kwargs.update(kwargs)
        return FakeSDKClient()

    monkeypatch.setattr("app.services.llm.openai_client.Settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.llm.openai_client.OpenAI", fake_openai)

    client = OpenAIResponsesClient()

    assert client.model == "gpt-test"
    assert init_kwargs == {
        "api_key": "test-key",
        "base_url": "https://example.com/v1",
    }


def test_prompt_tuning_can_write_raw_response_without_schema_validation(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    ocr_path = tmp_path / "ocr.json"
    prompt_path = tmp_path / "semantic_enrich.md"
    output_path = tmp_path / "raw-response.json"

    image_path.write_bytes(b"fake-jpeg")
    ocr_path.write_text(json.dumps(sample_raw_ocr_payload(), ensure_ascii=False), encoding="utf-8")
    prompt_path.write_text("OVERRIDE PROMPT\nSemanticFormModel\n", encoding="utf-8")

    class FakeClient:
        def __init__(self) -> None:
            self.request = None

        def generate_raw(self, request):
            self.request = request
            return _normalize_raw_response_payload(
                {
                    "id": "resp_123",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "not-json-but-useful"}],
                        }
                    ],
                }
            )

    client = FakeClient()

    result = run_prompt_tuning(
        image_path=image_path,
        ocr_json_path=ocr_path,
        prompt_path=prompt_path,
        output_path=output_path,
        client=client,
        raw_response_output=True,
    )

    assert result["response"]["id"] == "resp_123"
    assert result["output_text"] == "not-json-but-useful"
    assert client.request.instructions.startswith("OVERRIDE PROMPT")
    assert json.loads(output_path.read_text(encoding="utf-8"))["output_text"] == "not-json-but-useful"


def test_prompt_tuning_cli_runs_with_ocr_json_and_prompt_override(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    ocr_path = tmp_path / "ocr.json"
    prompt_path = tmp_path / "semantic_enrich.md"
    output_path = tmp_path / "semantic.json"

    image_path.write_bytes(b"fake-jpeg")
    ocr_path.write_text(json.dumps(sample_raw_ocr_payload(), ensure_ascii=False), encoding="utf-8")
    prompt_path.write_text("OVERRIDE PROMPT\nSemanticFormModel\n", encoding="utf-8")

    class FakeClient:
        def __init__(self) -> None:
            self.request = None

        def generate_structured(self, request, response_model):
            self.request = request
            return response_model.model_validate(sample_semantic_payload())

    client = FakeClient()

    result = run_prompt_tuning(
        image_path=image_path,
        ocr_json_path=ocr_path,
        prompt_path=prompt_path,
        output_path=output_path,
        client=client,
    )

    assert isinstance(result, SemanticFormModel)
    assert client.request.instructions.startswith("OVERRIDE PROMPT")
    assert client.request.raw_ocr_json["overall_ocr_res"]["rec_texts"] == ["工作负责人", "闫丽亚"]
    assert client.request.layout_json["reading_order"] == ["box_1", "box_2"]
    assert json.loads(output_path.read_text(encoding="utf-8"))["fields"][0]["key"] == "work_leader"


def test_extract_semantic_model_from_raw_response_uses_output_json(tmp_path: Path):
    raw_path = tmp_path / "semantic-result.raw.json"
    raw_path.write_text(
        json.dumps(
            {
                "response_format": "sse_text",
                "output_text": json.dumps(sample_semantic_payload(), ensure_ascii=False),
                "output_json": sample_semantic_payload(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = extract_semantic_model_from_raw_response(raw_path)

    assert isinstance(result, SemanticFormModel)
    assert result.form_meta.document_number == "2017070007"
    assert result.fields[0].key == "work_leader"


def test_extract_semantic_model_from_raw_response_rejects_missing_payload(tmp_path: Path):
    raw_path = tmp_path / "semantic-result.raw.json"
    raw_path.write_text(
        json.dumps(
            {
                "response_format": "sse_text",
                "output_text": "not-json",
                "output_json": None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Could not extract a valid semantic payload"):
        extract_semantic_model_from_raw_response(raw_path)
