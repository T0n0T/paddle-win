from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class OCRBlock(BaseModel):
    text: str
    bbox: list[float] = Field(default_factory=list)
    block_type: str = "text"


class PipelineState(BaseModel):
    image_path: Path
    run_dir: Path | None = None
    source_image_path: Path | None = None
    ocr_raw_path: Path | None = None
    ocr_compact_path: Path | None = None
    prompt_path: Path | None = None
    model_raw_path: Path | None = None
    result_html_path: Path | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
