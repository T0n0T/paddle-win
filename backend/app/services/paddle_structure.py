from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import numpy as np
from paddleocr import PaddleOCR

from app.models import OCRBlock


class PaddleStructureService:
    def __init__(self, ocr_client: Any | None = None) -> None:
        self.ocr_client = ocr_client

    def run(self, image_path: Path) -> tuple[dict[str, Any], list[OCRBlock]]:
        client = self.ocr_client or PaddleOCR(lang="ch", use_doc_orientation_classify=False)
        result = client.ocr(str(image_path))
        raw_result = {"engine": "paddleocr", "pages": self._dump_pages(result)}
        blocks = self._to_blocks(result)
        if not blocks:
            raise ValueError("no OCR text blocks detected")
        return raw_result, blocks

    def _to_blocks(self, result: list[Any]) -> list[OCRBlock]:
        blocks: list[OCRBlock] = []
        for page in result:
            page_payload = self._item_to_dict(page)
            rec_texts = page_payload.get("rec_texts")
            page_boxes = self._coerce_sequence(
                self._first_non_empty(page_payload.get("dt_polys"), page_payload.get("text_boxes"))
            )
            if isinstance(rec_texts, list):
                for index, text_value in enumerate(rec_texts):
                    text = str(text_value).strip()
                    if not text:
                        continue
                    bbox = []
                    if page_boxes and index < len(page_boxes):
                        bbox = self._normalize_bbox(page_boxes[index])
                    blocks.append(OCRBlock(text=text, bbox=bbox, block_type="text"))
                continue

            for item in self._iter_page_items(page):
                payload = self._item_to_dict(item)
                if not payload:
                    continue
                text = str(payload.get("rec_text", payload.get("text", ""))).strip()
                if not text:
                    continue
                bbox = self._normalize_bbox(
                    self._first_non_empty(
                        payload.get("dt_polys"),
                        payload.get("text_boxes"),
                        payload.get("bbox"),
                    )
                )
                blocks.append(OCRBlock(text=text, bbox=bbox, block_type="text"))
        return blocks

    def _dump_pages(self, result: list[Any]) -> list[Any]:
        dumped: list[Any] = []
        for page in result:
            if isinstance(page, list):
                dumped.append([self._item_to_dict(item) for item in page])
            else:
                dumped.append(self._item_to_dict(page))
        return dumped

    def _iter_page_items(self, page: Any) -> list[Any]:
        if isinstance(page, list):
            return page
        for attr in ("res", "result", "data"):
            value = getattr(page, attr, None)
            if isinstance(value, list):
                return value
        return []

    def _item_to_dict(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        if hasattr(item, "to_dict"):
            value = item.to_dict()
            if isinstance(value, dict):
                return value
        if hasattr(item, "model_dump"):
            value = item.model_dump(mode="json")
            if isinstance(value, dict):
                return value
        if hasattr(item, "__dict__"):
            return {
                key: self._to_jsonable(value)
                for key, value in vars(item).items()
                if not key.startswith("_")
            }
        try:
            value = json.loads(str(item))
            if isinstance(value, dict):
                return value
        except Exception:
            pass
        return {}

    def _to_jsonable(self, value: Any) -> Any:
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, tuple):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        return value

    def _coerce_sequence(self, value: Any) -> list[Any]:
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, tuple):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, list):
            return value
        return []

    def _first_non_empty(self, *values: Any) -> Any:
        for value in values:
            if isinstance(value, np.ndarray):
                if value.size > 0:
                    return value
                continue
            if isinstance(value, (list, tuple, dict, str)):
                if value:
                    return value
                continue
            if value is not None:
                return value
        return None

    def _normalize_bbox(self, dt_polys: Any) -> list[float]:
        points = self._coerce_sequence(dt_polys)
        if not points:
            return []
        xs: list[float] = []
        ys: list[float] = []
        for point in points:
            normalized_point = self._coerce_sequence(point)
            if len(normalized_point) < 2:
                continue
            try:
                xs.append(float(normalized_point[0]))
                ys.append(float(normalized_point[1]))
            except (TypeError, ValueError):
                continue
        if not xs or not ys:
            return []
        return [min(xs), min(ys), max(xs), max(ys)]
