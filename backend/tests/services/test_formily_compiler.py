from app.models.formily import FormilySchemaEnvelope
from app.models.semantic import (
    EvidenceRef,
    FormMeta,
    LayoutHints,
    SemanticField,
    SemanticFormModel,
    SemanticSection,
    TableColumnSpec,
)
from app.services.compiler.formily_compiler import (
    collect_field_confidences,
    compile_formily,
)
from app.services.compiler.validator import load_semantic_model_from_file


def sample_semantic_form_model() -> SemanticFormModel:
    return SemanticFormModel(
        form_meta=FormMeta(
            title="配电第一种工作票",
            document_type="电力工作票",
            document_number="2017070007",
        ),
        sections=[
            SemanticSection(
                key="basic_info",
                title="基本信息",
                field_keys=["work_leader", "plan_start_at", "safety_note", "executed"],
                order=1,
                section_type="basic",
            ),
            SemanticSection(
                key="work_items",
                title="工作任务",
                field_keys=["work_items_table"],
                order=2,
                section_type="table",
            ),
        ],
        fields=[
            SemanticField(
                key="work_leader",
                title="工作负责人",
                kind="string",
                section_key="basic_info",
                field_role="person_name",
                value="闫丽亚",
                confidence=0.98,
                evidence=[
                    EvidenceRef(
                        source_id="box_12",
                        source_type="text_box",
                        bbox=[120.0, 88.0, 210.0, 114.0],
                    )
                ],
                warnings=["low_contrast"],
            ),
            SemanticField(
                key="plan_start_at",
                title="计划工作开始时间",
                kind="datetime",
                section_key="basic_info",
                field_role="datetime_start",
                value="2016-07-24 15:30:00",
                confidence=0.91,
                evidence=[
                    EvidenceRef(
                        source_id="box_41",
                        source_type="text_box",
                        bbox=[240.0, 88.0, 380.0, 114.0],
                    )
                ],
            ),
            SemanticField(
                key="safety_note",
                title="安全措施",
                kind="textarea",
                section_key="basic_info",
                field_role="long_text",
                value="断开10kV白线55厂两线XX杆大段湾配变台区0.4kV大段湾出线剩余电流动作开关",
                confidence=0.87,
                evidence=[
                    EvidenceRef(
                        source_id="box_58",
                        source_type="text_box",
                        bbox=[80.0, 180.0, 520.0, 240.0],
                    )
                ],
            ),
            SemanticField(
                key="executed",
                title="已执行",
                kind="boolean",
                section_key="basic_info",
                field_role="status_checkbox",
                value=True,
                confidence=0.89,
                evidence=[
                    EvidenceRef(
                        source_id="checkbox_1",
                        source_type="checkbox_region",
                        bbox=[80.0, 260.0, 104.0, 284.0],
                    )
                ],
            ),
            SemanticField(
                key="work_items_table",
                title="工作任务",
                kind="array-table",
                section_key="work_items",
                field_role="table",
                value=[
                    {
                        "location_or_equipment": "10kV白55厂岗线XX杆大段湾台区",
                        "work_content": "安装关口表",
                    }
                ],
                table_columns=[
                    TableColumnSpec(
                        key="location_or_equipment",
                        title="工作地点或设备",
                        order=1,
                    ),
                    TableColumnSpec(
                        key="work_content",
                        title="工作内容",
                        order=2,
                    ),
                ],
                confidence=0.93,
                evidence=[
                    EvidenceRef(
                        source_id="table_1",
                        source_type="table_region",
                        bbox=[40.0, 320.0, 720.0, 520.0],
                    )
                ],
            ),
        ],
        layout_hints=LayoutHints(
            section_order=["basic_info", "work_items"],
            preferred_columns={"basic_info": 2, "work_items": 1},
            section_spans={"basic_info": "full", "work_items": "table"},
        ),
    )


def test_compile_array_table_uses_table_columns():
    schema = compile_formily(sample_semantic_form_model()).model_dump(by_alias=True)["schema"]
    table = schema["properties"]["work_items"]["properties"]["work_items_table"]

    assert table["x-component"] == "ArrayTable"
    assert "location_or_equipment_column" in table["items"]["properties"]
    assert "work_content_column" in table["items"]["properties"]


def test_compile_field_x_data_uses_source_ids_only():
    schema = compile_formily(sample_semantic_form_model()).model_dump(by_alias=True)["schema"]
    field = schema["properties"]["basic_info"]["properties"]["work_leader"]

    assert field["x-data"]["source_boxes"] == ["box_12"]


def test_compile_scalar_fields_to_expected_formily_components():
    schema = compile_formily(sample_semantic_form_model()).model_dump(by_alias=True)["schema"]
    section = schema["properties"]["basic_info"]

    assert section["type"] == "void"
    assert section["x-component"] == "FormGrid"
    assert section["x-component-props"] == {"maxColumns": 2, "minColumns": 1}
    assert section["properties"]["work_leader"]["x-component"] == "Input"
    assert section["properties"]["safety_note"]["x-component"] == "Input.TextArea"
    assert section["properties"]["executed"]["x-component"] == "Checkbox"


def test_compile_datetime_field_normalizes_timezone_fallback():
    schema = compile_formily(sample_semantic_form_model()).model_dump(by_alias=True)["schema"]
    field = schema["properties"]["basic_info"]["properties"]["plan_start_at"]

    assert field["x-component"] == "DatePicker"
    assert field["x-component-props"] == {"showTime": True}
    assert field["default"] == "2016-07-24T15:30:00+08:00"


def test_compile_preserves_array_default_rows():
    schema = compile_formily(sample_semantic_form_model()).model_dump(by_alias=True)["schema"]
    table = schema["properties"]["work_items"]["properties"]["work_items_table"]

    assert table["default"] == [
        {
            "location_or_equipment": "10kV白55厂岗线XX杆大段湾台区",
            "work_content": "安装关口表",
        }
    ]


def test_collect_field_confidences_returns_compiled_field_confidences():
    schema = compile_formily(sample_semantic_form_model())

    assert collect_field_confidences(schema.schema_) == [0.98, 0.91, 0.87, 0.89, 0.93]


def test_compile_formily_returns_valid_envelope():
    schema = compile_formily(sample_semantic_form_model())

    assert isinstance(schema, FormilySchemaEnvelope)


def test_compile_formily_makes_colliding_keys_deterministic():
    model = sample_semantic_form_model()
    model.fields[0].key = ""
    model.sections[0].field_keys = ["", "plan_start_at", "safety_note", "executed"]

    schema = compile_formily(model).model_dump(by_alias=True)["schema"]
    keys = list(schema["properties"]["basic_info"]["properties"].keys())

    assert "basic_info__field_1" in keys
    assert "plan_start_at" in keys


def test_load_semantic_model_from_file_accepts_validated_semantic_json(tmp_path):
    semantic_path = tmp_path / "semantic.json"
    semantic_path.write_text(
        sample_semantic_form_model().model_dump_json(indent=2),
        encoding="utf-8",
    )

    model = load_semantic_model_from_file(semantic_path)

    assert model.form_meta.document_number == "2017070007"
