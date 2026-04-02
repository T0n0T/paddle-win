from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

from app.models.formily import FormilySchemaNode
from app.models.semantic import ConfidenceScore, ContractModel


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobStage(str, Enum):
    INGEST = "ingest"
    OCR_TABLE = "ocr_table"
    NORMALIZE_LAYOUT = "normalize_layout"
    SEMANTIC_ENRICH = "semantic_enrich"
    VALIDATE_SCHEMA_INTENT = "validate_schema_intent"
    COMPILE_FORMILY = "compile_formily"
    PERSIST_RESULT = "persist_result"


class ApiError(ContractModel):
    code: StrictStr
    message: StrictStr
    retriable: StrictBool


class ApiErrorResponse(ContractModel):
    error: ApiError


class JobWarning(ContractModel):
    code: StrictStr
    message: StrictStr


class CreateJobResponse(ContractModel):
    job_id: StrictStr
    status: Literal[JobStatus.QUEUED]
    current_stage: Literal[JobStage.INGEST]
    created_at: StrictStr

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("created_at must be an ISO 8601 timestamp") from exc
        return value


class JobStatusResponse(ContractModel):
    job_id: StrictStr
    status: JobStatus
    current_stage: JobStage
    elapsed_ms: StrictInt | None = None
    warnings: list[JobWarning] | None = None
    error: ApiError | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_error_field_presence(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        status = data.get("status")
        if status != JobStatus.FAILED and "error" in data:
            raise ValueError("only failed job responses may include an error payload")
        return data

    @model_validator(mode="after")
    def validate_failed_shape(self) -> "JobStatusResponse":
        if self.status == JobStatus.FAILED and self.error is None:
            raise ValueError("failed job responses require an error payload")
        return self


class ResultResponse(ContractModel):
    job_id: StrictStr
    status: JobStatus
    overall_confidence: ConfidenceScore
    schema_: FormilySchemaNode = Field(alias="schema")
    warnings: list[JobWarning]

    @model_validator(mode="after")
    def validate_result_status(self) -> "ResultResponse":
        if self.status != JobStatus.SUCCEEDED:
            raise ValueError("result responses require succeeded status")
        return self


class ArtifactPaths(ContractModel):
    source_image: StrictStr
    ocr_json: StrictStr
    layout_skeleton: StrictStr
    semantic_form_model: StrictStr
    formily_schema: StrictStr


class PromptVersions(ContractModel):
    semantic_enrich: StrictStr
    validate_schema_intent: StrictStr


class ArtifactsResponse(ContractModel):
    job_id: StrictStr
    artifacts: ArtifactPaths
    prompt_versions: PromptVersions
    warnings: list[JobWarning]
