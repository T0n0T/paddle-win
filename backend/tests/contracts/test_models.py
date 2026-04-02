from pathlib import Path

import pytest
from pydantic import ValidationError

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
