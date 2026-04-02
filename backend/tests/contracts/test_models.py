from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings
from app.models.api import (
    ApiError,
    ApiErrorResponse,
    ArtifactPaths,
    ArtifactsResponse,
    CreateJobResponse,
    JobStage,
    JobStatus,
    JobStatusResponse,
    JobWarning,
    PromptVersions,
    ResultResponse,
)
from app.models.formily import (
    FormilySchemaEnvelope,
    FormilySchemaNode,
    FormilyXData,
)
from app.models.semantic import (
    EvidenceRef,
    FormMeta,
    LayoutHints,
    SemanticField,
    SemanticFormModel,
    SemanticSection,
    SemanticWarning,
    TableColumnSpec,
)


def test_array_table_field_requires_column_metadata():
    field = SemanticField(
        key="work_items_table",
        title="工作任务",
        kind="array-table",
        section_key="work_items",
        field_role="table",
        table_columns=[
            TableColumnSpec(key="work_content", title="工作内容", kind="string", order=1),
        ],
        value=[{"work_content": "安装关口表"}],
        confidence=0.93,
        evidence=[],
    )
    assert field.table_columns[0].title == "工作内容"


def test_array_table_field_rejects_missing_column_metadata():
    with pytest.raises(ValidationError):
        SemanticField(
            key="work_items_table",
            title="工作任务",
            kind="array-table",
            section_key="work_items",
            field_role="table",
            value=[{"work_content": "安装关口表"}],
            confidence=0.93,
            evidence=[],
        )


def test_boolean_field_rejects_string_value():
    with pytest.raises(ValidationError, match="boolean fields require a boolean value"):
        SemanticField(
            key="requires_outage",
            title="是否停电",
            kind="boolean",
            section_key="safety",
            field_role="checkbox",
            value="true",
            confidence=0.91,
            evidence=[],
        )


def test_boolean_field_rejects_integer_coercion():
    with pytest.raises(ValidationError):
        SemanticField(
            key="requires_outage",
            title="是否停电",
            kind="boolean",
            section_key="safety",
            field_role="checkbox",
            value=1,
            confidence=0.91,
            evidence=[],
        )


def test_array_table_field_rejects_scalar_value():
    with pytest.raises(ValidationError, match="array-table fields require a list value"):
        SemanticField(
            key="work_items_table",
            title="工作任务",
            kind="array-table",
            section_key="work_items",
            field_role="table",
            table_columns=[
                TableColumnSpec(key="work_content", title="工作内容", kind="string", order=1),
            ],
            value="安装关口表",
            confidence=0.93,
            evidence=[],
        )


def test_evidence_ref_rejects_string_page_number():
    with pytest.raises(ValidationError):
        EvidenceRef(
            source_id="box_12",
            source_type="text_box",
            bbox=[120.0, 88.0, 210.0, 114.0],
            page="2",
        )


def test_evidence_ref_rejects_non_rectangular_bbox():
    with pytest.raises(ValidationError, match="bbox must contain exactly 4 coordinates"):
        EvidenceRef(
            source_id="box_12",
            source_type="text_box",
            bbox=[120.0, 88.0, 210.0],
        )


def test_evidence_ref_rejects_string_bbox_coordinates():
    with pytest.raises(ValidationError):
        EvidenceRef(
            source_id="box_12",
            source_type="text_box",
            bbox=["120.0", "88.0", "210.0", "114.0"],
        )


def test_semantic_form_model_serializes_strict_contract():
    model = SemanticFormModel(
        form_meta=FormMeta(
            title="配电第一种工作票",
            document_type="电力工作票",
            document_number="2017070007",
        ),
        sections=[
            SemanticSection(
                key="basic_info",
                title="基本信息",
                field_keys=["work_leader"],
                order=1,
                section_type="basic",
            )
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
            )
        ],
        layout_hints=LayoutHints(
            section_order=["basic_info"],
            preferred_columns={"basic_info": 2},
            section_spans={"basic_info": "full"},
        ),
        warnings=[
            SemanticWarning(
                code="layout_approximation",
                message="表头布局经过近似归一化。",
                severity="low",
                related_field_keys=["work_leader"],
            )
        ],
    )

    dumped = model.model_dump()

    assert dumped["fields"][0]["evidence"][0]["page"] == 1
    assert dumped["warnings"][0]["related_field_keys"] == ["work_leader"]


def test_semantic_form_model_rejects_field_with_unknown_section():
    with pytest.raises(ValidationError, match="references unknown section"):
        SemanticFormModel(
            form_meta=FormMeta(title="配电第一种工作票"),
            sections=[
                SemanticSection(
                    key="basic_info",
                    title="基本信息",
                    field_keys=["work_leader"],
                    order=1,
                    section_type="basic",
                )
            ],
            fields=[
                SemanticField(
                    key="work_leader",
                    title="工作负责人",
                    kind="string",
                    section_key="missing_section",
                    field_role="person_name",
                    value="闫丽亚",
                    confidence=0.98,
                    evidence=[],
                )
            ],
            layout_hints=LayoutHints(
                section_order=["basic_info"],
                preferred_columns={"basic_info": 2},
                section_spans={"basic_info": "full"},
            ),
        )


def test_semantic_form_model_rejects_duplicate_section_keys():
    with pytest.raises(ValidationError, match="sections must use unique keys"):
        SemanticFormModel(
            form_meta=FormMeta(title="配电第一种工作票"),
            sections=[
                SemanticSection(
                    key="basic_info",
                    title="基本信息一",
                    field_keys=[],
                    order=1,
                    section_type="basic",
                ),
                SemanticSection(
                    key="basic_info",
                    title="基本信息二",
                    field_keys=[],
                    order=2,
                    section_type="group",
                ),
            ],
            fields=[],
            layout_hints=LayoutHints(section_order=[], preferred_columns={}, section_spans={}),
        )


def test_semantic_form_model_rejects_duplicate_field_keys():
    with pytest.raises(ValidationError, match="fields must use unique keys"):
        SemanticFormModel(
            form_meta=FormMeta(title="配电第一种工作票"),
            sections=[
                SemanticSection(
                    key="basic_info",
                    title="基本信息",
                    field_keys=["work_leader"],
                    order=1,
                    section_type="basic",
                )
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
                    evidence=[],
                ),
                SemanticField(
                    key="work_leader",
                    title="工作负责人副本",
                    kind="string",
                    section_key="basic_info",
                    field_role="person_name",
                    value="张三",
                    confidence=0.92,
                    evidence=[],
                ),
            ],
            layout_hints=LayoutHints(
                section_order=["basic_info"],
                preferred_columns={"basic_info": 2},
                section_spans={"basic_info": "full"},
            ),
        )


def test_semantic_form_model_rejects_section_with_unknown_field_reference():
    with pytest.raises(ValidationError, match="references unknown field"):
        SemanticFormModel(
            form_meta=FormMeta(title="配电第一种工作票"),
            sections=[
                SemanticSection(
                    key="basic_info",
                    title="基本信息",
                    field_keys=["missing_field"],
                    order=1,
                    section_type="basic",
                )
            ],
            fields=[],
            layout_hints=LayoutHints(
                section_order=["basic_info"],
                preferred_columns={"basic_info": 2},
                section_spans={"basic_info": "full"},
            ),
        )


def test_semantic_form_model_rejects_section_field_owned_by_other_section():
    with pytest.raises(ValidationError, match="references field work_leader owned by extra_info"):
        SemanticFormModel(
            form_meta=FormMeta(title="配电第一种工作票"),
            sections=[
                SemanticSection(
                    key="basic_info",
                    title="基本信息",
                    field_keys=["work_leader"],
                    order=1,
                    section_type="basic",
                ),
                SemanticSection(
                    key="extra_info",
                    title="补充信息",
                    field_keys=[],
                    order=2,
                    section_type="group",
                ),
            ],
            fields=[
                SemanticField(
                    key="work_leader",
                    title="工作负责人",
                    kind="string",
                    section_key="extra_info",
                    field_role="person_name",
                    value="闫丽亚",
                    confidence=0.98,
                    evidence=[],
                )
            ],
            layout_hints=LayoutHints(
                section_order=["basic_info", "extra_info"],
                preferred_columns={"basic_info": 2, "extra_info": 1},
                section_spans={"basic_info": "full", "extra_info": "left"},
            ),
        )


def test_semantic_form_model_rejects_layout_hints_with_unknown_section():
    with pytest.raises(ValidationError, match="layout_hints references unknown sections"):
        SemanticFormModel(
            form_meta=FormMeta(title="配电第一种工作票"),
            sections=[
                SemanticSection(
                    key="basic_info",
                    title="基本信息",
                    field_keys=[],
                    order=1,
                    section_type="basic",
                )
            ],
            fields=[],
            layout_hints=LayoutHints(
                section_order=["basic_info", "missing_section"],
                preferred_columns={"basic_info": 2},
                section_spans={"basic_info": "full"},
            ),
        )


def test_formily_envelope_preserves_field_warnings_in_x_data():
    envelope = FormilySchemaEnvelope(
        schema=FormilySchemaNode(
            type="object",
            properties={
                "basic_info": FormilySchemaNode(
                    type="void",
                    x_component="FormGrid",
                    properties={
                        "work_leader": FormilySchemaNode(
                            type="string",
                            title="工作负责人",
                            x_decorator="FormItem",
                            x_component="Input",
                            default="闫丽亚",
                            x_data=FormilyXData(
                                confidence=0.98,
                                source_boxes=["box_12"],
                                section_key="basic_info",
                                field_role="person_name",
                                warnings=["low_contrast"],
                            ),
                        )
                    },
                )
            },
        )
    )

    dumped = envelope.model_dump(by_alias=True)

    assert dumped["schema"]["properties"]["basic_info"]["properties"]["work_leader"]["x-data"][
        "warnings"
    ] == ["low_contrast"]


def test_result_response_keeps_top_level_job_warnings_separate():
    response = ResultResponse(
        job_id="job_123",
        status=JobStatus.SUCCEEDED,
        overall_confidence=0.91,
        schema=FormilySchemaNode(
            type="object",
            properties={
                "basic_info": FormilySchemaNode(
                    type="void",
                    properties={
                        "work_leader": FormilySchemaNode(
                            type="string",
                            x_data=FormilyXData(
                                confidence=0.98,
                                source_boxes=["box_12"],
                                section_key="basic_info",
                                field_role="person_name",
                                warnings=["field_warning"],
                            ),
                        )
                    },
                )
            },
        ),
        warnings=[{"code": "job_warning", "message": "One checkbox candidate remains uncertain."}],
    )

    dumped = response.model_dump(by_alias=True)

    assert dumped["warnings"] == [
        {"code": "job_warning", "message": "One checkbox candidate remains uncertain."}
    ]
    assert (
        dumped["schema"]["properties"]["basic_info"]["properties"]["work_leader"]["x-data"][
            "warnings"
        ]
        == ["field_warning"]
    )


def test_error_response_wraps_api_error_payload_exactly():
    response = ApiErrorResponse(
        error=ApiError(
            code="unsupported_media_type",
            message="Only JPEG, PNG, and WEBP are accepted in the MVP.",
            retriable=False,
        )
    )

    assert response.model_dump() == {
        "error": {
            "code": "unsupported_media_type",
            "message": "Only JPEG, PNG, and WEBP are accepted in the MVP.",
            "retriable": False,
        }
    }


def test_job_status_response_rejects_error_payload_for_non_failed_status():
    with pytest.raises(ValidationError, match="only failed job responses may include an error payload"):
        JobStatusResponse(
            job_id="job_123",
            status=JobStatus.RUNNING,
            current_stage=JobStage.SEMANTIC_ENRICH,
            error=ApiError(
                code="semantic_output_invalid",
                message="Model output failed structured validation after retry.",
                retriable=True,
            ),
        )


def test_job_status_response_rejects_explicit_null_error_for_non_failed_status():
    with pytest.raises(ValidationError, match="only failed job responses may include an error payload"):
        JobStatusResponse.model_validate(
            {
                "job_id": "job_123",
                "status": "running",
                "current_stage": "semantic_enrich",
                "error": None,
            }
        )


def test_job_status_response_requires_error_payload_for_failed_status():
    with pytest.raises(ValidationError, match="failed job responses require an error payload"):
        JobStatusResponse(
            job_id="job_123",
            status=JobStatus.FAILED,
            current_stage=JobStage.SEMANTIC_ENRICH,
        )


def test_job_status_response_rejects_string_elapsed_ms():
    with pytest.raises(ValidationError):
        JobStatusResponse(
            job_id="job_123",
            status=JobStatus.RUNNING,
            current_stage=JobStage.SEMANTIC_ENRICH,
            elapsed_ms="5231",
        )


def test_create_job_response_rejects_non_initial_status():
    with pytest.raises(ValidationError):
        CreateJobResponse(
            job_id="job_123",
            status=JobStatus.RUNNING,
            current_stage=JobStage.INGEST,
            created_at="2026-04-02T20:10:00+08:00",
        )


def test_create_job_response_rejects_non_initial_stage():
    with pytest.raises(ValidationError):
        CreateJobResponse(
            job_id="job_123",
            status=JobStatus.QUEUED,
            current_stage=JobStage.SEMANTIC_ENRICH,
            created_at="2026-04-02T20:10:00+08:00",
        )


def test_create_job_response_rejects_invalid_timestamp_shape():
    with pytest.raises(ValidationError):
        CreateJobResponse(
            job_id="job_123",
            status=JobStatus.QUEUED,
            current_stage=JobStage.INGEST,
            created_at="04/02/2026 20:10:00",
        )


def test_result_response_requires_top_level_warnings():
    with pytest.raises(ValidationError):
        ResultResponse(
            job_id="job_123",
            status=JobStatus.SUCCEEDED,
            overall_confidence=0.91,
            schema=FormilySchemaNode(type="object", properties={}),
        )


def test_result_response_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        ResultResponse(
            job_id="job_123",
            status=JobStatus.SUCCEEDED,
            overall_confidence=1.2,
            schema=FormilySchemaNode(type="object", properties={}),
            warnings=[],
        )


def test_formily_string_node_rejects_array_default():
    with pytest.raises(ValidationError, match="string schema nodes require a string default"):
        FormilySchemaNode(type="string", default=[{"a": 1}])


def test_formily_array_node_requires_items():
    with pytest.raises(ValidationError, match="array schema nodes require items"):
        FormilySchemaNode(type="array")


def test_formily_array_node_rejects_properties():
    with pytest.raises(ValidationError, match="array schema nodes do not support properties"):
        FormilySchemaNode(
            type="array",
            items=FormilySchemaNode(type="object", properties={}),
            properties={},
        )


def test_formily_array_node_rejects_default_items_that_do_not_match_item_schema():
    with pytest.raises(ValidationError, match="default items must match the items schema"):
        FormilySchemaNode(
            type="array",
            items=FormilySchemaNode(type="boolean"),
            default=[{"unexpected": "dict"}],
        )


def test_formily_object_node_requires_properties():
    with pytest.raises(ValidationError, match="object schema nodes require properties"):
        FormilySchemaNode(type="object")


def test_formily_x_data_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        FormilyXData(
            confidence=-0.1,
            source_boxes=["box_12"],
            section_key="basic_info",
            field_role="person_name",
        )


def test_artifacts_response_requires_top_level_warnings():
    with pytest.raises(ValidationError):
        ArtifactsResponse(
            job_id="job_123",
            artifacts=ArtifactPaths(
                source_image="/artifacts/job_123/source.jpg",
                ocr_json="/artifacts/job_123/ocr.json",
                layout_skeleton="/artifacts/job_123/layout.json",
                semantic_form_model="/artifacts/job_123/semantic.json",
                formily_schema="/artifacts/job_123/schema.json",
            ),
            prompt_versions=PromptVersions(
                semantic_enrich="sem_v1_draft",
                validate_schema_intent="val_v1",
            ),
        )


def test_api_response_models_capture_exact_contract_shapes():
    create_job = CreateJobResponse(
        job_id="job_123",
        status=JobStatus.QUEUED,
        current_stage=JobStage.INGEST,
        created_at="2026-04-02T20:10:00+08:00",
    )
    job_status = JobStatusResponse(
        job_id="job_123",
        status=JobStatus.RUNNING,
        current_stage=JobStage.SEMANTIC_ENRICH,
        elapsed_ms=5231,
        warnings=[JobWarning(code="low_confidence_checkbox", message="One checkbox candidate remains uncertain.")],
    )
    failed_status = JobStatusResponse(
        job_id="job_123",
        status=JobStatus.FAILED,
        current_stage=JobStage.SEMANTIC_ENRICH,
        error=ApiError(
            code="semantic_output_invalid",
            message="Model output failed structured validation after retry.",
            retriable=True,
        ),
    )
    result = ResultResponse(
        job_id="job_123",
        status=JobStatus.SUCCEEDED,
        overall_confidence=0.91,
        schema=FormilySchemaNode(type="object", properties={}),
        warnings=[],
    )
    artifacts = ArtifactsResponse(
        job_id="job_123",
        artifacts=ArtifactPaths(
            source_image="/artifacts/job_123/source.jpg",
            ocr_json="/artifacts/job_123/ocr.json",
            layout_skeleton="/artifacts/job_123/layout.json",
            semantic_form_model="/artifacts/job_123/semantic.json",
            formily_schema="/artifacts/job_123/schema.json",
        ),
        prompt_versions=PromptVersions(
            semantic_enrich="sem_v1_draft",
            validate_schema_intent="val_v1",
        ),
        warnings=[],
    )

    assert create_job.model_dump() == {
        "job_id": "job_123",
        "status": "queued",
        "current_stage": "ingest",
        "created_at": "2026-04-02T20:10:00+08:00",
    }
    assert job_status.model_dump() == {
        "job_id": "job_123",
        "status": "running",
        "current_stage": "semantic_enrich",
        "elapsed_ms": 5231,
        "warnings": [
            {
                "code": "low_confidence_checkbox",
                "message": "One checkbox candidate remains uncertain.",
            }
        ],
    }
    assert failed_status.model_dump() == {
        "job_id": "job_123",
        "status": "failed",
        "current_stage": "semantic_enrich",
        "error": {
            "code": "semantic_output_invalid",
            "message": "Model output failed structured validation after retry.",
            "retriable": True,
        },
    }
    assert ApiErrorResponse(error=failed_status.error).model_dump() == {
        "error": {
            "code": "semantic_output_invalid",
            "message": "Model output failed structured validation after retry.",
            "retriable": True,
        }
    }
    assert result.model_dump(by_alias=True)["overall_confidence"] == 0.91
    assert artifacts.model_dump() == {
        "job_id": "job_123",
        "artifacts": {
            "source_image": "/artifacts/job_123/source.jpg",
            "ocr_json": "/artifacts/job_123/ocr.json",
            "layout_skeleton": "/artifacts/job_123/layout.json",
            "semantic_form_model": "/artifacts/job_123/semantic.json",
            "formily_schema": "/artifacts/job_123/schema.json",
        },
        "prompt_versions": {
            "semantic_enrich": "sem_v1_draft",
            "validate_schema_intent": "val_v1",
        },
        "warnings": [],
    }


def test_settings_load_expected_environment_fields(tmp_path: Path):
    artifact_root = tmp_path / "artifacts"
    settings = Settings(
        OPENAI_API_KEY="test-key",
        OPENAI_MODEL="gpt-4.1-mini",
        ARTIFACT_ROOT=artifact_root,
        ENABLE_DEV_ARTIFACTS=True,
    )

    assert settings.OPENAI_API_KEY == "test-key"
    assert settings.OPENAI_MODEL == "gpt-4.1-mini"
    assert settings.ARTIFACT_ROOT == artifact_root
    assert settings.ENABLE_DEV_ARTIFACTS is True


def test_settings_load_backend_env_file_from_project_root_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir(parents=True)
    env_file = backend_dir / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=env-test-key",
                "OPENAI_MODEL=gpt-4.1-mini",
                f"ARTIFACT_ROOT={backend_dir / 'artifacts'}",
                "ENABLE_DEV_ARTIFACTS=true",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    TempSettings = type(
        "TempSettings",
        (Settings,),
        {
            "model_config": SettingsConfigDict(
                env_file=env_file,
                env_file_encoding="utf-8",
                extra="ignore",
                case_sensitive=True,
            )
        },
    )

    settings = TempSettings()

    assert settings.OPENAI_API_KEY == "env-test-key"
    assert settings.OPENAI_MODEL == "gpt-4.1-mini"
    assert settings.ARTIFACT_ROOT == backend_dir / "artifacts"
    assert settings.ENABLE_DEV_ARTIFACTS is True
