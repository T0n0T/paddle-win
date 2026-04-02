from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CHECKED_MARKS = {"√", "✓", "✔", "☑"}
UNCHECKED_MARKS = {"□", "☐"}


@dataclass(slots=True)
class TextBox:
    box_id: str
    text: str
    bbox: list[float]
    confidence: float | None = None


@dataclass(slots=True)
class TableCell:
    cell_id: str
    row: int
    col: int
    bbox: list[float]
    text: str
    confidence: float | None = None


@dataclass(slots=True)
class TableRegion:
    table_id: str
    bbox: list[float]
    cells: list[TableCell] = field(default_factory=list)


@dataclass(slots=True)
class CheckboxRegion:
    region_id: str
    bbox: list[float]
    confidence: float | None = None
    checked: bool | None = None


@dataclass(slots=True)
class UnderlineFillRegion:
    region_id: str
    bbox: list[float]
    confidence: float | None = None
    text_box_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LayoutSkeleton:
    page_count: int
    image_size: dict[str, int]
    text_boxes: list[TextBox]
    tables: list[TableRegion]
    checkbox_regions: list[CheckboxRegion]
    underline_fill_regions: list[UnderlineFillRegion]
    reading_order: list[str]


def _as_bbox(value: list[Any]) -> list[float]:
    if len(value) not in {4, 8}:
        raise ValueError("bbox must contain 4 or 8 coordinates")
    if len(value) == 8:
        xs = [float(value[index]) for index in range(0, 8, 2)]
        ys = [float(value[index]) for index in range(1, 8, 2)]
        return [min(xs), min(ys), max(xs), max(ys)]
    return [float(coord) for coord in value]


def _bbox_width(bbox: list[float]) -> float:
    return bbox[2] - bbox[0]


def _bbox_height(bbox: list[float]) -> float:
    return bbox[3] - bbox[1]


def _intersection_ratio(lhs: list[float], rhs: list[float]) -> float:
    left = max(lhs[0], rhs[0])
    top = max(lhs[1], rhs[1])
    right = min(lhs[2], rhs[2])
    bottom = min(lhs[3], rhs[3])
    if left >= right or top >= bottom:
        return 0.0
    intersection = (right - left) * (bottom - top)
    rhs_area = max((rhs[2] - rhs[0]) * (rhs[3] - rhs[1]), 1.0)
    return intersection / rhs_area


def _iou(lhs: list[float], rhs: list[float]) -> float:
    left = max(lhs[0], rhs[0])
    top = max(lhs[1], rhs[1])
    right = min(lhs[2], rhs[2])
    bottom = min(lhs[3], rhs[3])
    if left >= right or top >= bottom:
        return 0.0
    intersection = (right - left) * (bottom - top)
    lhs_area = max((lhs[2] - lhs[0]) * (lhs[3] - lhs[1]), 1.0)
    rhs_area = max((rhs[2] - rhs[0]) * (rhs[3] - rhs[1]), 1.0)
    return intersection / (lhs_area + rhs_area - intersection)


def _dedupe_sorted(values: list[float], tolerance: float = 8.0) -> list[float]:
    unique_values: list[float] = []
    for value in sorted(values):
        if not unique_values or abs(value - unique_values[-1]) > tolerance:
            unique_values.append(value)
    return unique_values


def _axis_index(coord: float, axis_values: list[float], tolerance: float = 8.0) -> int:
    for index, value in enumerate(axis_values, start=1):
        if abs(coord - value) <= tolerance:
            return index
    return len(axis_values)


def _normalize_ocr_triplet(
    boxes_raw: list[list[Any]],
    texts_raw: list[Any],
    scores_raw: list[Any],
    label: str,
) -> tuple[list[list[float]], list[str], list[float | None]]:
    boxes = [_as_bbox(box) for box in boxes_raw]
    texts = [str(text) for text in texts_raw]
    if len(texts) != len(boxes):
        raise ValueError(f"{label} rec_texts and rec_boxes must have the same length")

    scores: list[float | None] = []
    for index in range(len(texts)):
        if index < len(scores_raw):
            scores.append(float(scores_raw[index]))
        else:
            scores.append(None)
    return boxes, texts, scores


def _match_cell_text(
    cell_bbox: list[float],
    rec_boxes: list[list[float]],
    rec_texts: list[str],
    rec_scores: list[float | None],
) -> tuple[str, float | None]:
    matches: list[tuple[str, float | None]] = []
    for rec_bbox, rec_text, rec_score in zip(rec_boxes, rec_texts, rec_scores):
        if _intersection_ratio(cell_bbox, rec_bbox) >= 0.5:
            matches.append((rec_text, rec_score))

    if not matches:
        return "", None

    text = " ".join(item[0] for item in matches if item[0]).strip()
    confidences = [item[1] for item in matches if item[1] is not None]
    confidence = min(confidences) if confidences else None
    return text, confidence


def _infer_checkbox_regions(text_boxes: list[TextBox]) -> list[CheckboxRegion]:
    checkbox_regions: list[CheckboxRegion] = []
    for index, box in enumerate(text_boxes, start=1):
        text = box.text.strip()
        if text in CHECKED_MARKS | UNCHECKED_MARKS:
            checkbox_regions.append(
                CheckboxRegion(
                    region_id=f"checkbox_{index}",
                    bbox=box.bbox,
                    confidence=box.confidence,
                    checked=text in CHECKED_MARKS,
                )
            )
    return checkbox_regions


def _infer_underline_fill_regions(
    text_boxes: list[TextBox],
    image_width: int,
    table_bboxes: list[list[float]],
) -> list[UnderlineFillRegion]:
    underline_regions: list[UnderlineFillRegion] = []
    region_index = 1
    for box in text_boxes:
        text = box.text.strip()
        if not text or text in CHECKED_MARKS | UNCHECKED_MARKS:
            continue
        if any(_intersection_ratio(table_bbox, box.bbox) >= 0.4 for table_bbox in table_bboxes):
            continue

        width = _bbox_width(box.bbox)
        height = max(_bbox_height(box.bbox), 1.0)
        if width / height < 2.0:
            continue
        if width > image_width * 0.3:
            continue
        if len(text) > 12:
            continue
        if not any(
            abs(((candidate.bbox[1] + candidate.bbox[3]) / 2) - ((box.bbox[1] + box.bbox[3]) / 2)) <= 18
            and candidate.bbox[2] <= box.bbox[0]
            and candidate.box_id != box.box_id
            for candidate in text_boxes
        ):
            continue

        underline_regions.append(
            UnderlineFillRegion(
                region_id=f"underline_{region_index}",
                bbox=box.bbox,
                confidence=box.confidence,
                text_box_ids=[box.box_id],
            )
        )
        region_index += 1
    return underline_regions


def _bbox_from_cells(cell_boxes: list[list[float]]) -> list[float]:
    return [
        min(box[0] for box in cell_boxes),
        min(box[1] for box in cell_boxes),
        max(box[2] for box in cell_boxes),
        max(box[3] for box in cell_boxes),
    ]


def _match_table_bbox(
    cell_boxes: list[list[float]],
    candidate_layout_boxes: list[list[float]],
) -> list[float]:
    if not cell_boxes:
        return []
    table_bbox = _bbox_from_cells(cell_boxes)
    if not candidate_layout_boxes:
        return table_bbox

    best_index = max(
        range(len(candidate_layout_boxes)),
        key=lambda index: _iou(table_bbox, candidate_layout_boxes[index]),
    )
    if _iou(table_bbox, candidate_layout_boxes[best_index]) <= 0:
        return table_bbox
    return candidate_layout_boxes.pop(best_index)


def normalize_layout(payload: dict[str, Any]) -> LayoutSkeleton:
    overall_ocr_res = payload.get("overall_ocr_res", {})
    rec_boxes, rec_texts, rec_scores = _normalize_ocr_triplet(
        overall_ocr_res.get("rec_boxes", []),
        overall_ocr_res.get("rec_texts", []),
        overall_ocr_res.get("rec_scores", []),
        "overall_ocr_res",
    )

    text_boxes = [
        TextBox(
            box_id=f"box_{index}",
            text=text,
            bbox=bbox,
            confidence=confidence,
        )
        for index, (bbox, text, confidence) in enumerate(
            zip(rec_boxes, rec_texts, rec_scores),
            start=1,
        )
    ]

    layout_boxes = payload.get("layout_det_res", {}).get("boxes", [])
    table_layout_boxes = [
        _as_bbox(item.get("coordinate", []))
        for item in layout_boxes
        if item.get("label") == "table"
    ]

    tables: list[TableRegion] = []
    for table_index, table in enumerate(payload.get("table_res_list", []), start=1):
        table_id = f"table_{table.get('table_region_id', table_index)}"
        cell_boxes = [_as_bbox(box) for box in table.get("cell_box_list", [])]
        x_positions = _dedupe_sorted([box[0] for box in cell_boxes])
        y_positions = _dedupe_sorted([box[1] for box in cell_boxes])

        table_ocr_pred = table.get("table_ocr_pred", {})
        table_rec_boxes, table_rec_texts, table_rec_scores = _normalize_ocr_triplet(
            table_ocr_pred.get("rec_boxes", []),
            table_ocr_pred.get("rec_texts", []),
            table_ocr_pred.get("rec_scores", []),
            f"table_res_list[{table_index - 1}].table_ocr_pred",
        )

        cells = []
        for cell_index, cell_bbox in enumerate(cell_boxes, start=1):
            cell_text, confidence = _match_cell_text(
                cell_bbox,
                table_rec_boxes,
                table_rec_texts,
                table_rec_scores,
            )
            cells.append(
                TableCell(
                    cell_id=f"{table_id}_cell_{cell_index}",
                    row=_axis_index(cell_bbox[1], y_positions),
                    col=_axis_index(cell_bbox[0], x_positions),
                    bbox=cell_bbox,
                    text=cell_text,
                    confidence=confidence,
                )
            )

        table_bbox = _match_table_bbox(cell_boxes, table_layout_boxes)

        tables.append(TableRegion(table_id=table_id, bbox=table_bbox, cells=cells))

    image_width = int(payload.get("doc_preprocessor_res", {}).get("output_img_shape", [0, 0])[1])
    image_height = int(payload.get("doc_preprocessor_res", {}).get("output_img_shape", [0, 0])[0])
    if not image_width and rec_boxes:
        image_width = int(max(box[2] for box in rec_boxes))
    if not image_height and rec_boxes:
        image_height = int(max(box[3] for box in rec_boxes))

    table_bboxes = [table.bbox for table in tables if table.bbox]
    checkbox_regions = _infer_checkbox_regions(text_boxes)
    underline_fill_regions = _infer_underline_fill_regions(text_boxes, image_width, table_bboxes)

    return LayoutSkeleton(
        page_count=1 if payload.get("page_index") is None else int(payload.get("page_index", 0)) + 1,
        image_size={"width": image_width, "height": image_height},
        text_boxes=text_boxes,
        tables=tables,
        checkbox_regions=checkbox_regions,
        underline_fill_regions=underline_fill_regions,
        reading_order=[box.box_id for box in text_boxes] + [table.table_id for table in tables],
    )
