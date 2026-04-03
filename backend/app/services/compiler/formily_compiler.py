from __future__ import annotations

from datetime import datetime
from typing import Iterable

from app.models.formily import FormilySchemaEnvelope, FormilySchemaNode, FormilyXData
from app.models.semantic import SemanticField, SemanticFormModel, SemanticSection, TableColumnSpec
from app.services.compiler.validator import validate_semantic_model


def _normalize_datetime(value: str | None) -> str | None:
    if value is None:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    normalized = candidate.replace("Z", "+00:00").replace(" ", "T")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.isoformat() + "+08:00"
    return dt.isoformat()


def _make_x_data(field: SemanticField) -> FormilyXData:
    return FormilyXData(
        confidence=field.confidence,
        source_boxes=[evidence.source_id for evidence in field.evidence],
        section_key=field.section_key,
        field_role=field.field_role,
        warnings=field.warnings,
    )


def _compile_scalar_field(field: SemanticField) -> FormilySchemaNode:
    component_by_kind = {
        "string": "Input",
        "textarea": "Input.TextArea",
        "boolean": "Checkbox",
        "datetime": "DatePicker",
    }
    node_type = "boolean" if field.kind == "boolean" else "string"
    component_props = {"showTime": True} if field.kind == "datetime" else None
    default_value = field.value
    if field.kind == "datetime":
        default_value = _normalize_datetime(field.value if isinstance(field.value, str) else None)

    return FormilySchemaNode(
        type=node_type,
        title=field.title,
        x_decorator="FormItem",
        x_component=component_by_kind[field.kind],
        x_component_props=component_props,
        default=default_value,
        x_data=_make_x_data(field),
    )


def _compile_table_column(column: TableColumnSpec) -> FormilySchemaNode:
    component_by_kind = {
        "string": "Input",
        "textarea": "Input.TextArea",
        "boolean": "Checkbox",
        "datetime": "DatePicker",
    }
    node_type = "boolean" if column.kind == "boolean" else "string"
    component_props = {"showTime": True} if column.kind == "datetime" else None

    return FormilySchemaNode(
        type="void",
        x_component="ArrayTable.Column",
        x_component_props={"title": column.title},
        properties={
            column.key: FormilySchemaNode(
                type=node_type,
                x_decorator="FormItem",
                x_component=component_by_kind[column.kind],
                x_component_props=component_props,
            )
        },
    )


def _compile_array_table(field: SemanticField) -> FormilySchemaNode:
    assert field.table_columns is not None
    ordered_columns = sorted(field.table_columns, key=lambda item: item.order)
    items_properties = {
        f"{column.key}_column": _compile_table_column(column) for column in ordered_columns
    }

    return FormilySchemaNode(
        type="array",
        title=field.title,
        x_decorator="FormItem",
        x_component="ArrayTable",
        default=field.value,
        items=FormilySchemaNode(type="object", properties=items_properties),
        x_data=_make_x_data(field),
    )


def _resolve_field_keys(fields: list[SemanticField], section: SemanticSection) -> dict[int, str]:
    resolved: dict[int, str] = {}
    used: set[str] = set()
    ordinal = 1

    for index, field in enumerate(fields, start=1):
        base_key = field.key or f"{section.key}__field_{ordinal}"
        if base_key in used:
            base_key = f"{section.key}__{base_key}_{index}"
        used.add(base_key)
        resolved[index - 1] = base_key
        ordinal += 1

    return resolved


def _compile_section(section: SemanticSection, fields: list[SemanticField], preferred_columns: int) -> FormilySchemaNode:
    key_map = _resolve_field_keys(fields, section)
    properties: dict[str, FormilySchemaNode] = {}

    for index, field in enumerate(fields):
        schema_key = key_map[index]
        if field.kind == "array-table":
            properties[schema_key] = _compile_array_table(field)
        else:
            properties[schema_key] = _compile_scalar_field(field)

    return FormilySchemaNode(
        type="void",
        title=section.title,
        x_component="FormGrid",
        x_component_props={"maxColumns": preferred_columns, "minColumns": 1},
        properties=properties,
    )


def compile_formily(model: SemanticFormModel) -> FormilySchemaEnvelope:
    validated = validate_semantic_model(model)
    fields_by_key = {field.key: field for field in validated.fields}
    ordered_sections = sorted(
        validated.sections,
        key=lambda item: (
            validated.layout_hints.section_order.index(item.key)
            if item.key in validated.layout_hints.section_order
            else item.order
        ),
    )
    schema_properties = {}

    for section in ordered_sections:
        section_fields = [fields_by_key[field_key] for field_key in section.field_keys]
        preferred_columns = validated.layout_hints.preferred_columns.get(section.key, 1)
        schema_properties[section.key] = _compile_section(section, section_fields, preferred_columns)

    return FormilySchemaEnvelope(schema=FormilySchemaNode(type="object", properties=schema_properties))


def collect_field_confidences(node: FormilySchemaNode) -> list[float]:
    confidences: list[float] = []

    def walk(current: FormilySchemaNode) -> None:
        if current.x_data is not None:
            confidences.append(float(current.x_data.confidence))
        if current.properties:
            for child in current.properties.values():
                walk(child)
        if current.items is not None:
            walk(current.items)

    walk(node)
    return confidences
