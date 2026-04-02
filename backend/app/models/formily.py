from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, StrictBool, StrictStr, model_validator

from app.models.semantic import ConfidenceScore, ContractModel


class FormilyXData(ContractModel):
    confidence: ConfidenceScore
    source_boxes: list[StrictStr]
    section_key: StrictStr
    field_role: StrictStr
    warnings: list[StrictStr] = Field(default_factory=list)


class FormilySchemaNode(ContractModel):
    type: Literal["object", "void", "string", "boolean", "array"]
    title: StrictStr | None = None
    properties: dict[StrictStr, "FormilySchemaNode"] | None = None
    items: "FormilySchemaNode | None" = None
    default: StrictStr | StrictBool | list[dict[StrictStr, Any]] | None = None
    x_component: StrictStr | None = Field(default=None, alias="x-component")
    x_component_props: dict[StrictStr, Any] | None = Field(default=None, alias="x-component-props")
    x_decorator: StrictStr | None = Field(default=None, alias="x-decorator")
    x_decorator_props: dict[StrictStr, Any] | None = Field(default=None, alias="x-decorator-props")
    x_data: FormilyXData | None = Field(default=None, alias="x-data")

    @classmethod
    def _default_matches_node(cls, node: "FormilySchemaNode", value: Any) -> bool:
        if node.type == "string":
            return isinstance(value, str)
        if node.type == "boolean":
            return isinstance(value, bool)
        if node.type == "array":
            return (
                isinstance(value, list)
                and node.items is not None
                and all(cls._default_matches_node(node.items, item) for item in value)
            )
        if node.type in {"object", "void"}:
            if not isinstance(value, dict) or node.properties is None:
                return False
            for key, item in value.items():
                child = node.properties.get(key)
                if child is None or not cls._default_matches_node(child, item):
                    return False
            return True
        return False

    @model_validator(mode="after")
    def validate_shape(self) -> "FormilySchemaNode":
        if self.type in {"object", "void"}:
            if self.properties is None:
                raise ValueError(f"{self.type} schema nodes require properties")
            if self.items is not None:
                raise ValueError(f"{self.type} schema nodes do not support items")
            if self.default is not None:
                raise ValueError(f"{self.type} schema nodes do not support default")
            return self

        if self.type == "array":
            if self.items is None:
                raise ValueError("array schema nodes require items")
            if self.properties is not None:
                raise ValueError("array schema nodes do not support properties")
            if self.default is not None and not isinstance(self.default, list):
                raise ValueError("array schema nodes require a list default")
            if self.default is not None and any(
                not self._default_matches_node(self.items, item) for item in self.default
            ):
                raise ValueError("array schema node default items must match the items schema")
            return self

        if self.properties is not None:
            raise ValueError(f"{self.type} schema nodes do not support properties")
        if self.items is not None:
            raise ValueError(f"{self.type} schema nodes do not support items")
        if self.type == "string" and self.default is not None and not isinstance(self.default, str):
            raise ValueError("string schema nodes require a string default")
        if self.type == "boolean" and self.default is not None and not isinstance(self.default, bool):
            raise ValueError("boolean schema nodes require a boolean default")
        return self


class FormilySchemaEnvelope(ContractModel):
    schema_: FormilySchemaNode = Field(alias="schema")


FormilySchemaNode.model_rebuild()
