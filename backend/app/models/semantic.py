from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True, populate_by_name=True)

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class EvidenceRef(ContractModel):
    source_id: str
    source_type: Literal[
        "text_box",
        "table_cell",
        "table_region",
        "checkbox_region",
        "image_region",
    ]
    bbox: list[float]
    page: int = 1


class SemanticWarning(ContractModel):
    code: str
    message: str
    severity: Literal["low", "medium", "high"]
    related_field_keys: list[str] = Field(default_factory=list)


class LayoutHints(ContractModel):
    section_order: list[str]
    preferred_columns: dict[str, int]
    section_spans: dict[str, Literal["full", "left", "right", "table"]]


class TableColumnSpec(ContractModel):
    key: str
    title: str
    kind: Literal["string", "datetime", "textarea", "boolean"] = "string"
    order: int
    required: bool = False


class SemanticField(ContractModel):
    key: str
    title: str
    kind: Literal["string", "datetime", "textarea", "boolean", "array-table"]
    section_key: str
    field_role: str
    value: str | bool | list[dict[str, object]] | None
    table_columns: list[TableColumnSpec] | None = None
    confidence: float
    evidence: list[EvidenceRef]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_table_columns(self) -> "SemanticField":
        if self.kind == "array-table" and not self.table_columns:
            raise ValueError("array-table fields require table_columns metadata")
        if self.kind != "array-table" and self.table_columns is not None:
            raise ValueError("table_columns is only valid for array-table fields")
        return self


class SemanticSection(ContractModel):
    key: str
    title: str
    field_keys: list[str]
    order: int
    section_type: Literal["basic", "group", "table", "long_text"]


class FormMeta(ContractModel):
    title: str | None = None
    document_type: str | None = None
    document_number: str | None = None


class SemanticFormModel(ContractModel):
    form_meta: FormMeta
    sections: list[SemanticSection]
    fields: list[SemanticField]
    layout_hints: LayoutHints
    warnings: list[SemanticWarning] = Field(default_factory=list)
