from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


ConfidenceScore = Annotated[StrictFloat, Field(ge=0.0, le=1.0)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True, populate_by_name=True)

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class EvidenceRef(ContractModel):
    source_id: StrictStr
    source_type: Literal[
        "text_box",
        "table_cell",
        "table_region",
        "checkbox_region",
        "image_region",
    ]
    bbox: list[StrictFloat]
    page: StrictInt = 1

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, value: list[float]) -> list[float]:
        if len(value) != 4:
            raise ValueError("bbox must contain exactly 4 coordinates")
        return value


class SemanticWarning(ContractModel):
    code: StrictStr
    message: StrictStr
    severity: Literal["low", "medium", "high"]
    related_field_keys: list[StrictStr] = Field(default_factory=list)


class LayoutHints(ContractModel):
    section_order: list[StrictStr]
    preferred_columns: dict[StrictStr, StrictInt]
    section_spans: dict[StrictStr, Literal["full", "left", "right", "table"]]


class TableColumnSpec(ContractModel):
    key: StrictStr
    title: StrictStr
    kind: Literal["string", "datetime", "textarea", "boolean"] = "string"
    order: StrictInt
    required: StrictBool = False


class SemanticField(ContractModel):
    key: StrictStr
    title: StrictStr
    kind: Literal["string", "datetime", "textarea", "boolean", "array-table"]
    section_key: StrictStr
    field_role: StrictStr
    value: StrictStr | StrictBool | list[dict[StrictStr, Any]] | None
    table_columns: list[TableColumnSpec] | None = None
    confidence: ConfidenceScore
    evidence: list[EvidenceRef]
    warnings: list[StrictStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_table_columns(self) -> "SemanticField":
        if self.kind == "array-table" and not self.table_columns:
            raise ValueError("array-table fields require table_columns metadata")
        if self.kind != "array-table" and self.table_columns is not None:
            raise ValueError("table_columns is only valid for array-table fields")
        if self.kind == "boolean" and self.value is not None and not isinstance(self.value, bool):
            raise ValueError("boolean fields require a boolean value")
        if self.kind == "array-table" and self.value is not None and not isinstance(self.value, list):
            raise ValueError("array-table fields require a list value")
        if (
            self.kind in {"string", "datetime", "textarea"}
            and self.value is not None
            and not isinstance(self.value, str)
        ):
            raise ValueError(f"{self.kind} fields require a string value")
        return self


class SemanticSection(ContractModel):
    key: StrictStr
    title: StrictStr
    field_keys: list[StrictStr]
    order: StrictInt
    section_type: Literal["basic", "group", "table", "long_text"]


class FormMeta(ContractModel):
    title: StrictStr | None = None
    document_type: StrictStr | None = None
    document_number: StrictStr | None = None


class SemanticFormModel(ContractModel):
    form_meta: FormMeta
    sections: list[SemanticSection]
    fields: list[SemanticField]
    layout_hints: LayoutHints
    warnings: list[SemanticWarning] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "SemanticFormModel":
        section_keys = [section.key for section in self.sections]
        if len(section_keys) != len(set(section_keys)):
            raise ValueError("sections must use unique keys")

        field_keys = [field.key for field in self.fields]
        if len(field_keys) != len(set(field_keys)):
            raise ValueError("fields must use unique keys")

        section_key_set = set(section_keys)
        field_by_key = {field.key: field for field in self.fields}

        for field in self.fields:
            if field.section_key not in section_key_set:
                raise ValueError(f"field {field.key} references unknown section {field.section_key}")

        for section in self.sections:
            for field_key in section.field_keys:
                field = field_by_key.get(field_key)
                if field is None:
                    raise ValueError(f"section {section.key} references unknown field {field_key}")
                if field.section_key != section.key:
                    raise ValueError(
                        f"section {section.key} references field {field_key} owned by {field.section_key}"
                    )

        layout_section_keys = set(self.layout_hints.section_order)
        layout_section_keys.update(self.layout_hints.preferred_columns.keys())
        layout_section_keys.update(self.layout_hints.section_spans.keys())
        unknown_layout_sections = sorted(layout_section_keys - section_key_set)
        if unknown_layout_sections:
            raise ValueError(
                "layout_hints references unknown sections: " + ", ".join(unknown_layout_sections)
            )

        return self
