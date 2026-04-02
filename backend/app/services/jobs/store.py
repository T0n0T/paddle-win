from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.models.api import JobStage, JobStatus


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    status: str
    current_stage: str
    created_at: datetime


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    def create_job(self, filename: str) -> JobRecord:
        _ = filename
        record = JobRecord(
            job_id=f"job_{uuid4().hex[:12]}",
            status=JobStatus.QUEUED.value,
            current_stage=JobStage.INGEST.value,
            created_at=datetime.now(timezone.utc),
        )
        self._jobs[record.job_id] = record
        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)
