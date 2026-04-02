from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACT_ROOT = Path(__file__).resolve().parents[3] / "data" / "jobs"


@dataclass(frozen=True)
class JobArtifacts:
    root: Path
    job_id: str

    def __post_init__(self) -> None:
        job_path = Path(self.job_id)
        if self.job_id in {"", ".", ".."} or job_path.is_absolute() or len(job_path.parts) != 1:
            raise ValueError("job_id must be a single relative path segment")

    @classmethod
    def for_job(cls, job_id: str, root: Path | None = None) -> "JobArtifacts":
        return cls(root=root or DEFAULT_ARTIFACT_ROOT, job_id=job_id)

    @property
    def job_dir(self) -> Path:
        return self.root / self.job_id

    @property
    def source_image_path(self) -> Path:
        return self.job_dir / "source.jpg"

    @property
    def ocr_json_path(self) -> Path:
        return self.job_dir / "ocr.json"

    @property
    def layout_json_path(self) -> Path:
        return self.job_dir / "layout.json"

    @property
    def semantic_json_path(self) -> Path:
        return self.job_dir / "semantic.json"

    @property
    def schema_json_path(self) -> Path:
        return self.job_dir / "schema.json"

    def write_source_image(self, content: bytes) -> Path:
        return self._write_bytes(self.source_image_path, content)

    def write_ocr_json(self, payload: dict[str, Any] | list[Any]) -> Path:
        return self._write_json(self.ocr_json_path, payload)

    def write_layout_json(self, payload: dict[str, Any] | list[Any]) -> Path:
        return self._write_json(self.layout_json_path, payload)

    def write_semantic_json(self, payload: dict[str, Any] | list[Any]) -> Path:
        return self._write_json(self.semantic_json_path, payload)

    def write_schema_json(self, payload: dict[str, Any] | list[Any]) -> Path:
        return self._write_json(self.schema_json_path, payload)

    def _write_bytes(self, path: Path, content: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _write_json(self, path: Path, payload: dict[str, Any] | list[Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
