from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any


class PaddleTableV2Client:
    """Thin wrapper around the official PaddleOCR table_recognition_v2 entrypoint."""

    def __init__(self) -> None:
        self._pipeline: Any | None = None

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            paddleocr = import_module("paddleocr")
            self._pipeline = paddleocr.TableRecognitionPipelineV2()
        return self._pipeline

    def run(self, image_path: Path) -> dict[str, Any]:
        predictions = iter(self._get_pipeline().predict(image_path))
        try:
            prediction = next(predictions)
        except StopIteration as exc:
            raise ValueError("TableRecognitionPipelineV2 returned no predictions") from exc
        if isinstance(prediction, dict):
            return prediction

        if hasattr(prediction, "json"):
            payload = prediction.json()
            if isinstance(payload, str):
                return json.loads(payload)
            if isinstance(payload, dict):
                return payload

        raise TypeError("TableRecognitionPipelineV2 prediction must expose dict or json() payload")
