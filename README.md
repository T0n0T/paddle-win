# paddle-win

一个基于 PaddleOCR 表格识别与 OpenAI 语义增强的中文表单识别实验项目。

当前推荐工作流分为两步：

1. 先运行 PaddleOCR，导出原始 `ocr.json`
2. 再结合原图与 `ocr.json`，运行语义 prompt 调优 CLI

## 项目结构

- `backend/`：FastAPI 后端、OCR 与语义处理逻辑
- `frontend/`：前端操作台
- `ocr.json`：当前仓库中的一个 OCR 输出示例

## 后端环境变量配置

后端默认从 `backend/.env` 读取环境变量。

先根据示例文件创建：

```bash
cp backend/.env.example backend/.env
```

至少需要配置：

```env
OPENAI_API_KEY=your_openai_api_key_here
```

如果你使用代理网关、OpenAI 兼容服务或自建转发层，也可以配置：

```env
OPENAI_BASE_URL=https://api.openai.com/v1
```

可选配置项：

- `OPENAI_BASE_URL`：OpenAI 或 OpenAI 兼容接口的基础地址；直连官方接口时可留空
- `OPENAI_MODEL`：语义调优使用的模型名，默认是 `gpt-4.1-mini`
- `ARTIFACT_ROOT`：后端任务产物目录；相对路径以 `backend/` 为基准
- `ENABLE_DEV_ARTIFACTS`：设为 `true` 时保留更多开发期产物

示例文件见：

- [`backend/.env.example`](/home/Tiger/Documents/code/agent/paddle-win/backend/.env.example)

## 安装依赖

后端使用 `uv` 管理 Python 依赖。

首次使用建议执行：

```bash
cd backend
uv sync
```

说明：第一次真实运行 OCR 时，PaddleOCR 会自动下载多套官方模型，因此初始化会比较慢；模型缓存完成后，后续运行会快很多。

## 导出 OCR JSON

项目里提供了一个 OCR CLI，用于调用 PaddleOCR `TableRecognitionPipelineV2` 对单张图片做识别，并输出原始 OCR JSON。

在仓库根目录执行：

```bash
cd backend
uv run python -m app.services.ocr.paddle_table_v2_cli --image ../test.jpg --output ../ocr.json
```

参数说明：

- `--image`：输入图片路径
- `--output`：输出 JSON 路径，默认值为 `data/manual/ocr.json`

也可以直接使用根目录 `Makefile`：

```bash
make ocr IMAGE=test.jpg OCR=ocr.json
```

当前示例输出文件：

- [`ocr.json`](/home/Tiger/Documents/code/agent/paddle-win/ocr.json)

## Prompt 调优 CLI

生成 `ocr.json` 后，可以使用语义调优 CLI，结合原图、OCR 结果和 prompt 文件进行调优实验。

当前阶段的调优目标需要优先锁定为：

- 先让模型稳定输出当前后端严格 `SemanticFormModel`
- 暂时不追求让模型直接生成最终 Formily Schema

原因是当前系统设计里，Formily Schema 应由后端在语义模型稳定后做确定性编译；如果在 prompt 调优阶段直接追求最终 Formily 输出，容易把语义抽取问题、结构漂移问题和编译问题混在一起，导致调优方向失真。

当前推荐直接使用根目录 `Makefile`：

```bash
make semantic-tune \
  IMAGE=test.jpg \
  OCR=ocr.json \
  PROMPT=backend/app/services/llm/prompts/semantic_enrich.md \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.raw.json
```

默认行为：

- 默认跳过 `SemanticFormModel` 校验
- 直接保存模型原始响应
- 如果网关返回 SSE 流，会自动提取并拼接最终 `output_text`
- 如果最终文本本身是 JSON，还会额外生成 `output_json`

如果你想切回严格 schema 校验模式，可以显式传：

```bash
make semantic-tune \
  IMAGE=test.jpg \
  OCR=ocr.json \
  PROMPT=backend/app/services/llm/prompts/semantic_enrich.md \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.json \
  STRICT=1
```

参数说明：

- `--image`：原始图片路径
- `--ocr`：原始 OCR JSON 路径
- `--prompt`：prompt Markdown 文件路径
- `--output`：输出文件路径

如果要测试新的 prompt 版本，可以新建一个 Markdown 文件，然后通过 `--prompt` 指向它。

例如：

```bash
make semantic-tune \
  IMAGE=test.jpg \
  OCR=ocr.json \
  PROMPT=tmp/semantic_enrich.experiment.md \
  SEMANTIC_OUTPUT=tmp/semantic-result.experiment.raw.json
```

如果你已经拿到一份模型原始响应文件，希望在不重复请求大模型的前提下，仅做本地提取与严格 `SemanticFormModel` 校验，可以使用：

```bash
make semantic-validate-raw \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.raw.json \
  SEMANTIC_VALIDATED_OUTPUT=backend/data/manual/semantic-result.validated.json
```

这个模式会：

- 读取本地 raw 响应文件
- 优先提取其中的 `output_json`
- 如果没有 `output_json`，则尝试解析 `output_text`
- 在本地执行 `SemanticFormModel` 校验
- 将验证通过后的标准 JSON 写入 `--output`

这个模式不会再次请求大模型，适合反复检查 prompt 调优结果是否已经满足当前严格语义契约。

## 如何判断一次 Prompt 调优是否有效

在当前阶段，不建议只看“模型输出看起来是否更完整”，而应优先检查它是否更接近后端严格语义契约。

建议至少按下面几项判断：

- `output_json` 是否存在，且本身是合法 JSON
- 顶层是否只有 `form_meta`、`sections`、`fields`、`layout_hints`、`warnings`
- `form_meta` 是否使用当前契约字段名：
  - `title`
  - `document_type`
  - `document_number`
- `sections` 是否补齐：
  - `field_keys`
  - `order`
  - `section_type`
- `fields[].kind` 是否只使用允许枚举：
  - `string`
  - `datetime`
  - `textarea`
  - `boolean`
  - `array-table`
- `fields[].evidence[]` 是否补齐：
  - `source_id`
  - `source_type`
  - `bbox`
  - `page`
- `layout_hints` 是否使用当前契约字段：
  - `section_order`
  - `preferred_columns`
  - `section_spans`
- 顶层 `warnings` 是否是结构化对象数组，而不是纯字符串数组

如果一次输出只是“信息更多”，但字段名继续漂移、`kind` 继续越界、`evidence` 仍然缺 bbox，那么这次调优通常不算有效。

## 长 OCR 输入的拆分策略预案

当前默认策略仍然是：

- 单张图片
- 单次请求
- 一次性提交 `raw_ocr_json + layout_json + image`

但在 OCR 输出明显变大时，需要提前考虑是否要拆分任务，而不是无限制把全部内容继续塞进一次请求。

当前建议的拆分原则是：

- 优先按 section、表格区块、布局块拆分
- 不优先按纯文本长度平均切片

原因：

- 这个任务依赖 section 边界、表格结构和证据回指
- 如果只按 OCR 文本长度硬切，容易把一个 section 或同一张表拆散
- 一旦拆散，字段归属、`table_columns`、`evidence` 和最终合并都会明显变得不稳定

因此，后续如果要接入自动拆分，更推荐：

- 先基于 `layout_json` 判断是否超出单次请求的合适规模
- 超出后按 section / table region 生成局部任务
- 每个局部任务只负责输出局部语义结果
- 最后由后端统一做合并与校验

这部分更适合在 LangGraph 正式接入后实现，因为那时可以更自然地编排：

- 分块
- 局部抽取
- 局部重试
- 汇总合并
- 最终校验

在 LangGraph 接入前，建议先把单次 prompt 调优到能稳定贴合严格 `SemanticFormModel` 契约，再评估是否真的需要拆分。

## 最小调优闭环

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 OPENAI_API_KEY

cd backend
uv sync

uv run python -m app.services.ocr.paddle_table_v2_cli --image ../test.jpg --output ../ocr.json

cd ..
make semantic-tune \
  IMAGE=test.jpg \
  OCR=ocr.json \
  PROMPT=backend/app/services/llm/prompts/semantic_enrich.md \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.raw.json

make semantic-validate-raw \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.raw.json \
  SEMANTIC_VALIDATED_OUTPUT=backend/data/manual/semantic-result.validated.json
```

## Makefile 快捷命令

根目录提供了一个简化版 `Makefile`：

```bash
make help
```

常用命令：

- `make backend-dev`：启动后端服务
- `make backend-test`：运行后端 smoke test
- `make ocr IMAGE=test.jpg OCR=ocr.json`：导出 OCR JSON
- `make semantic-tune ...`：运行 prompt 调优，默认落盘原始响应
- `make semantic-validate-raw ...`：本地提取并校验 raw 响应，不重复请求大模型
- `STRICT=1`：给 `make semantic-tune` 增加严格 schema 校验模式
