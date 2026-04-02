# Zero-Shot Chinese Form Recognition MVP Design

Date: 2026-04-02
Project: `paddle-win`
Status: Approved for planning review

## Goal

Build an MVP that recognizes a single-page Chinese filled form image, uses PaddleOCR's official General Table Recognition V2 pipeline as the layout extraction base, strengthens semantics with an OpenAI multimodal model coordinated through LangGraph and LangChain, and returns a Formily Schema JSON file that can be consumed directly by a `@formily/antd-v5` editor or renderer.

The MVP is optimized for semi-structured Chinese forms similar to work tickets: title blocks, underlined fill-in areas, partial tables, long instructional text, date/time ranges, and checkbox-like execution markers.

## Scope

### In Scope

- Single-image recognition jobs
- Chinese filled forms as primary input
- Scan-quality images as the main target, with tolerance for mild skew, shadow, and imperfect crops
- Layout extraction with PaddleOCR official General Table Recognition V2 pipeline
- Semantic enrichment with OpenAI multimodal reasoning
- LangGraph-based workflow orchestration
- LangChain-based model abstraction, prompt management, and structured outputs
- FastAPI backend for async job APIs
- Next.js frontend as a thin operator console
- Direct output as Formily Schema JSON for `@formily/antd-v5`
- Supported field kinds in the MVP:
  - string
  - datetime
  - textarea
  - boolean
  - array-table

### Out of Scope

- Multi-page PDF or multi-image aggregation
- Built-in manual correction workflow
- Complex annotation tools
- User accounts, permissions, or task history management
- Signature, seal, or stamp semantic recognition
- Robust mobile-photo understanding with strong perspective distortion
- General-purpose document understanding beyond semi-structured Chinese forms

## Product Shape

The user uploads one form image in the frontend. The frontend creates an asynchronous recognition job and polls status. The backend runs a graph-based recognition workflow, persists intermediate artifacts, and returns a final Formily Schema JSON when the job succeeds.

The frontend MVP intentionally stays thin:

- image upload
- job creation
- job status polling
- current pipeline stage display
- schema JSON preview
- basic Formily preview
- copy/download result

The MVP does not include an in-app correction experience. Any manual adjustment happens later in a Formily editor flow outside the recognition workbench.

## User Inputs and Expected Outputs

### Input Assumptions

- Primary input is a single image file
- The image usually contains a single Chinese form page
- The page is mostly readable and roughly aligned
- Filled values may be handwritten or machine-printed, but the MVP is not optimized for poor-quality handwriting

### Output Contract

The backend returns a single Formily Schema JSON document that can be consumed directly by `@formily/antd-v5`.

The schema prioritizes semantic correctness while preserving macro layout:

- section order is preserved
- major left/right grouping is preserved where meaningful
- table-like areas stay as structured tables
- exact pixel-level reproduction of the source page is not a goal

Filled values are included directly in the schema as field defaults so a renderer can immediately show a prefilled form.

Per-field metadata such as confidence, source references, and warnings are included in field metadata, not exposed as separate top-level business objects.

### Canonical Schema Conventions

To avoid compiler and frontend divergence, the MVP uses these exact conventions:

- All extracted values are stored in the schema node's `default` property. Formily maps `default` to the field's initial value.
- All defaults must stay JSON-serializable.
- `string` fields use a string `default`
- `textarea` fields use a string `default`
- `boolean` fields use a boolean `default`
- `array-table` fields store the entire row list on the array field's `default`, not separately on each cell field
- Datetime values are normalized to ISO-like strings with timezone information where possible, for example `2016-07-24T15:30:00+08:00`

Because the output artifact is JSON, datetime defaults are stored as strings. The frontend preview adapter is responsible for hydrating those strings into renderer-specific date objects when needed by `DatePicker`.

If the source document does not expose timezone information, the MVP normalizes datetimes using `+08:00`. This matches the initial target document domain and keeps the output deterministic.

Per-field metadata is attached under `x-data` with at least:

- `confidence`
- `source_boxes`
- `section_key`
- `field_role`
- `warnings`

`x-data.source_boxes` stores Layer 1 `EvidenceRef.source_id` values only. Bounding boxes and source typing remain in the internal semantic model and artifact files.

## Architecture

### Top-Level Components

1. Next.js frontend
2. FastAPI backend
3. PaddleOCR official `table_recognition_v2` / `TableRecognitionPipelineV2` pipeline
4. LangGraph workflow runtime
5. LangChain model and prompt layer
6. OpenAI multimodal model client via the OpenAI SDK
7. Artifact persistence for intermediate and final outputs

### Architectural Decision

The system uses:

- `LangGraph` for orchestration and workflow state transitions
- `LangChain` for prompt templates, structured model outputs, and chat-model abstraction
- `OpenAI SDK` as the actual model client

This is not a single linear chain. The workflow needs explicit state, validation, limited retries, and deterministic compilation, which makes LangGraph a better fit than a plain chain-only design.

### Recognition Flow

1. Frontend uploads a single image and creates an async job
2. FastAPI stores the source image and starts the recognition graph
3. PaddleOCR official General Table Recognition V2 pipeline extracts layout and table structure
4. Backend normalizes OCR output into an internal layout skeleton
5. OpenAI multimodal reasoning enriches the skeleton into a semantic form model
6. Backend validates the semantic form model
7. Backend deterministically compiles the validated model into Formily Schema JSON
8. Backend persists artifacts and exposes the final result

## Internal Data Model

The external API returns only Formily Schema JSON, but the backend uses three internal layers to keep the system debuggable and stable.

### Layer 1: OCR Layout Skeleton

This layer preserves geometry and reading order, not business meaning.

It is derived specifically from PaddleOCR's official General Table Recognition V2 pipeline output, not from a lower-level substitute entrypoint.

It includes:

- page metadata
- image preprocessing metadata
- text boxes
- line and cell regions
- table structures
- paragraph blocks
- candidate underline-fill regions
- candidate checkbox regions
- adjacency relationships
- OCR confidence values

### Layer 2: Semantic Form Model

This is the main internal representation produced after multimodal reasoning.

It includes:

- `form_meta`
  - title
  - document type
  - document number
- `sections`
  - ordered logical sections such as basic info, work content, time range, safety measures
- `fields`
  - normalized field records with:
    - stable field key
    - Chinese title
    - field kind
    - extracted value
    - confidence
    - evidence references
- `layout_hints`
  - macro layout intent such as section sequence, coarse columns, and table presence
- `warnings`
  - uncertain extractions and semantic conflicts

Allowed field kinds in the MVP:

- `string`
- `datetime`
- `textarea`
- `boolean`
- `array-table`

### Strict Semantic Model Contract

The semantic model is a strict typed contract between `semantic_enrich`, `validate_schema_intent`, and `compile_formily`.

Pydantic-style shape:

```python
class EvidenceRef(BaseModel):
    source_id: str
    source_type: Literal["text_box", "table_cell", "table_region", "checkbox_region", "image_region"]
    bbox: list[float]
    page: int = 1


class SemanticWarning(BaseModel):
    code: str
    message: str
    severity: Literal["low", "medium", "high"]
    related_field_keys: list[str] = []


class LayoutHints(BaseModel):
    section_order: list[str]
    preferred_columns: dict[str, int]
    section_spans: dict[str, Literal["full", "left", "right", "table"]]


class SemanticField(BaseModel):
    key: str
    title: str
    kind: Literal["string", "datetime", "textarea", "boolean", "array-table"]
    section_key: str
    field_role: str
    value: str | bool | list[dict[str, object]] | None
    confidence: float
    evidence: list[EvidenceRef]
    warnings: list[str] = []


class SemanticSection(BaseModel):
    key: str
    title: str
    field_keys: list[str]
    order: int
    section_type: Literal["basic", "group", "table", "long_text"]


class FormMeta(BaseModel):
    title: str | None = None
    document_type: str | None = None
    document_number: str | None = None


class SemanticFormModel(BaseModel):
    form_meta: FormMeta
    sections: list[SemanticSection]
    fields: list[SemanticField]
    layout_hints: LayoutHints
    warnings: list[SemanticWarning]
```

Canonical JSON example:

```json
{
  "form_meta": {
    "title": "配电第一种工作票",
    "document_type": "电力工作票",
    "document_number": "2017070007"
  },
  "sections": [
    {
      "key": "basic_info",
      "title": "基本信息",
      "field_keys": ["work_leader", "team_leader", "plan_start_at", "plan_end_at"],
      "order": 1,
      "section_type": "basic"
    },
    {
      "key": "work_items",
      "title": "工作任务",
      "field_keys": ["work_items_table"],
      "order": 2,
      "section_type": "table"
    }
  ],
  "fields": [
    {
      "key": "work_leader",
      "title": "工作负责人",
      "kind": "string",
      "section_key": "basic_info",
      "field_role": "person_name",
      "value": "闫丽亚",
      "confidence": 0.98,
      "evidence": [
        {
          "source_id": "box_12",
          "source_type": "text_box",
          "bbox": [120.0, 88.0, 210.0, 114.0],
          "page": 1
        }
      ],
      "warnings": []
    },
    {
      "key": "work_items_table",
      "title": "工作任务",
      "kind": "array-table",
      "section_key": "work_items",
      "field_role": "table",
      "value": [
        {
          "location_or_equipment": "10kV白55厂岗线XX杆大段湾台区",
          "work_content": "安装关口表"
        }
      ],
      "confidence": 0.93,
      "evidence": [
        {
          "source_id": "table_1",
          "source_type": "table_region",
          "bbox": [32.0, 250.0, 482.0, 368.0],
          "page": 1
        }
      ],
      "warnings": []
    }
  ],
  "layout_hints": {
    "section_order": ["basic_info", "work_items"],
    "preferred_columns": {
      "basic_info": 2,
      "work_items": 1
    },
    "section_spans": {
      "basic_info": "full",
      "work_items": "table"
    }
  },
  "warnings": []
}
```

### Layer 3: Formily Schema

This is the only external business output.

Compilation rules:

- root node uses `type: "object"`
- major sections compile to `Void` containers
- layout uses coarse-grained containers such as `FormGrid`
- text fields map to `Input`
- long text maps to `Input.TextArea`
- booleans map to `Checkbox`
- tabular regions map to `ArrayTable`
- date and time ranges compile into explicit start/end fields instead of opaque range objects

Recognized values are written into field defaults so a consumer can immediately render the extracted form state.

Field metadata such as confidence and source evidence are attached via Formily field metadata, for example in `x-data`.

`overall_confidence` in API responses is computed as the arithmetic mean of all compiled field confidences after validation and any degradation.

### Deterministic Field Key Strategy

Field keys must be stable across retries on the same source image unless the semantic interpretation changes materially.

Rules:

1. Prefer semantic role keys when available, for example `work_leader`, `team_leader`, `plan_start_at`
2. Prefix ambiguous repeated fields with the section key, for example `safety_measures__executor`
3. When no semantic role is available, fall back to `section_key__field_<ordinal>`
4. If a collision still occurs, append a deterministic suffix derived from layout order, not randomness

This key strategy is required so downstream Formily consumers do not see meaningless key churn between runs.

### Canonical Minimal Formily Shapes

The schema compiler targets the following minimal shapes.

#### Simple Scalar Fields

```json
{
  "type": "object",
  "properties": {
    "basic_info": {
      "type": "void",
      "x-component": "FormGrid",
      "x-component-props": {
        "maxColumns": 2,
        "minColumns": 1
      },
      "properties": {
        "work_leader": {
          "type": "string",
          "title": "工作负责人",
          "x-decorator": "FormItem",
          "x-component": "Input",
          "default": "闫丽亚",
          "x-data": {
            "confidence": 0.98,
            "section_key": "basic_info",
            "field_role": "person_name",
            "source_boxes": ["box_12", "box_13"],
            "warnings": []
          }
        },
        "plan_start_at": {
          "type": "string",
          "format": "date-time",
          "title": "计划工作开始时间",
          "x-decorator": "FormItem",
          "x-component": "DatePicker",
          "x-component-props": {
            "showTime": true
          },
          "default": "2016-07-24T15:30:00+08:00",
          "x-data": {
            "confidence": 0.91,
            "section_key": "basic_info",
            "field_role": "datetime_start",
            "source_boxes": ["box_41"],
            "warnings": []
          }
        },
        "safety_note": {
          "type": "string",
          "title": "安全措施",
          "x-decorator": "FormItem",
          "x-component": "Input.TextArea",
          "default": "断开10kV白线55厂两线XX杆大段湾配变台区0.4kV大段湾出线剩余电流动作开关",
          "x-data": {
            "confidence": 0.87,
            "section_key": "safety_measures",
            "field_role": "long_text",
            "source_boxes": ["box_58", "box_59"],
            "warnings": []
          }
        },
        "executed": {
          "type": "boolean",
          "title": "已执行",
          "x-decorator": "FormItem",
          "x-component": "Checkbox",
          "default": true,
          "x-data": {
            "confidence": 0.89,
            "section_key": "safety_measures",
            "field_role": "status_checkbox",
            "source_boxes": ["box_61"],
            "warnings": []
          }
        }
      }
    }
  }
}
```

#### ArrayTable

`ArrayTable` always compiles as an object-array field. The recognized rows live on the array field's `default`.

```json
{
  "type": "array",
  "title": "工作任务",
  "x-decorator": "FormItem",
  "x-component": "ArrayTable",
  "default": [
    {
      "location_or_equipment": "10kV白55厂岗线XX杆大段湾台区",
      "work_content": "安装关口表"
    }
  ],
  "x-data": {
    "confidence": 0.93,
    "section_key": "work_items",
    "field_role": "table",
    "source_boxes": ["table_1"],
    "warnings": []
  },
  "items": {
    "type": "object",
    "properties": {
      "location_or_equipment_column": {
        "type": "void",
        "x-component": "ArrayTable.Column",
        "x-component-props": {
          "title": "工作地点或设备"
        },
        "properties": {
          "location_or_equipment": {
            "type": "string",
            "x-decorator": "FormItem",
            "x-component": "Input"
          }
        }
      },
      "work_content_column": {
        "type": "void",
        "x-component": "ArrayTable.Column",
        "x-component-props": {
          "title": "工作内容"
        },
        "properties": {
          "work_content": {
            "type": "string",
            "x-decorator": "FormItem",
            "x-component": "Input"
          }
        }
      }
    }
  }
}
```

## API Design

The backend exposes a minimal asynchronous job interface.

### `POST /api/jobs`

Creates a recognition job from one uploaded image.

Request contract:

- content type: `multipart/form-data`
- file field name: `file`
- accepted MIME types in the MVP:
  - `image/jpeg`
  - `image/png`
  - `image/webp`
- maximum upload size in the MVP: 15 MB

Response:

- `job_id`
- initial status

Success response example:

```json
{
  "job_id": "job_123",
  "status": "queued",
  "current_stage": "ingest",
  "created_at": "2026-04-02T20:10:00+08:00"
}
```

Error responses:

- `400` invalid multipart payload
- `413` file too large
- `415` unsupported media type
- `422` image cannot be decoded or fails validation

Error shape:

```json
{
  "error": {
    "code": "unsupported_media_type",
    "message": "Only JPEG, PNG, and WEBP are accepted in the MVP.",
    "retriable": false
  }
}
```

### `GET /api/jobs/{job_id}`

Returns:

- `job_id`
- status: `queued | running | succeeded | failed`
- current stage:
  - `ingest`
  - `ocr_table`
  - `normalize_layout`
  - `semantic_enrich`
  - `validate_schema_intent`
  - `compile_formily`
  - `persist_result`
- elapsed metadata
- warning summary if available
- error summary if the job is failed

Success response example:

```json
{
  "job_id": "job_123",
  "status": "running",
  "current_stage": "semantic_enrich",
  "elapsed_ms": 5231,
  "warnings": [
    {
      "code": "low_confidence_checkbox",
      "message": "One checkbox candidate remains uncertain."
    }
  ]
}
```

Failed-job shape:

```json
{
  "job_id": "job_123",
  "status": "failed",
  "current_stage": "semantic_enrich",
  "error": {
    "code": "semantic_output_invalid",
    "message": "Model output failed structured validation after retry.",
    "retriable": true
  }
}
```

### `GET /api/jobs/{job_id}/result`

Returns the final Formily Schema JSON when the job succeeds.

Success response example:

```json
{
  "job_id": "job_123",
  "status": "succeeded",
  "overall_confidence": 0.91,
  "schema": {
    "type": "object",
    "properties": {
      "work_leader": {
        "type": "string",
        "title": "工作负责人",
        "x-decorator": "FormItem",
        "x-component": "Input",
        "default": "闫丽亚"
      }
    }
  },
  "warnings": []
}
```

### `GET /api/jobs/{job_id}/artifacts`

Development-only endpoint for inspecting intermediate outputs:

- OCR JSON
- normalized layout skeleton
- semantic form model
- final schema
- warnings
- prompt version references

This endpoint is available only when `ENABLE_DEV_ARTIFACTS=true`.

Artifacts are retained on a best-effort basis for local development and may be manually cleaned up. Long-term retention policy is outside the MVP.

Success response example:

```json
{
  "job_id": "job_123",
  "artifacts": {
    "source_image": "/artifacts/job_123/source.jpg",
    "ocr_json": "/artifacts/job_123/ocr.json",
    "layout_skeleton": "/artifacts/job_123/layout.json",
    "semantic_form_model": "/artifacts/job_123/semantic.json",
    "formily_schema": "/artifacts/job_123/schema.json"
  },
  "prompt_versions": {
    "semantic_enrich": "sem_v1_draft",
    "validate_schema_intent": "val_v1"
  },
  "warnings": []
}
```

## LangGraph Workflow

The graph operates over a single `RecognitionState` object.

### `RecognitionState`

The state stores at minimum:

- job metadata
- input image path
- normalized image path
- OCR result
- normalized layout skeleton
- semantic form model
- validation warnings
- retry counters
- prompt version identifiers
- final Formily schema
- error summary
- current stage

### Nodes

#### `ingest`

- validate input file
- normalize orientation and basic image hygiene
- persist original and processed image references

#### `ocr_table`

- invoke PaddleOCR official General Table Recognition V2 pipeline via `table_recognition_v2` / `TableRecognitionPipelineV2`
- persist raw OCR outputs

#### `normalize_layout`

- convert PaddleOCR output into the internal layout skeleton
- preserve table and reading-order structure
- infer candidate underline-fill and checkbox regions where feasible

#### `semantic_enrich`

- call the OpenAI multimodal model with:
  - the source image
  - normalized OCR skeleton
  - a constrained prompt
- request a structured semantic form model, not final Formily Schema

#### `validate_schema_intent`

- validate semantic consistency before compilation
- examples:
  - paired start/end time fields exist where needed
  - checkbox semantics are boolean-like
  - tables have columns and rows in a consistent shape
  - fields are attached to the correct section
  - duplicate or contradictory fields are surfaced as warnings

#### `compile_formily`

- deterministically compile the validated semantic model into Formily Schema JSON

#### `persist_result`

- save final schema and relevant artifacts
- update final job state

## Prompting and Model Governance

The multimodal model does not directly generate the final Formily Schema.
It generates the semantic form model, which is then validated and compiled by deterministic backend logic.

This is a hard design constraint to reduce schema drift and improve debuggability.

### Prompt Review Requirement

Before productionizing the semantic prompt chain:

- the prompt drafts for `semantic_enrich` and related semantic validation logic must be shown to the user first
- the user will test those prompts against real sample forms
- only after that review should the prompt be connected into the formal workflow

Prompt versions must be tracked in job artifacts for reproducibility.

## Failure Handling and Degradation

### PaddleOCR Failure

- mark the job failed
- return a clear failure state and diagnostic summary

### Multimodal Output Invalid

- retry only the semantic pass once
- do not rerun the entire OCR stage unless explicitly needed later

### Validation Failure After Retry

Compile a conservative schema if possible:

- preserve obvious sections
- preserve high-confidence text fields
- downgrade uncertain structures into warnings
- avoid inventing high-risk checkbox or table semantics when confidence is low

### Unexpected Runtime Errors

- capture the failing node
- record the exception summary
- mark the job failed with a recoverable diagnostic shape

## Frontend MVP

The frontend is a single operator console in Next.js.

### Required Screens and Behaviors

- single upload surface
- async job creation
- status and current stage display
- result preview area
- raw Formily Schema JSON view
- basic rendered form preview using the resulting schema
- copy and download actions

### Deliberate Omissions

- no embedded correction workspace
- no history dashboard
- no multi-document workflow
- no prompt management UI

## Testing Strategy

### Unit Tests

- OCR normalization
- semantic model validators
- schema compiler
- degradation behavior for invalid semantic outputs

### Integration Tests

- FastAPI job lifecycle
- LangGraph node transitions
- artifact persistence
- schema result retrieval

External model calls should be mockable.

### Regression Tests With Sample Forms

Maintain a small corpus of Chinese semi-structured form images covering:

- title and identifier blocks
- underline-fill regions
- table regions
- long safety/instruction paragraphs
- time ranges
- checkbox-like execution markers

Primary regression criteria:

- key field recall
- field kind accuracy
- schema consumability by the frontend

## Acceptance Criteria

The MVP is accepted when all of the following are true:

1. A user can upload a single image from the frontend and receive a `job_id`
2. The frontend can poll and display async recognition progress
3. The backend can process a semi-structured Chinese form image through PaddleOCR and multimodal enrichment
4. The backend returns Formily Schema JSON directly consumable by `@formily/antd-v5`
5. The output preserves major sections and tables without requiring pixel-perfect layout reconstruction
6. Recognized values appear directly in the resulting schema defaults
7. Intermediate artifacts are inspectable in development mode
8. Prompt drafts are reviewed by the user before final semantic prompt integration

## Open Decisions Deferred to Planning

These are not unresolved product questions. They are implementation details intentionally deferred to planning:

- exact artifact storage mechanism
- exact queue/background execution primitive
- exact OpenAI model version
- exact schema metadata shape under `x-data`
- exact frontend preview library wiring for Formily

## Summary

This MVP is a structured, inspectable recognition system rather than a one-shot black-box generator. PaddleOCR provides layout structure, OpenAI multimodal reasoning supplies semantic understanding, LangGraph manages the workflow, LangChain provides model abstractions, and deterministic backend compilation produces a stable Formily Schema output suitable for downstream editing and rendering.
