import json
from pathlib import Path

from app.services.ocr.paddle_table_v2_cli import run_ocr_export


def test_run_ocr_export_writes_utf8_json(tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    output_path = tmp_path / "ocr.json"
    image_path.write_bytes(b"fake-jpeg")

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[Path] = []

        def run(self, input_image_path: Path) -> dict[str, object]:
            self.calls.append(input_image_path)
            return {
                "input_path": str(input_image_path),
                "overall_ocr_res": {
                    "rec_texts": ["工作负责人", "闫丽亚"],
                },
            }

    client = FakeClient()

    payload = run_ocr_export(image_path=image_path, output_path=output_path, client=client)

    assert client.calls == [image_path]
    assert payload["overall_ocr_res"]["rec_texts"] == ["工作负责人", "闫丽亚"]
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload
