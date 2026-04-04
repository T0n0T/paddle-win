from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import OCRBlock
from app.services.artifacts import ArtifactStore
from app.workbench.models import CreateSessionRequest


class WorkbenchBootstrapService:
    def __init__(self, artifact_store: ArtifactStore, ocr_service: Any) -> None:
        self.artifact_store = artifact_store
        self.ocr_service = ocr_service

    def create_request_from_upload(self, filename: str, content: bytes) -> CreateSessionRequest:
        run_dir, source_image_path = self.artifact_store.create_run_from_upload(filename, content)
        raw_result, compact_blocks = self.ocr_service.run(source_image_path)
        self.artifact_store.write_text(
            run_dir,
            "ocr_raw.json",
            json.dumps(self._to_jsonable(raw_result), ensure_ascii=False, indent=2),
        )
        ocr_json_path = self.artifact_store.write_text(
            run_dir,
            "ocr_compact.json",
            json.dumps(
                [self._dump_block(block) for block in compact_blocks],
                ensure_ascii=False,
                indent=2,
            ),
        )
        return CreateSessionRequest(
            image_path=source_image_path,
            ocr_json_path=ocr_json_path,
            run_id=run_dir.name,
            source_image_name=filename,
        )

    def _dump_block(self, block: OCRBlock | dict[str, Any]) -> dict[str, Any]:
        if isinstance(block, OCRBlock):
            return block.model_dump(mode="json")
        return dict(block)

    def _to_jsonable(self, value: Any) -> Any:
        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            return tolist()
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, tuple):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if hasattr(value, "__dict__"):
            return {
                key: self._to_jsonable(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        return str(value)
