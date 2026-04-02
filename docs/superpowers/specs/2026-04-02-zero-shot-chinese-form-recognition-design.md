# Zero-Shot Chinese Form Recognition MVP Design

Date: 2026-04-02
Project: `paddle-win`
Status: Approved for planning review

## Goal

Build an MVP that recognizes a single-page Chinese filled form image, uses PaddleOCR's general table recognition pipeline as the layout extraction base, strengthens semantics with an OpenAI multimodal model coordinated through LangGraph and LangChain, and returns a Formily Schema JSON file that can be consumed directly by a `@formily/antd-v5` editor or renderer.

The MVP is optimized for semi-structured Chinese forms similar to work tickets: title blocks, underlined fill-in areas, partial tables, long instructional text, date/time ranges, and checkbox-like execution markers.

## Scope

### In Scope

- Single-image recognition jobs
- Chinese filled forms as primary input
- Scan-quality images as the main target, with tolerance for mild skew, shadow, and imperfect crops
- Layout extraction with PaddleOCR Table Recognition V2
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

## Architecture

### Top-Level Components

1. Next.js frontend
2. FastAPI backend
3. PaddleOCR Table Recognition V2 pipeline
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
3. PaddleOCR extracts layout and table structure
4. Backend normalizes OCR output into an internal layout skeleton
5. OpenAI multimodal reasoning enriches the skeleton into a semantic form model
6. Backend validates the semantic form model
7. Backend deterministically compiles the validated model into Formily Schema JSON
8. Backend persists artifacts and exposes the final result

## Internal Data Model

The external API returns only Formily Schema JSON, but the backend uses three internal layers to keep the system debuggable and stable.

### Layer 1: OCR Layout Skeleton

This layer preserves geometry and reading order, not business meaning.

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

## API Design

The backend exposes a minimal asynchronous job interface.

### `POST /api/jobs`

Creates a recognition job from one uploaded image.

Response:

- `job_id`
- initial status

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

### `GET /api/jobs/{job_id}/result`

Returns the final Formily Schema JSON when the job succeeds.

### `GET /api/jobs/{job_id}/artifacts`

Development-only endpoint for inspecting intermediate outputs:

- OCR JSON
- normalized layout skeleton
- semantic form model
- final schema
- warnings
- prompt version references

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

- invoke PaddleOCR Table Recognition V2
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
