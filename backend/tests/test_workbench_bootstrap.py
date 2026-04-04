import json
from pathlib import Path
import numpy as np

from app.models import OCRBlock
from app.services.artifacts import ArtifactStore
from app.workbench.bootstrap import WorkbenchBootstrapService


class FakeOCRService:
    def run(self, image_path: Path) -> tuple[dict, list[OCRBlock]]:
        return (
            {"engine": "fake-ocr", "pages": 1},
            [OCRBlock(text="姓名", bbox=[0, 0, 10, 10], block_type="text")],
        )


def test_bootstrap_uses_ocr_service_outputs_for_artifacts(tmp_path: Path) -> None:
    artifact_store = ArtifactStore(tmp_path / "runs")
    bootstrap = WorkbenchBootstrapService(
        artifact_store=artifact_store,
        ocr_service=FakeOCRService(),
    )

    request = bootstrap.create_request_from_upload(
        filename="form.png",
        content=b"fake-image",
    )

    run_dir = artifact_store.run_root / request.run_id
    ocr_raw = json.loads((run_dir / "ocr_raw.json").read_text(encoding="utf-8"))
    ocr_compact = json.loads((run_dir / "ocr_compact.json").read_text(encoding="utf-8"))

    assert request.source_image_name == "form.png"
    assert ocr_raw == {"engine": "fake-ocr", "pages": 1}
    assert ocr_compact == [
        {
            "text": "姓名",
            "bbox": [0, 0, 10, 10],
            "block_type": "text",
        }
    ]


def test_bootstrap_serializes_numpy_values_in_raw_ocr_payload(tmp_path: Path) -> None:
    class FakeNumpyOCRService:
        def run(self, image_path: Path):
            del image_path
            return (
                {"dt_polys": [np.array([[0, 0], [10, 0], [10, 20], [0, 20]])]},
                [OCRBlock(text="姓名", bbox=[0, 0, 10, 20], block_type="text")],
            )

    artifact_store = ArtifactStore(tmp_path / "runs")
    bootstrap = WorkbenchBootstrapService(
        artifact_store=artifact_store,
        ocr_service=FakeNumpyOCRService(),
    )

    request = bootstrap.create_request_from_upload("form.png", b"fake-image")
    run_dir = artifact_store.run_root / request.run_id
    raw_payload = json.loads((run_dir / "ocr_raw.json").read_text(encoding="utf-8"))

    assert raw_payload["dt_polys"] == [[[0, 0], [10, 0], [10, 20], [0, 20]]]
