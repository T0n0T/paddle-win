import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from app.services.ocr.layout_normalizer import normalize_layout
from app.services.ocr.paddle_table_v2 import PaddleTableV2Client


FIXTURE_PATH = Path("backend/tests/fixtures/ocr/work-ticket-table-v2.json")


@pytest.fixture
def sample_table_v2_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_normalize_table_v2_output_builds_layout_skeleton(sample_table_v2_payload: dict):
    skeleton = normalize_layout(sample_table_v2_payload)

    assert skeleton.page_count == 1
    assert skeleton.image_size == {"width": 750, "height": 1126}
    assert [box.box_id for box in skeleton.text_boxes] == ["box_1", "box_2", "box_3", "box_4", "box_5"]
    assert [table.table_id for table in skeleton.tables] == ["table_1"]
    assert [cell.cell_id for cell in skeleton.tables[0].cells] == [
        "table_1_cell_1",
        "table_1_cell_2",
        "table_1_cell_3",
        "table_1_cell_4",
    ]
    assert [cell.text for cell in skeleton.tables[0].cells] == [
        "工作内容",
        "停电范围",
        "安装关口表",
        "一线一变",
    ]
    assert [region.region_id for region in skeleton.checkbox_regions] == ["checkbox_4", "checkbox_5"]
    assert [region.region_id for region in skeleton.underline_fill_regions] == ["underline_1"]

    assert skeleton.tables[0].bbox == [32.0, 250.0, 482.0, 368.0]
    assert skeleton.tables[0].cells[1].row == 1
    assert skeleton.tables[0].cells[1].col == 2
    assert skeleton.checkbox_regions[0].checked is True
    assert skeleton.checkbox_regions[1].checked is False
    assert skeleton.underline_fill_regions[0].text_box_ids == ["box_3"]
    assert skeleton.reading_order == ["box_1", "box_2", "box_3", "box_4", "box_5", "table_1"]


def test_normalize_layout_omits_best_effort_regions_when_missing(sample_table_v2_payload: dict):
    payload_without_candidates = dict(sample_table_v2_payload)
    payload_without_candidates["overall_ocr_res"] = dict(sample_table_v2_payload["overall_ocr_res"])
    payload_without_candidates["overall_ocr_res"]["rec_texts"] = ["配电第一种工作票", "工作负责人"]
    payload_without_candidates["overall_ocr_res"]["rec_scores"] = [0.99, 0.97]
    payload_without_candidates["overall_ocr_res"]["rec_boxes"] = [
        [120.0, 88.0, 420.0, 126.0],
        [48.0, 168.0, 160.0, 204.0],
    ]

    skeleton = normalize_layout(payload_without_candidates)

    assert skeleton.checkbox_regions == []
    assert skeleton.underline_fill_regions == []


def test_normalize_layout_rejects_mismatched_overall_ocr_lengths(sample_table_v2_payload: dict):
    payload = dict(sample_table_v2_payload)
    payload["overall_ocr_res"] = dict(sample_table_v2_payload["overall_ocr_res"])
    payload["overall_ocr_res"]["rec_texts"] = ["A", "B"]
    payload["overall_ocr_res"]["rec_boxes"] = [[1.0, 2.0, 3.0, 4.0]]

    with pytest.raises(ValueError, match="rec_texts and rec_boxes must have the same length"):
        normalize_layout(payload)


def test_normalize_layout_rejects_invalid_bbox_shape(sample_table_v2_payload: dict):
    payload = dict(sample_table_v2_payload)
    payload["overall_ocr_res"] = dict(sample_table_v2_payload["overall_ocr_res"])
    payload["overall_ocr_res"]["rec_boxes"] = [[1.0, 2.0, 3.0]]

    with pytest.raises(ValueError, match="bbox must contain 4 or 8 coordinates"):
        normalize_layout(payload)


def test_normalize_layout_preserves_cell_text_when_scores_are_missing(sample_table_v2_payload: dict):
    payload = dict(sample_table_v2_payload)
    payload["table_res_list"] = [dict(sample_table_v2_payload["table_res_list"][0])]
    payload["table_res_list"][0]["table_ocr_pred"] = dict(
        sample_table_v2_payload["table_res_list"][0]["table_ocr_pred"]
    )
    payload["table_res_list"][0]["table_ocr_pred"]["rec_scores"] = [0.95]

    skeleton = normalize_layout(payload)

    assert [cell.text for cell in skeleton.tables[0].cells] == [
        "工作内容",
        "停电范围",
        "安装关口表",
        "一线一变",
    ]
    assert skeleton.tables[0].cells[1].confidence is None


def test_normalize_layout_matches_table_regions_by_geometry(sample_table_v2_payload: dict):
    payload = dict(sample_table_v2_payload)
    payload["layout_det_res"] = {
        "boxes": [
            {"label": "table", "coordinate": [410.0, 520.0, 700.0, 660.0], "score": 0.97},
            {"label": "table", "coordinate": [32.0, 250.0, 482.0, 368.0], "score": 0.98},
        ]
    }
    payload["table_res_list"] = [
        dict(sample_table_v2_payload["table_res_list"][0]),
        {
            "table_region_id": 2,
            "cell_box_list": [
                [420.0, 530.0, 560.0, 590.0],
                [560.0, 530.0, 700.0, 590.0],
                [420.0, 590.0, 560.0, 650.0],
                [560.0, 590.0, 700.0, 650.0],
            ],
            "table_ocr_pred": {
                "rec_texts": ["设备", "编号", "开关", "A-01"],
                "rec_scores": [0.9, 0.9, 0.9, 0.9],
                "rec_boxes": [
                    [420.0, 530.0, 560.0, 590.0],
                    [560.0, 530.0, 700.0, 590.0],
                    [420.0, 590.0, 560.0, 650.0],
                    [560.0, 590.0, 700.0, 650.0],
                ],
            },
        },
    ]

    skeleton = normalize_layout(payload)

    assert [table.table_id for table in skeleton.tables] == ["table_1", "table_2"]
    assert skeleton.tables[0].bbox == [32.0, 250.0, 482.0, 368.0]
    assert skeleton.tables[1].bbox == [410.0, 520.0, 700.0, 660.0]


def test_normalize_layout_falls_back_to_cell_bbox_when_layout_table_does_not_overlap(
    sample_table_v2_payload: dict,
):
    payload = dict(sample_table_v2_payload)
    payload["layout_det_res"] = {
        "boxes": [
            {"label": "table", "coordinate": [600.0, 700.0, 720.0, 820.0], "score": 0.98},
        ]
    }

    skeleton = normalize_layout(payload)

    assert skeleton.tables[0].bbox == [32.0, 250.0, 482.0, 368.0]


def test_paddle_table_v2_client_calls_official_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    calls: list[Path] = []

    class FakePrediction:
        def __init__(self, payload: dict):
            self.payload = payload

        def json(self) -> dict:
            return self.payload

    class FakePipeline:
        def predict(self, image_path: Path):
            calls.append(Path(image_path))
            return iter([FakePrediction({"page_index": None, "overall_ocr_res": {}, "table_res_list": []})])

    fake_module = ModuleType("paddleocr")
    fake_module.TableRecognitionPipelineV2 = lambda: FakePipeline()
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fixture")

    client = PaddleTableV2Client()
    payload = client.run(image_path)

    assert calls == [image_path]
    assert payload == {"page_index": None, "overall_ocr_res": {}, "table_res_list": []}


def test_paddle_table_v2_client_rejects_empty_predictions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    class FakePipeline:
        def predict(self, image_path: Path):
            return iter([])

    fake_module = ModuleType("paddleocr")
    fake_module.TableRecognitionPipelineV2 = lambda: FakePipeline()
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fixture")

    client = PaddleTableV2Client()

    with pytest.raises(ValueError, match="returned no predictions"):
        client.run(image_path)
