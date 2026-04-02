# Zero-Shot Chinese Form Recognition MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MVP that accepts one semi-structured Chinese form image, runs PaddleOCR official General Table Recognition V2 plus OpenAI multimodal semantic enrichment through LangGraph and LangChain, and returns a directly consumable `@formily/antd-v5` Formily Schema through a FastAPI and Next.js workflow.

**Architecture:** The backend owns typed contracts, local artifact persistence, OCR and LLM adapters, LangGraph orchestration, and deterministic Formily compilation. The frontend is a thin Next.js operator console that creates async jobs, polls stage updates, previews raw schema, and renders a basic Formily preview. Prompt drafting is an explicit checkpoint: prompt files must be shown to the user before they are wired into the live graph.

**Tech Stack:** FastAPI, Pydantic v2, LangGraph, LangChain, OpenAI SDK, PaddleOCR/PaddleX `table_recognition_v2`, pytest, Next.js 16, React 19, `@formily/core`, `@formily/react`, `@formily/antd-v5`, `antd`, `dayjs`, Vitest, Testing Library

---

## References

- Spec: `docs/superpowers/specs/2026-04-02-zero-shot-chinese-form-recognition-design.md`
- Backend entrypoint today: `backend/main.py`
- Frontend entrypoint today: `frontend/app/page.tsx`
- Check official docs before implementation:
  - PaddleOCR General Table Recognition V2
  - LangGraph install and graph API
  - LangChain ChatOpenAI structured output
  - Formily `@formily/antd-v5` `ArrayTable` and `FormGrid`
  - `frontend/AGENTS.md` note about Next.js 16 breaking changes

## Planned File Structure

### Backend

- Modify: `backend/pyproject.toml`
- Modify: `backend/.python-version`
- Modify: `backend/main.py`
- Modify: `backend/README.md`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/models/api.py`
- Create: `backend/app/models/semantic.py`
- Create: `backend/app/models/formily.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/api/routes/jobs.py`
- Create: `backend/app/services/jobs/store.py`
- Create: `backend/app/services/jobs/artifacts.py`
- Create: `backend/app/services/ocr/paddle_table_v2.py`
- Create: `backend/app/services/ocr/layout_normalizer.py`
- Create: `backend/app/services/llm/prompts/semantic_enrich.md`
- Create: `backend/app/services/llm/prompts/semantic_validate.md`
- Create: `backend/app/services/llm/openai_client.py`
- Create: `backend/app/services/llm/semantic_enricher.py`
- Create: `backend/app/services/compiler/validator.py`
- Create: `backend/app/services/compiler/formily_compiler.py`
- Create: `backend/app/workflows/state.py`
- Create: `backend/app/workflows/recognition_graph.py`
- Create: `backend/app/workflows/runner.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_app_smoke.py`
- Create: `backend/tests/contracts/test_models.py`
- Create: `backend/tests/services/test_job_store.py`
- Create: `backend/tests/services/test_layout_normalizer.py`
- Create: `backend/tests/services/test_semantic_enricher.py`
- Create: `backend/tests/services/test_formily_compiler.py`
- Create: `backend/tests/workflows/test_recognition_graph.py`
- Create: `backend/tests/api/test_jobs_api.py`
- Create: `backend/tests/fixtures/forms/work-ticket.jpg`
- Create: `backend/tests/fixtures/ocr/work-ticket-table-v2.json`

### Frontend

- Modify: `frontend/package.json`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/README.md`
- Create: `frontend/.env.example`
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/formily.ts`
- Create: `frontend/components/recognition-console.tsx`
- Create: `frontend/components/upload-panel.tsx`
- Create: `frontend/components/job-status-panel.tsx`
- Create: `frontend/components/schema-preview.tsx`
- Create: `frontend/components/form-preview.tsx`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/components/__tests__/recognition-console.test.tsx`

### Docs

- Create: `docs/superpowers/plans/2026-04-02-zero-shot-chinese-form-recognition-mvp.md`

## Execution Notes

- Use `@superpowers:test-driven-development` discipline for each task.
- Keep commits small and task-scoped.
- Do not wire prompts into the live semantic graph until the user reviews the prompt files.
- Keep artifact persistence local and simple for the MVP.
- Do not add a built-in correction UI.

### Task 1: Establish Backend Runtime Baseline

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/.python-version`
- Modify: `backend/main.py`
- Modify: `backend/README.md`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/routes/health.py`
- Test: `backend/tests/test_app_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_healthz_returns_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `uv run --project backend pytest backend/tests/test_app_smoke.py -v`  
Expected: FAIL because `app.main` and FastAPI dependencies do not exist yet.

- [ ] **Step 3: Write the minimal runtime baseline**

```python
from fastapi import FastAPI

from app.api.routes.health import router as health_router

app = FastAPI(title="Paddle Win API")
app.include_router(health_router)
```

Also make these runtime choices in `backend/pyproject.toml`:

- set `requires-python = ">=3.11,<3.13"`
- add `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `httpx`, `pytest`, `python-multipart`, `pillow`, `openai`, `langchain`, `langgraph`, `paddlex`
- make `backend/main.py` a thin compatibility entrypoint that imports `app` from `app.main` so both `uv run --project backend uvicorn app.main:app --reload` and legacy module references stay clear

Add a quick import smoke test to `backend/tests/test_app_smoke.py` that imports `openai`, `langchain`, `langgraph`, and the PaddleOCR wrapper module so missing runtime dependencies fail early.

- [ ] **Step 4: Run backend tests again**

Run: `uv run --project backend pytest backend/tests/test_app_smoke.py -v`  
Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/.python-version backend/main.py backend/README.md backend/.env.example backend/app/__init__.py backend/app/main.py backend/app/api/routes/health.py backend/tests/test_app_smoke.py
git commit -m "feat: bootstrap backend fastapi app"
```

### Task 2: Lock API and Semantic Contracts

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/models/api.py`
- Create: `backend/app/models/semantic.py`
- Create: `backend/app/models/formily.py`
- Test: `backend/tests/contracts/test_models.py`

- [ ] **Step 1: Write failing contract tests**

```python
from app.models.semantic import SemanticField, TableColumnSpec


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
```

- [ ] **Step 2: Run the contract tests to verify they fail**

Run: `uv run --project backend pytest backend/tests/contracts/test_models.py -v`  
Expected: FAIL because the contract models do not exist.

- [ ] **Step 3: Implement typed models and config**

```python
class TableColumnSpec(BaseModel):
    key: str
    title: str
    kind: Literal["string", "datetime", "textarea", "boolean"] = "string"
    order: int
    required: bool = False
```

Capture these contracts:

- job status responses
- artifact response shapes
- `SemanticFormModel`
- `FormilySchemaEnvelope`
- settings for `OPENAI_API_KEY`, `OPENAI_MODEL`, `ARTIFACT_ROOT`, `ENABLE_DEV_ARTIFACTS`
- artifact payload fields for `prompt_versions`
- top-level job warnings vs per-field `x-data.warnings`
- exact response fields for:
  - `POST /api/jobs`
  - `GET /api/jobs/{job_id}`
  - `GET /api/jobs/{job_id}/result`
  - `GET /api/jobs/{job_id}/artifacts`

- [ ] **Step 4: Run the contract tests**

Run: `uv run --project backend pytest backend/tests/contracts/test_models.py -v`  
Expected: PASS with model serialization and validation working.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/models/api.py backend/app/models/semantic.py backend/app/models/formily.py backend/tests/contracts/test_models.py
git commit -m "feat: add recognition contracts"
```

### Task 3: Add Local Job Store and Artifact Persistence

**Files:**
- Create: `backend/app/services/jobs/store.py`
- Create: `backend/app/services/jobs/artifacts.py`
- Test: `backend/tests/services/test_job_store.py`

- [ ] **Step 1: Write failing storage tests**

```python
def test_create_job_starts_queued(tmp_path):
    store = JobStore()
    job = store.create_job(filename="sample.jpg")
    assert job.status == "queued"
```

- [ ] **Step 2: Run the storage tests to verify they fail**

Run: `uv run --project backend pytest backend/tests/services/test_job_store.py -v`  
Expected: FAIL because `JobStore` and artifact helpers do not exist.

- [ ] **Step 3: Implement local storage**

```python
@dataclass
class JobRecord:
    job_id: str
    status: str
    current_stage: str
    created_at: datetime
```

Implementation rules:

- use in-process store for MVP
- persist artifacts under `backend/data/jobs/<job_id>/`
- expose helpers for writing `source.jpg`, `ocr.json`, `layout.json`, `semantic.json`, `schema.json`

- [ ] **Step 4: Run storage tests**

Run: `uv run --project backend pytest backend/tests/services/test_job_store.py -v`  
Expected: PASS with job creation and artifact path generation working.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/jobs/store.py backend/app/services/jobs/artifacts.py backend/tests/services/test_job_store.py
git commit -m "feat: add job store and artifact persistence"
```

### Task 4: Wrap PaddleOCR and Normalize Layout Skeletons

**Files:**
- Create: `backend/app/services/ocr/paddle_table_v2.py`
- Create: `backend/app/services/ocr/layout_normalizer.py`
- Create: `backend/tests/fixtures/forms/work-ticket.jpg`
- Create: `backend/tests/fixtures/ocr/work-ticket-table-v2.json`
- Test: `backend/tests/services/test_layout_normalizer.py`

- [ ] **Step 1: Write failing normalization tests**

```python
def test_normalize_table_v2_output_builds_layout_skeleton(sample_table_v2_payload):
    skeleton = normalize_layout(sample_table_v2_payload)
    assert skeleton.page_count == 1
    assert skeleton.tables[0].table_id == "table_1"
```

- [ ] **Step 2: Run normalization tests to verify they fail**

Run: `uv run --project backend pytest backend/tests/services/test_layout_normalizer.py -v`  
Expected: FAIL because the adapter and normalizer are missing.

- [ ] **Step 3: Implement the adapter boundary**

```python
class PaddleTableV2Client:
    def run(self, image_path: Path) -> dict:
        """Call PaddleOCR official table_recognition_v2 pipeline and return raw JSON."""
```

Implementation rules:

- the only supported OCR entrypoint is official `table_recognition_v2` / `TableRecognitionPipelineV2`
- keep the runner wrapper thin
- normalize raw output into deterministic IDs for boxes, tables, cells, and candidate checkbox regions
- candidate checkbox and underline-fill regions are best-effort for the MVP, but deterministic IDs are still required when they are emitted

- [ ] **Step 4: Run normalization tests**

Run: `uv run --project backend pytest backend/tests/services/test_layout_normalizer.py -v`  
Expected: PASS with deterministic layout skeleton output.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ocr/paddle_table_v2.py backend/app/services/ocr/layout_normalizer.py backend/tests/fixtures/forms/work-ticket.jpg backend/tests/fixtures/ocr/work-ticket-table-v2.json backend/tests/services/test_layout_normalizer.py
git commit -m "feat: add paddle table v2 normalization"
```

### Task 5: Draft Semantic Prompt Files and Review Harness

**Files:**
- Create: `backend/app/services/llm/prompts/semantic_enrich.md`
- Create: `backend/app/services/llm/prompts/semantic_validate.md`
- Create: `backend/app/services/llm/openai_client.py`
- Create: `backend/app/services/llm/semantic_enricher.py`
- Test: `backend/tests/services/test_semantic_enricher.py`

- [ ] **Step 1: Write failing semantic-enrichment tests**

```python
def test_build_semantic_prompt_includes_layout_contract(sample_layout_skeleton):
    request = build_semantic_request(sample_layout_skeleton, image_path="tests/fixtures/forms/work-ticket.jpg")
    assert "SemanticFormModel" in request.instructions
    assert "table_columns" in request.instructions
```

- [ ] **Step 2: Run the semantic-enrichment tests to verify they fail**

Run: `uv run --project backend pytest backend/tests/services/test_semantic_enricher.py -v`  
Expected: FAIL because prompt files and the enricher do not exist.

- [ ] **Step 3: Implement the draft prompt layer and request builder**

```python
def build_semantic_request(layout: LayoutSkeleton, image_path: str) -> SemanticPromptRequest:
    prompt = prompt_loader("semantic_enrich.md")
    return SemanticPromptRequest(system_prompt=prompt, image_path=image_path, layout_json=layout.model_dump())
```

Implementation rules:

- prompt files live on disk, not inline in Python
- `semantic_enrich.md` targets `SemanticFormModel`
- `semantic_validate.md` is reserved for later repair/validation passes
- `openai_client.py` wraps the OpenAI SDK behind a small interface that LangChain can call
- pass multimodal image input from saved artifact path to OpenAI as bytes/base64 through a single request builder
- parse structured outputs through Pydantic validation before graph nodes accept them

- [ ] **Step 4: Pause for user review before graph wiring**

Action: show the contents of `backend/app/services/llm/prompts/semantic_enrich.md` to the user and wait for approval before continuing to Task 6.  
Expected: explicit user approval or requested prompt edits.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm/prompts/semantic_enrich.md backend/app/services/llm/prompts/semantic_validate.md backend/app/services/llm/openai_client.py backend/app/services/llm/semantic_enricher.py backend/tests/services/test_semantic_enricher.py
git commit -m "feat: draft semantic enrichment prompts"
```

### Task 6: Build Semantic Validators and Formily Compiler

**Files:**
- Create: `backend/app/services/compiler/validator.py`
- Create: `backend/app/services/compiler/formily_compiler.py`
- Test: `backend/tests/services/test_formily_compiler.py`

- [ ] **Step 1: Write failing compiler tests**

```python
def test_compile_array_table_uses_table_columns():
    schema = compile_formily(sample_semantic_form_model())
    table = schema["properties"]["work_items"]["properties"]["work_items_table"]
    assert table["x-component"] == "ArrayTable"
    assert "location_or_equipment_column" in table["items"]["properties"]


def test_compile_field_x_data_uses_source_ids_only():
    schema = compile_formily(sample_semantic_form_model())
    field = schema["properties"]["basic_info"]["properties"]["work_leader"]
    assert field["x-data"]["source_boxes"] == ["box_12"]
```

- [ ] **Step 2: Run compiler tests to verify they fail**

Run: `uv run --project backend pytest backend/tests/services/test_formily_compiler.py -v`  
Expected: FAIL because validator and compiler are missing.

- [ ] **Step 3: Implement validation and deterministic compilation**

```python
def compile_formily(model: SemanticFormModel) -> dict:
    validate_semantic_model(model)
    return {"type": "object", "properties": build_sections(model)}
```

Must cover:

- always wrap fields under section `Void` containers
- map `string` to `Input`
- map `textarea` to `Input.TextArea`
- map `boolean` to `Checkbox`
- map `datetime` to `DatePicker` with string defaults and `+08:00` fallback when timezone is missing
- generate `ArrayTable.Column` nodes from `table_columns`, never inferred row keys alone
- enforce the deterministic field key strategy before compilation:
  - semantic role key first
  - then section-prefixed key
  - then deterministic ordinal fallback
  - then deterministic layout-order suffix on collision
- populate field `x-data` with `confidence`, `source_boxes`, `section_key`, `field_role`, `warnings`
- return enough metadata to compute top-level `overall_confidence` as the arithmetic mean of compiled field confidences

- [ ] **Step 4: Run compiler tests**

Run: `uv run --project backend pytest backend/tests/services/test_formily_compiler.py -v`  
Expected: PASS with scalar fields, date defaults, and array tables compiled correctly.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/compiler/validator.py backend/app/services/compiler/formily_compiler.py backend/tests/services/test_formily_compiler.py
git commit -m "feat: add semantic validator and formily compiler"
```

### Task 7: Assemble the LangGraph Recognition Workflow

**Files:**
- Create: `backend/app/workflows/state.py`
- Create: `backend/app/workflows/recognition_graph.py`
- Create: `backend/app/workflows/runner.py`
- Test: `backend/tests/workflows/test_recognition_graph.py`

- [ ] **Step 1: Write failing workflow tests**

```python
def test_semantic_failure_retries_once_then_degrades():
    runner = build_test_runner(semantic_failures=2)
    result = runner.run(sample_job())
    assert result.status == "succeeded"
    assert result.warnings


def test_degraded_schema_keeps_only_high_confidence_scalar_fields():
    result = build_test_runner(semantic_failures=2).run(sample_job())
    assert "basic_info" in result.schema["properties"]
    assert "work_items_table" not in result.schema["properties"].get("work_items", {}).get("properties", {})
```

- [ ] **Step 2: Run workflow tests to verify they fail**

Run: `uv run --project backend pytest backend/tests/workflows/test_recognition_graph.py -v`  
Expected: FAIL because graph state and runner do not exist.

- [ ] **Step 3: Implement `RecognitionState` and graph nodes**

```python
class RecognitionState(TypedDict):
    job_id: str
    image_path: str
    processed_image_path: str | None
    current_stage: str
    retry_count: int
    ocr_result: dict | None
    layout_skeleton: dict | None
    semantic_model: dict | None
    schema: dict | None
    warnings: list[dict]
    prompt_versions: dict[str, str]
    error: dict | None
```

Workflow rules:

- `ingest -> ocr_table -> normalize_layout -> semantic_enrich -> validate_schema_intent -> compile_formily -> persist_result`
- retry semantic pass once
- on repeated semantic validation failure, degrade to conservative schema plus warnings

Degradation rules for deterministic implementation:

- preserve section containers discovered from layout order
- preserve scalar fields with confidence `>= 0.80`
- preserve long-text fields with confidence `>= 0.75`
- drop `array-table` fields when column structure is invalid or confidence is below `0.85`
- drop boolean fields when checkbox evidence is ambiguous
- add a job-level warning for every dropped field and every degraded section
- recompute `overall_confidence` from only the compiled fields that remain in the degraded schema

- [ ] **Step 4: Run workflow tests**

Run: `uv run --project backend pytest backend/tests/workflows/test_recognition_graph.py -v`  
Expected: PASS with retry, degradation, and artifact writes covered.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflows/state.py backend/app/workflows/recognition_graph.py backend/app/workflows/runner.py backend/tests/workflows/test_recognition_graph.py
git commit -m "feat: add recognition workflow graph"
```

### Task 8: Expose FastAPI Job APIs

**Files:**
- Create: `backend/app/api/routes/jobs.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_jobs_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_post_jobs_returns_queued_job_id(client, sample_upload_file):
    response = client.post("/api/jobs", files={"file": sample_upload_file})
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_post_jobs_rejects_unsupported_media_type(client):
    response = client.post("/api/jobs", files={"file": ("bad.txt", b"x", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_get_job_status_includes_stage_and_elapsed_ms(client, seeded_job):
    response = client.get(f"/api/jobs/{seeded_job.job_id}")
    payload = response.json()
    assert payload["current_stage"] == "semantic_enrich"
    assert payload["elapsed_ms"] >= 0


def test_get_job_result_includes_overall_confidence(client, seeded_completed_job):
    response = client.get(f"/api/jobs/{seeded_completed_job.job_id}/result")
    payload = response.json()
    assert payload["overall_confidence"] == 0.91
```

- [ ] **Step 2: Run API tests to verify they fail**

Run: `uv run --project backend pytest backend/tests/api/test_jobs_api.py -v`  
Expected: FAIL because job routes are not registered.

- [ ] **Step 3: Implement the API contract**

```python
@router.post("/api/jobs", status_code=202)
async def create_job(file: UploadFile) -> JobStatusResponse:
    ...
```

Must cover:

- multipart field name `file`
- MIME validation for JPEG/PNG/WEBP
- 15 MB max upload size
- exact error shape: `{"error": {"code": str, "message": str, "retriable": bool}}`
- `400` invalid multipart payload
- `413` payload too large
- `422` image decode or validation failure
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/result`
- `GET /api/jobs/{job_id}/artifacts` gated by `ENABLE_DEV_ARTIFACTS`
- include `elapsed_ms`, top-level warnings, failed-job `error`, and artifact `prompt_versions`
- include test coverage for at least one `413` payload-too-large case and one `415` unsupported-media-type case
- include a `/result` test that locks `overall_confidence` to the arithmetic-mean rule from the spec on a fixed fixture
- use an in-process async execution primitive for the MVP: create the job as `queued`, then schedule the workflow with `asyncio.create_task(...)` inside a runner service so polling can observe `running` and final states without adding Celery/Redis
- mount dev artifact files with FastAPI `StaticFiles` under `/artifacts` when `ENABLE_DEV_ARTIFACTS=true`, so artifact response paths are actually fetchable

- [ ] **Step 4: Run API tests**

Run: `uv run --project backend pytest backend/tests/api/test_jobs_api.py -v`  
Expected: PASS with upload validation, exact error JSON, stage polling, result retrieval, and gated artifacts endpoint.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/jobs.py backend/app/main.py backend/tests/api/test_jobs_api.py
git commit -m "feat: add recognition job api"
```

### Task 9: Build the Frontend Operator Console

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/globals.css`
- Create: `frontend/.env.example`
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/components/recognition-console.tsx`
- Create: `frontend/components/upload-panel.tsx`
- Create: `frontend/components/job-status-panel.tsx`
- Create: `frontend/components/schema-preview.tsx`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/components/__tests__/recognition-console.test.tsx`
- Create: `frontend/components/__tests__/form-preview.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

```tsx
it("shows polling stages and final schema", async () => {
  render(<RecognitionConsole api={mockApi} />)
  await user.upload(screen.getByLabelText(/upload/i), file)
  expect(await screen.findByText(/semantic_enrich/i)).toBeInTheDocument()
  expect(await screen.findByText(/schema preview/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run frontend tests to verify they fail**

Run: `pnpm --dir frontend exec vitest run components/__tests__/recognition-console.test.tsx`  
Expected: FAIL because test tooling and components do not exist.

- [ ] **Step 3: Implement the console and API client**

```ts
export async function createJob(file: File): Promise<JobStatusResponse> {
  const formData = new FormData()
  formData.set("file", file)
  return request("/api/jobs", { method: "POST", body: formData })
}
```

Frontend requirements:

- install `@formily/core`, `@formily/react`, `@formily/antd-v5`, `antd`, `dayjs`, `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`
- render upload, stage timeline, schema JSON preview, copy/download actions
- keep the page single-purpose and thin
- connect to the backend via `NEXT_PUBLIC_API_BASE_URL` plus FastAPI CORS allowlist for the local frontend origin

- [ ] **Step 4: Run frontend tests and lint**

Run: `pnpm --dir frontend exec vitest run components/__tests__/recognition-console.test.tsx`  
Expected: PASS  

Run: `pnpm --dir frontend lint`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/app/page.tsx frontend/app/globals.css frontend/.env.example frontend/lib/types.ts frontend/lib/api.ts frontend/components/recognition-console.tsx frontend/components/upload-panel.tsx frontend/components/job-status-panel.tsx frontend/components/schema-preview.tsx frontend/vitest.config.ts frontend/vitest.setup.ts frontend/components/__tests__/recognition-console.test.tsx frontend/components/__tests__/form-preview.test.tsx
git commit -m "feat: add recognition operator console"
```

### Task 10: Add Formily Preview, Fixture Integration, and Runbooks

**Files:**
- Create: `frontend/lib/formily.ts`
- Create: `frontend/components/form-preview.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/README.md`
- Modify: `backend/README.md`
- Test: `frontend/components/__tests__/form-preview.test.tsx`

- [ ] **Step 1: Write failing preview tests**

```tsx
it("hydrates datetime defaults for formily preview", async () => {
  render(<FormPreview schema={sampleSchemaWithDate()} />)
  expect(await screen.findByLabelText("计划工作开始时间")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run preview tests to verify they fail**

Run: `pnpm --dir frontend exec vitest run components/__tests__/form-preview.test.tsx`  
Expected: FAIL because the preview adapter does not hydrate schema defaults yet.

- [ ] **Step 3: Implement the preview adapter and runbooks**

```ts
export function hydrateSchemaDefaults(schema: FormilySchema) {
  // Convert ISO strings to renderer-friendly date values for DatePicker preview only.
}
```

Also document:

- backend local setup with `uv sync --project backend`
- frontend local setup with `pnpm --dir frontend install`
- env vars for backend and frontend
- prompt-review checkpoint before enabling live semantic enrichment

- [ ] **Step 4: Run final focused verification**

Run: `uv run --project backend pytest backend/tests -v`  
Expected: PASS  

Run: `pnpm --dir frontend exec vitest run`  
Expected: PASS  

Run: `pnpm --dir frontend lint`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/formily.ts frontend/components/form-preview.tsx frontend/app/page.tsx frontend/README.md backend/README.md frontend/components/__tests__/form-preview.test.tsx
git commit -m "feat: add formily preview and setup docs"
```

## Suggested Verification Order

1. Backend smoke test
2. Contract tests
3. Storage tests
4. Layout normalization tests
5. Prompt builder tests
6. Compiler tests
7. Workflow tests
8. API tests
9. Frontend console tests
10. Final backend and frontend verification runs

## Handoff Notes

- Keep the backend in one process for the MVP; do not introduce Celery, Redis, or distributed workers.
- Prefer filesystem artifacts and in-memory job state first.
- Use the sample work-ticket fixture for regression, but keep OpenAI and PaddleOCR calls mockable in tests.
- Treat prompt approval as a hard checkpoint.
