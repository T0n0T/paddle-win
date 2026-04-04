from pathlib import Path

import numpy as np
import pytest

from app.models import OCRBlock
from app.services.paddle_structure import PaddleStructureService


class FakePaddleOCRClient:
    def __init__(self, result: list[dict]) -> None:
        self.result = result
        self.calls: list[tuple[str, dict]] = []

    def ocr(self, image_path: str, **kwargs):
        self.calls.append((image_path, kwargs))
        return [self.result]


class FakeOCRPage(dict):
    pass


def test_paddle_structure_service_converts_ocr_lines_to_blocks(tmp_path: Path) -> None:
    image_path = tmp_path / "form.png"
    image_path.write_bytes(b"fake-image")
    client = FakePaddleOCRClient(
        [
            {
                "rec_text": "姓名",
                "rec_score": 0.99,
                "dt_polys": [[0, 0], [10, 0], [10, 20], [0, 20]],
            }
        ]
    )
    service = PaddleStructureService(ocr_client=client)

    raw_result, blocks = service.run(image_path)

    assert client.calls == [(str(image_path), {})]
    assert raw_result == {
        "engine": "paddleocr",
        "pages": [
            [
                {
                    "rec_text": "姓名",
                    "rec_score": 0.99,
                    "dt_polys": [[0, 0], [10, 0], [10, 20], [0, 20]],
                }
            ]
        ],
    }
    assert blocks == [
        OCRBlock(text="姓名", bbox=[0.0, 0.0, 10.0, 20.0], block_type="text")
    ]


def test_paddle_structure_service_requires_text_detections(tmp_path: Path) -> None:
    image_path = tmp_path / "form.png"
    image_path.write_bytes(b"fake-image")
    client = FakePaddleOCRClient([])
    service = PaddleStructureService(ocr_client=client)

    with pytest.raises(ValueError, match="no OCR text blocks detected"):
        service.run(image_path)


def test_paddle_structure_service_supports_mapping_style_page_results(tmp_path: Path) -> None:
    image_path = tmp_path / "form.png"
    image_path.write_bytes(b"fake-image")
    client = FakePaddleOCRClient(
        FakeOCRPage(
            {
                "rec_texts": ["姓名", "电话"],
                "dt_polys": [
                    [[0, 0], [10, 0], [10, 20], [0, 20]],
                    [[20, 0], [40, 0], [40, 20], [20, 20]],
                ],
            }
        )
    )
    service = PaddleStructureService(ocr_client=client)

    raw_result, blocks = service.run(image_path)

    assert raw_result["pages"][0]["rec_texts"] == ["姓名", "电话"]
    assert blocks == [
        OCRBlock(text="姓名", bbox=[0.0, 0.0, 10.0, 20.0], block_type="text"),
        OCRBlock(text="电话", bbox=[20.0, 0.0, 40.0, 20.0], block_type="text"),
    ]


def test_paddle_structure_service_extracts_bbox_from_numpy_page_polys(tmp_path: Path) -> None:
    image_path = tmp_path / "form.png"
    image_path.write_bytes(b"fake-image")
    client = FakePaddleOCRClient(
        FakeOCRPage(
            {
                "rec_texts": ["姓名", "电话"],
                "dt_polys": np.array(
                    [
                        [[0, 0], [10, 0], [10, 20], [0, 20]],
                        [[20, 0], [40, 0], [40, 20], [20, 20]],
                    ]
                ),
            }
        )
    )
    service = PaddleStructureService(ocr_client=client)

    _, blocks = service.run(image_path)

    assert blocks == [
        OCRBlock(text="姓名", bbox=[0.0, 0.0, 10.0, 20.0], block_type="text"),
        OCRBlock(text="电话", bbox=[20.0, 0.0, 40.0, 20.0], block_type="text"),
    ]
