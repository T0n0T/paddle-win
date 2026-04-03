import json
from pathlib import Path

from app.services.compiler.formily_compiler_cli import run_formily_compile
from app.services.compiler.formily_compiler import collect_field_confidences
from app.services.compiler.validator import load_semantic_model_from_file


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
                "field_keys": ["work_leader", "plan_start_at"],
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
                        "source_id": "box_12",
                        "source_type": "text_box",
                        "bbox": [120.0, 88.0, 210.0, 114.0],
                        "page": 1,
                    }
                ],
                "warnings": [],
            },
            {
                "key": "plan_start_at",
                "title": "计划工作开始时间",
                "kind": "datetime",
                "section_key": "basic_info",
                "field_role": "datetime_start",
                "value": "2016-07-24 15:30:00",
                "confidence": 0.91,
                "evidence": [
                    {
                        "source_id": "box_41",
                        "source_type": "text_box",
                        "bbox": [240.0, 88.0, 380.0, 114.0],
                        "page": 1,
                    }
                ],
                "warnings": [],
            },
        ],
        "layout_hints": {
            "section_order": ["basic_info"],
            "preferred_columns": {"basic_info": 2},
            "section_spans": {"basic_info": "full"},
        },
        "warnings": [],
    }


def test_run_formily_compile_writes_formily_schema_from_semantic_json(tmp_path: Path):
    semantic_path = tmp_path / "semantic.json"
    output_path = tmp_path / "formily.json"
    semantic_path.write_text(
        json.dumps(sample_semantic_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    envelope = run_formily_compile(semantic_path=semantic_path, output_path=output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["schema"]["properties"]["basic_info"]["properties"]["work_leader"]["default"] == "闫丽亚"
    assert (
        payload["schema"]["properties"]["basic_info"]["properties"]["plan_start_at"]["default"]
        == "2016-07-24T15:30:00+08:00"
    )
    assert collect_field_confidences(envelope.schema_) == [0.98, 0.91]


def test_load_semantic_model_from_file_can_feed_compile_cli(tmp_path: Path):
    semantic_path = tmp_path / "semantic.json"
    semantic_path.write_text(
        json.dumps(sample_semantic_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    model = load_semantic_model_from_file(semantic_path)

    assert model.fields[0].key == "work_leader"
