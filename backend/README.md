# Backend

后端目录包含 FastAPI 服务、OCR 管线、语义增强逻辑以及相关测试。

更完整的项目说明请优先查看根目录文档：

- [`README.md`](/home/Tiger/Documents/code/agent/paddle-win/README.md)

## 本地启动

在仓库根目录执行：

```bash
uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
```

启动后可访问：

- `http://127.0.0.1:8011`

## 环境变量

后端默认读取：

- `backend/.env`

初始化方式：

```bash
cp backend/.env.example backend/.env
```

至少需要填写：

```env
OPENAI_API_KEY=your_openai_api_key_here
```

如果需要使用代理网关或兼容 OpenAI 协议的服务，也可以配置：

```env
OPENAI_BASE_URL=https://api.openai.com/v1
```

示例文件：

- [`backend/.env.example`](/home/Tiger/Documents/code/agent/paddle-win/backend/.env.example)

## 常用命令

导出 OCR JSON：

```bash
cd backend
uv run python -m app.services.ocr.paddle_table_v2_cli --image ../test.jpg --output ../ocr.json
```

或在仓库根目录执行：

```bash
make ocr IMAGE=test.jpg OCR=ocr.json
```

运行 prompt 调优：

```bash
make semantic-tune \
  IMAGE=test.jpg \
  OCR=ocr.json \
  PROMPT=backend/app/services/llm/prompts/semantic_enrich.md \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.raw.json
```

或在仓库根目录执行：

```bash
make semantic-tune \
  IMAGE=test.jpg \
  OCR=ocr.json \
  PROMPT=backend/app/services/llm/prompts/semantic_enrich.md \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.raw.json
```

如果你想启用严格 `SemanticFormModel` 校验：

```bash
make semantic-tune \
  IMAGE=test.jpg \
  OCR=ocr.json \
  PROMPT=backend/app/services/llm/prompts/semantic_enrich.md \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.json \
  STRICT=1
```

如果你已经拿到一份原始模型响应文件，希望不重复请求大模型、只在本地提取并验证是否可转换为 `SemanticFormModel`，可以执行：

```bash
make semantic-validate-raw \
  SEMANTIC_OUTPUT=backend/data/manual/semantic-result.raw.json \
  SEMANTIC_VALIDATED_OUTPUT=backend/data/manual/semantic-result.validated.json
```

这个模式会优先读取 raw 文件中的 `output_json`，如果没有则回退解析 `output_text`，然后在本地执行严格 `SemanticFormModel` 校验，并把验证通过后的标准 JSON 写到 `--output`。

如果你已经有一份通过严格校验的语义 JSON，希望进一步编译成前端可直接消费的 Formily Schema，可以执行：

```bash
make semantic-compile-formily \
  SEMANTIC_VALIDATED_OUTPUT=backend/data/manual/semantic-result.validated.json \
  FORMILY_OUTPUT=backend/data/manual/semantic-result.formily.json
```

也可以使用更短的别名命令：

```bash
make semantic-to-formily \
  SEMANTIC_VALIDATED_OUTPUT=backend/data/manual/semantic-result.validated.json \
  FORMILY_OUTPUT=backend/data/manual/semantic-result.formily.json
```

这个模式要求输入文件本身就是 `SemanticFormModel` 结构，而不是 OpenAI raw response 包裹格式。
如果你手头文件实际上已经是语义 JSON，只是文件名仍然叫 `*.raw.json`，可以先重命名，或者直接把它传给编译 CLI：

```bash
cd backend
uv run python -m app.services.compiler.formily_compiler_cli \
  --semantic data/manual/semantic-result.raw.json \
  --output data/manual/semantic-result.formily.json
```

## 测试

运行 smoke test：

```bash
uv run --project backend pytest backend/tests/test_app_smoke.py -v
```

运行新增 OCR CLI 测试：

```bash
uv run --project backend pytest backend/tests/services/test_paddle_table_v2_cli.py -v
```
