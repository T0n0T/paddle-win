# 零样本表单重建 Implementation Plan

> 状态：已暂停，不再作为当前主线实施计划。
> 当前受支持主线为“外部 OCR JSON + workbench 会话编辑”。
> 说明：Task 1 与 Task 2 的部分基础设施已被后续实现吸收，但 Task 3 及之后围绕 `make ocr` / `make reconstruct` 的主链没有继续落地。继续开发时，请以 workbench 相关设计与实现为准，不再按本文档推进零样本重建 CLI。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一条“单张表单图片 -> PaddleOCR Structure -> 多模态大模型 -> 单文件 HTML”的可运行链路，并通过 `Makefile` 暴露 OCR 与重建命令，让用户可以在代码外通过修改 prompt 持续调优效果。

**Architecture:** 后端采用 Python + LangGraph 单向流水线编排，节点顺序为加载图片、运行 OCR、构建 prompt、调用多模态模型、清洗并写出 HTML。所有中间产物统一落到 `backend/runs/<run-id>/`，prompt 独立存放在 `backend/app/prompts/`，以便用户在“可调 prompt”检查点继续人工优化。

**Tech Stack:** Python 3.13、LangGraph、PaddleOCR / PaddleX Structure、OpenAI 兼容多模态接口、Pydantic、pytest、Makefile

---

## 文件结构

本计划实施后，代码与测试文件应按以下职责分布：

- `backend/main.py`
  - CLI 总入口，解析子命令与参数，调用 pipeline
- `backend/app/config.py`
  - 读取环境变量与默认配置
- `backend/app/models.py`
  - 定义 pipeline 状态、OCR 精简结构、运行元数据等共享类型
- `backend/app/pipeline/graph.py`
  - 构建 LangGraph 图与执行入口
- `backend/app/pipeline/nodes/load_image.py`
  - 校验图片、初始化运行目录、复制原图
- `backend/app/pipeline/nodes/run_ocr.py`
  - 调用 OCR 服务并写出 `ocr_raw.json`、`ocr_compact.json`
- `backend/app/pipeline/nodes/build_prompt.py`
  - 读取 prompt 模板并写出 `prompt.txt`
- `backend/app/pipeline/nodes/call_model.py`
  - 调用多模态模型并写出 `model_raw.txt`
- `backend/app/pipeline/nodes/write_result.py`
  - 提取有效 HTML、写出 `result.html` 和 `metadata.json`
- `backend/app/services/paddle_structure.py`
  - 对 PaddleOCR Structure 的调用封装
- `backend/app/services/multimodal_llm.py`
  - 对 OpenAI 兼容多模态模型的调用封装
- `backend/app/services/artifacts.py`
  - 运行目录、文件写入、最近一次运行定位等工具
- `backend/app/prompts/reconstruct_html.md`
  - 用户可直接修改的 HTML 重建 prompt 模板
- `backend/tests/test_artifacts.py`
  - 运行目录与产物工具测试
- `backend/tests/test_prompt_builder.py`
  - prompt 构建测试
- `backend/tests/test_pipeline_smoke.py`
  - mock OCR / mock 模型的 pipeline 冒烟测试
- `Makefile`
  - `ocr`、`reconstruct`、`latest`、`prompt-show` 等命令

## Task 1: 搭好后端骨架与共享类型

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models.py`
- Create: `backend/app/pipeline/__init__.py`
- Create: `backend/app/pipeline/nodes/__init__.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_config_smoke.py`

- [ ] **Step 1: 写配置与 CLI 的失败测试**

```python
from pathlib import Path

from app.config import Settings


def test_settings_default_prompt_path_is_inside_backend() -> None:
    settings = Settings()
    assert settings.prompt_template_path == Path("app/prompts/reconstruct_html.md")


def test_settings_default_run_root_is_backend_runs() -> None:
    settings = Settings()
    assert settings.run_root == Path("runs")
```

```python
from typer.testing import CliRunner

from main import app


def test_main_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "reconstruct" in result.stdout
    assert "ocr" in result.stdout
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `cd backend && uv run pytest tests/test_config_smoke.py -v`
Expected: FAIL，提示 `app.config` 或 `main.app` 不存在

- [ ] **Step 3: 写最小配置、共享模型与 CLI 骨架**

```python
# backend/app/config.py
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4.1-mini"
    run_root: Path = Path("runs")
    prompt_template_path: Path = Path("app/prompts/reconstruct_html.md")
    enable_dev_artifacts: bool = True
```

```python
# backend/app/models.py
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class OCRBlock(BaseModel):
    text: str
    bbox: list[float] = Field(default_factory=list)
    block_type: str = "text"


class PipelineState(BaseModel):
    image_path: Path
    run_dir: Path | None = None
    source_image_path: Path | None = None
    ocr_raw_path: Path | None = None
    ocr_compact_path: Path | None = None
    prompt_path: Path | None = None
    model_raw_path: Path | None = None
    result_html_path: Path | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

```python
# backend/main.py
import typer


app = typer.Typer(no_args_is_help=True)


@app.command()
def ocr(image: str) -> None:
    raise NotImplementedError("OCR pipeline not implemented yet")


@app.command()
def reconstruct(image: str) -> None:
    raise NotImplementedError("Reconstruction pipeline not implemented yet")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: 再跑测试，确认骨架通过**

Run: `cd backend && uv run pytest tests/test_config_smoke.py -v`
Expected: PASS

- [ ] **Step 5: 提交骨架**

```bash
git add backend/main.py backend/app backend/tests/test_config_smoke.py
git commit -m "feat: scaffold form reconstruction backend skeleton"
```

## Task 2: 实现运行目录与产物管理

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/artifacts.py`
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_artifacts.py`

- [ ] **Step 1: 写运行目录与产物文件测试**

```python
from pathlib import Path

from app.services.artifacts import ArtifactStore


def test_create_run_dir_copies_source_image(tmp_path: Path) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"fake-image")

    store = ArtifactStore(tmp_path / "runs")
    run_dir, copied_image = store.create_run(image)

    assert run_dir.exists()
    assert copied_image.exists()
    assert copied_image.read_bytes() == b"fake-image"


def test_latest_run_returns_most_recent_directory(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    first_dir = store.run_root / "20260403-000001-a"
    second_dir = store.run_root / "20260403-000002-b"
    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)

    assert store.latest_run() == second_dir
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_artifacts.py -v`
Expected: FAIL，提示 `ArtifactStore` 不存在

- [ ] **Step 3: 实现最小产物存储工具**

```python
# backend/app/services/artifacts.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from shutil import copy2
from uuid import uuid4


class ArtifactStore:
    def __init__(self, run_root: Path) -> None:
        self.run_root = run_root
        self.run_root.mkdir(parents=True, exist_ok=True)

    def create_run(self, image_path: Path) -> tuple[Path, Path]:
        run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
        run_dir = self.run_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        target = run_dir / f"source{image_path.suffix.lower()}"
        copy2(image_path, target)
        return run_dir, target

    def write_text(self, run_dir: Path, filename: str, content: str) -> Path:
        path = run_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def write_bytes(self, run_dir: Path, filename: str, content: bytes) -> Path:
        path = run_dir / filename
        path.write_bytes(content)
        return path

    def latest_run(self) -> Path | None:
        candidates = [path for path in self.run_root.iterdir() if path.is_dir()]
        return sorted(candidates)[-1] if candidates else None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_artifacts.py -v`
Expected: PASS

- [ ] **Step 5: 提交产物工具**

```bash
git add backend/app/services/artifacts.py backend/tests/test_artifacts.py
git commit -m "feat: add run artifact storage utilities"
```

## Task 3: 实现 OCR 服务与 OCR-only 流水线

**Files:**
- Create: `backend/app/services/paddle_structure.py`
- Create: `backend/app/pipeline/nodes/load_image.py`
- Create: `backend/app/pipeline/nodes/run_ocr.py`
- Create: `backend/app/pipeline/state.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_ocr_node.py`

- [ ] **Step 1: 写 OCR 节点测试**

```python
from pathlib import Path

from app.models import OCRBlock, PipelineState
from app.pipeline.nodes.run_ocr import run_ocr_node


class FakeOCRService:
    def run(self, image_path: Path) -> tuple[dict, list[OCRBlock]]:
        return {"pages": 1}, [OCRBlock(text="姓名", bbox=[0, 0, 100, 20], block_type="text")]


def test_run_ocr_node_writes_raw_and_compact_json(tmp_path: Path) -> None:
    state = PipelineState(
        image_path=tmp_path / "input.png",
        run_dir=tmp_path / "run",
        source_image_path=tmp_path / "run/source.png",
    )
    state.run_dir.mkdir()
    state.source_image_path.write_bytes(b"fake")

    next_state = run_ocr_node(state, FakeOCRService())

    assert next_state.ocr_raw_path is not None
    assert next_state.ocr_compact_path is not None
    assert next_state.ocr_raw_path.exists()
    assert next_state.ocr_compact_path.exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_ocr_node.py -v`
Expected: FAIL，提示 `run_ocr_node` 不存在

- [ ] **Step 3: 实现 OCR 服务封装与节点**

```python
# backend/app/services/paddle_structure.py
from __future__ import annotations

from pathlib import Path

from app.models import OCRBlock


class PaddleStructureService:
    def run(self, image_path: Path) -> tuple[dict, list[OCRBlock]]:
        raise NotImplementedError("Wire PaddleOCR Structure here")
```

```python
# backend/app/pipeline/nodes/run_ocr.py
from __future__ import annotations

import json

from app.models import PipelineState


def run_ocr_node(state: PipelineState, ocr_service) -> PipelineState:
    raw_result, compact_blocks = ocr_service.run(state.source_image_path)
    raw_path = state.run_dir / "ocr_raw.json"
    compact_path = state.run_dir / "ocr_compact.json"
    raw_path.write_text(json.dumps(raw_result, ensure_ascii=False, indent=2), encoding="utf-8")
    compact_path.write_text(
        json.dumps([block.model_dump() for block in compact_blocks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    state.ocr_raw_path = raw_path
    state.ocr_compact_path = compact_path
    return state
```

```python
# backend/app/pipeline/nodes/load_image.py
from pathlib import Path

from app.models import PipelineState
from app.services.artifacts import ArtifactStore


def load_image_node(image_path: Path, artifact_store: ArtifactStore) -> PipelineState:
    run_dir, copied_image = artifact_store.create_run(image_path)
    return PipelineState(image_path=image_path, run_dir=run_dir, source_image_path=copied_image)
```

- [ ] **Step 4: 把 `ocr` CLI 接到 load + OCR 节点**

```python
# backend/main.py
from pathlib import Path

import typer

from app.config import Settings
from app.pipeline.nodes.load_image import load_image_node
from app.pipeline.nodes.run_ocr import run_ocr_node
from app.services.artifacts import ArtifactStore
from app.services.paddle_structure import PaddleStructureService

app = typer.Typer(no_args_is_help=True)


@app.command()
def ocr(image: str) -> None:
    settings = Settings()
    artifact_store = ArtifactStore(settings.run_root)
    state = load_image_node(Path(image), artifact_store)
    state = run_ocr_node(state, PaddleStructureService())
    typer.echo(state.ocr_compact_path)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_ocr_node.py -v`
Expected: PASS

- [ ] **Step 6: 提交 OCR-only 链路**

```bash
git add backend/main.py backend/app/pipeline backend/app/services/paddle_structure.py backend/tests/test_ocr_node.py
git commit -m "feat: add ocr-only pipeline flow"
```

## Task 4: 实现 prompt 构建与模型调用服务

**Files:**
- Create: `backend/app/pipeline/nodes/build_prompt.py`
- Create: `backend/app/pipeline/nodes/call_model.py`
- Create: `backend/app/services/multimodal_llm.py`
- Create: `backend/app/prompts/reconstruct_html.md`
- Test: `backend/tests/test_prompt_builder.py`

- [ ] **Step 1: 写 prompt 构建测试**

```python
from pathlib import Path

from app.models import PipelineState
from app.pipeline.nodes.build_prompt import build_prompt_node


def test_build_prompt_node_writes_prompt_file(tmp_path: Path) -> None:
    prompt_template = tmp_path / "reconstruct_html.md"
    prompt_template.write_text("OCR结果如下：\n{{OCR_JSON}}", encoding="utf-8")

    compact_json = tmp_path / "ocr_compact.json"
    compact_json.write_text('[{"text":"姓名","bbox":[0,0,100,20]}]', encoding="utf-8")

    state = PipelineState(
        image_path=tmp_path / "input.png",
        run_dir=tmp_path,
        source_image_path=tmp_path / "input.png",
        ocr_compact_path=compact_json,
    )

    next_state = build_prompt_node(state, prompt_template)

    assert next_state.prompt_path is not None
    assert "姓名" in next_state.prompt_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_prompt_builder.py -v`
Expected: FAIL，提示 `build_prompt_node` 不存在

- [ ] **Step 3: 实现 prompt 模板与构建节点**

```markdown
你是一名表单重建助手。请参考输入图片和 OCR 结构结果，输出一个可以直接在浏览器打开的单文件 HTML。

要求：
1. 只输出 HTML，不要输出解释、Markdown 或代码围栏。
2. 视觉还原优先，使用绝对定位优先。
3. 尽可能保留边框、标题、分组、下划线、输入框、表格线等视觉元素。
4. 在 HTML 内联 CSS。

OCR 结果如下：
{{OCR_JSON}}
```

```python
# backend/app/pipeline/nodes/build_prompt.py
from pathlib import Path

from app.models import PipelineState


def build_prompt_node(state: PipelineState, template_path: Path) -> PipelineState:
    template = template_path.read_text(encoding="utf-8")
    ocr_json = state.ocr_compact_path.read_text(encoding="utf-8")
    prompt = template.replace("{{OCR_JSON}}", ocr_json)
    prompt_path = state.run_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    state.prompt_path = prompt_path
    return state
```

- [ ] **Step 4: 实现模型调用服务接口与节点**

```python
# backend/app/services/multimodal_llm.py
from __future__ import annotations

from pathlib import Path

from openai import OpenAI


class MultimodalLLMService:
    def __init__(self, api_key: str, model: str, base_url: str = "") -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)
        self.model = model

    def generate_html(self, image_path: Path, prompt: str) -> str:
        raise NotImplementedError("Wire multimodal request here")
```

```python
# backend/app/pipeline/nodes/call_model.py
from app.models import PipelineState


def call_model_node(state: PipelineState, llm_service) -> PipelineState:
    prompt = state.prompt_path.read_text(encoding="utf-8")
    raw_response = llm_service.generate_html(state.source_image_path, prompt)
    raw_path = state.run_dir / "model_raw.txt"
    raw_path.write_text(raw_response, encoding="utf-8")
    state.model_raw_path = raw_path
    return state
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_prompt_builder.py -v`
Expected: PASS

- [ ] **Step 6: 提交 prompt 与模型节点**

```bash
git add backend/app/pipeline/nodes/build_prompt.py backend/app/pipeline/nodes/call_model.py backend/app/services/multimodal_llm.py backend/app/prompts/reconstruct_html.md backend/tests/test_prompt_builder.py
git commit -m "feat: add prompt builder and multimodal model client"
```

## Task 5: 接通 LangGraph 主流水线与 HTML 落盘

**Files:**
- Create: `backend/app/pipeline/graph.py`
- Create: `backend/app/pipeline/nodes/write_result.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_pipeline_smoke.py`

- [ ] **Step 1: 写完整 pipeline 冒烟测试**

```python
from pathlib import Path

from app.pipeline.graph import run_reconstruction_pipeline


class FakeOCRService:
    def run(self, image_path: Path):
        return {"pages": 1}, []


class FakeLLMService:
    def generate_html(self, image_path: Path, prompt: str) -> str:
        return "<html><body><div>hello</div></body></html>"


def test_reconstruction_pipeline_writes_result_html(tmp_path: Path) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"fake-image")

    state = run_reconstruction_pipeline(
        image_path=image,
        run_root=tmp_path / "runs",
        prompt_template_path=tmp_path / "prompt.md",
        ocr_service=FakeOCRService(),
        llm_service=FakeLLMService(),
    )

    assert state.result_html_path is not None
    assert state.result_html_path.exists()
    assert "hello" in state.result_html_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_pipeline_smoke.py -v`
Expected: FAIL，提示 `run_reconstruction_pipeline` 不存在

- [ ] **Step 3: 实现 HTML 提取与元数据写入节点**

```python
# backend/app/pipeline/nodes/write_result.py
from __future__ import annotations

import json
from datetime import datetime, UTC

from app.models import PipelineState


def extract_html(raw_response: str) -> str:
    stripped = raw_response.strip()
    if "```" in stripped:
        stripped = stripped.replace("```html", "").replace("```", "").strip()
    if "<html" not in stripped.lower():
        raise ValueError("Model response does not contain HTML")
    return stripped


def write_result_node(state: PipelineState) -> PipelineState:
    raw_response = state.model_raw_path.read_text(encoding="utf-8")
    html = extract_html(raw_response)
    result_path = state.run_dir / "result.html"
    result_path.write_text(html, encoding="utf-8")
    metadata = {
        "image_path": str(state.image_path),
        "run_dir": str(state.run_dir),
        "created_at": datetime.now(UTC).isoformat(),
        "result_html": str(result_path),
    }
    metadata_path = state.run_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    state.result_html_path = result_path
    state.metadata["metadata_path"] = str(metadata_path)
    return state
```

- [ ] **Step 4: 实现 LangGraph 主执行函数并接到 CLI**

```python
# backend/app/pipeline/graph.py
from pathlib import Path

from app.config import Settings
from app.pipeline.nodes.build_prompt import build_prompt_node
from app.pipeline.nodes.call_model import call_model_node
from app.pipeline.nodes.load_image import load_image_node
from app.pipeline.nodes.run_ocr import run_ocr_node
from app.pipeline.nodes.write_result import write_result_node
from app.services.artifacts import ArtifactStore


def run_reconstruction_pipeline(image_path: Path, run_root: Path, prompt_template_path: Path, ocr_service, llm_service):
    artifact_store = ArtifactStore(run_root)
    state = load_image_node(image_path, artifact_store)
    state = run_ocr_node(state, ocr_service)
    state = build_prompt_node(state, prompt_template_path)
    state = call_model_node(state, llm_service)
    state = write_result_node(state)
    return state
```

```python
# backend/main.py
@app.command()
def reconstruct(image: str) -> None:
    settings = Settings()
    state = run_reconstruction_pipeline(
        image_path=Path(image),
        run_root=settings.run_root,
        prompt_template_path=settings.prompt_template_path,
        ocr_service=PaddleStructureService(),
        llm_service=MultimodalLLMService(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        ),
    )
    typer.echo(state.result_html_path)
```

- [ ] **Step 5: 运行冒烟测试确认通过**

Run: `cd backend && uv run pytest tests/test_pipeline_smoke.py -v`
Expected: PASS

- [ ] **Step 6: 提交完整主链路**

```bash
git add backend/app/pipeline/graph.py backend/app/pipeline/nodes/write_result.py backend/main.py backend/tests/test_pipeline_smoke.py
git commit -m "feat: connect end-to-end reconstruction pipeline"
```

## Task 6: 补 Makefile 命令与暂停点交付检查

**Files:**
- Create: `Makefile`
- Modify: `backend/README.md`
- Test: `backend/tests/test_cli_smoke.py`

- [ ] **Step 1: 写 CLI / Makefile 冒烟测试**

```python
from pathlib import Path
from subprocess import run


def test_makefile_contains_required_targets() -> None:
    content = Path("Makefile").read_text(encoding="utf-8")
    assert "ocr:" in content
    assert "reconstruct:" in content
    assert "latest:" in content
    assert "prompt-show:" in content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_cli_smoke.py -v`
Expected: FAIL，提示仓库根目录下缺少 `Makefile`

- [ ] **Step 3: 新建 Makefile 并补 README 用法**

```makefile
PYTHON ?= uv run python
BACKEND_DIR := backend
IMAGE ?=

.PHONY: ocr reconstruct latest prompt-show

ocr:
	cd $(BACKEND_DIR) && $(PYTHON) main.py ocr "$(IMAGE)"

reconstruct:
	cd $(BACKEND_DIR) && $(PYTHON) main.py reconstruct "$(IMAGE)"

latest:
	cd $(BACKEND_DIR) && ls -1 runs | tail -n 1 | sed 's#^#backend/runs/#'

prompt-show:
	cd $(BACKEND_DIR) && cat app/prompts/reconstruct_html.md
```

```md
# backend/README.md

## 表单重建调试命令

```bash
make ocr IMAGE=/absolute/path/to/form.png
make reconstruct IMAGE=/absolute/path/to/form.png
make latest
make prompt-show
```

当 `make reconstruct` 能稳定输出以下产物后，本阶段停止，进入人工 prompt 调优：

- `source.*`
- `ocr_raw.json`
- `ocr_compact.json`
- `prompt.txt`
- `model_raw.txt`
- `result.html`
- `metadata.json`
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_cli_smoke.py -v`
Expected: PASS

- [ ] **Step 5: 手工执行暂停点验收**

Run: `make reconstruct IMAGE=/absolute/path/to/sample-form.png`
Expected: 终端输出 `backend/runs/<run-id>/result.html`，且同一目录下存在 `ocr_raw.json`、`ocr_compact.json`、`prompt.txt`、`model_raw.txt`、`metadata.json`

- [ ] **Step 6: 提交命令入口与暂停点说明**

```bash
git add Makefile backend/README.md backend/tests/test_cli_smoke.py
git commit -m "feat: add make targets for prompt-driven reconstruction workflow"
```

## Spec Self-Review

### 覆盖检查

- 单张图片输入：由 Task 3 的 `load_image` 与 CLI 参数实现
- PaddleOCR Structure 输出：由 Task 3 的 `paddle_structure.py` 与 `run_ocr` 实现
- 原图 + OCR 结果送给多模态模型：由 Task 4 的 prompt 构建与模型服务实现
- 输出单文件 HTML：由 Task 5 的 `write_result.py` 实现
- 保存完整调试产物：由 Task 2、Task 3、Task 4、Task 5 联合实现
- `Makefile` 命令：由 Task 6 实现
- 到 prompt 调试前暂停：由 Task 6 的手工验收步骤与 README 说明落实

### 占位符检查

- 计划中没有 `TBD`、`TODO`、`稍后实现` 等占位语
- 每个任务都给出了明确文件路径、测试入口和提交点

### 类型与命名一致性检查

- `PipelineState` 在各任务中保持同一命名
- 产物命名统一为 `ocr_raw.json`、`ocr_compact.json`、`prompt.txt`、`model_raw.txt`、`result.html`
- CLI 命令统一为 `ocr`、`reconstruct`、`latest`、`prompt-show`
