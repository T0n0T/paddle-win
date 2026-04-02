import base64
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.semantic import SemanticFormModel
from app.services.llm.openai_client import OpenAIResponsesClient, build_responses_request
from app.services.llm.semantic_enricher_cli import run_prompt_tuning
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
