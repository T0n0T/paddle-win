from datetime import datetime
from pathlib import Path

import pytest

from app.models.api import JobStage, JobStatus
from app.services.jobs.artifacts import DEFAULT_ARTIFACT_ROOT, JobArtifacts
from app.services.jobs.store import JobStore


def test_create_job_starts_queued_from_uploaded_filename():
    store = JobStore()

    record = store.create_job(filename="sample.jpg")

    assert record.job_id
    assert record.status == JobStatus.QUEUED.value
    assert record.current_stage == JobStage.INGEST.value
    assert isinstance(record.created_at, datetime)
    assert store.get_job(record.job_id) == record


def test_job_artifacts_default_to_backend_data_jobs_root():
    artifacts = JobArtifacts.for_job("job_123")

    assert artifacts.root == DEFAULT_ARTIFACT_ROOT
    assert artifacts.job_dir == DEFAULT_ARTIFACT_ROOT / "job_123"
    assert artifacts.job_dir.parts[-3:] == ("data", "jobs", "job_123")
    assert artifacts.source_image_path == DEFAULT_ARTIFACT_ROOT / "job_123" / "source.jpg"
    assert artifacts.ocr_json_path == DEFAULT_ARTIFACT_ROOT / "job_123" / "ocr.json"
    assert artifacts.layout_json_path == DEFAULT_ARTIFACT_ROOT / "job_123" / "layout.json"
    assert artifacts.semantic_json_path == DEFAULT_ARTIFACT_ROOT / "job_123" / "semantic.json"
    assert artifacts.schema_json_path == DEFAULT_ARTIFACT_ROOT / "job_123" / "schema.json"


def test_job_artifacts_write_named_files_under_backend_jobs_shape(tmp_path: Path):
    artifacts = JobArtifacts.for_job("job_123", root=tmp_path / "backend" / "data" / "jobs")

    source_path = artifacts.write_source_image(b"binary-image")
    ocr_path = artifacts.write_ocr_json({"boxes": []})
    layout_path = artifacts.write_layout_json({"tables": []})
    semantic_path = artifacts.write_semantic_json({"fields": []})
    schema_path = artifacts.write_schema_json({"schema": {}})

    assert source_path.read_bytes() == b"binary-image"
    assert ocr_path.read_text(encoding="utf-8").strip() == '{\n  "boxes": []\n}'
    assert layout_path.read_text(encoding="utf-8").strip() == '{\n  "tables": []\n}'
    assert semantic_path.read_text(encoding="utf-8").strip() == '{\n  "fields": []\n}'
    assert schema_path.read_text(encoding="utf-8").strip() == '{\n  "schema": {}\n}'


def test_job_artifacts_reject_path_traversal_job_ids():
    with pytest.raises(ValueError, match="single relative path segment"):
        JobArtifacts.for_job("../escape")


def test_job_artifacts_reject_absolute_job_ids():
    with pytest.raises(ValueError, match="single relative path segment"):
        JobArtifacts.for_job("/tmp/escape")
