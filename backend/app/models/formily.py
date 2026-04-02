from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.models.semantic import ContractModel


class FormilyXData(ContractModel):
    confidence: float
    source_boxes: list[str]
    section_key: str
    field_role: str
    warnings: list[str] = Field(default_factory=list)


class FormilySchemaNode(ContractModel):
    type: Literal["object", "void", "string", "boolean", "array"]
    title: str | None = None
    properties: dict[str, "FormilySchemaNode"] | None = None
    items: "FormilySchemaNode | None" = None
    default: str | bool | list[dict[str, object]] | None = None
    x_component: str | None = Field(default=None, alias="x-component")
    x_component_props: dict[str, Any] | None = Field(default=None, alias="x-component-props")
    x_decorator: str | None = Field(default=None, alias="x-decorator")
    x_decorator_props: dict[str, Any] | None = Field(default=None, alias="x-decorator-props")
    x_data: FormilyXData | None = Field(default=None, alias="x-data")


class FormilySchemaEnvelope(ContractModel):
    schema_: FormilySchemaNode = Field(alias="schema")


FormilySchemaNode.model_rebuild()
