# 后端使用说明

## 目录职责

`backend/` 当前主要负责 workbench 编辑接口，同时保留少量历史 CLI 入口：
1. workbench 会话 API，与前端对话工作台联调
2. `ocr` / `reconstruct` 两个预留命令入口

当前默认运行产物目录是 `backend/data/jobs/<run-id>/`。如果你修改了 `ARTIFACT_ROOT` 或 `RUN_ROOT`，请按实际目录排查 OCR、prompt 和模型输出问题。

## 环境准备

### 1. 复制环境变量模板

```bash
cp .env.example .env
```

### 2. 配置关键变量

- `OPENAI_API_KEY`：必填
- `OPENAI_BASE_URL`：OpenAI 兼容接口地址，可留空
- `OPENAI_MODEL`：默认是 `gpt-4.1-mini`
- `ARTIFACT_ROOT` 或 `RUN_ROOT`：运行产物目录，相对路径以 `backend/` 为基准，默认是 `data/jobs`
- `WORKBENCH_INIT_PROMPT_PATH`：初始化会话 prompt 模板路径
- `WORKBENCH_EDIT_PROMPT_PATH`：多轮编辑 prompt 模板路径
- `WORKBENCH_MAX_VALIDATION_RETRIES`：模型返回结构不合法时的最大重试次数

## 常用命令

优先使用仓库根目录的 `Makefile`：

```bash
make latest
make api-dev
```

如果需要使用底层原始命令：

```bash
cd backend
uv run uvicorn app.server:create_app --factory --reload
uv run pytest -q
```

`make api-dev` 会启动 FastAPI 开发服务，默认监听 `http://127.0.0.1:8000`。

如果你需要检查当前保留的 CLI 入口，也可以执行：

```bash
make ocr IMAGE=/absolute/path/to/form.png
make reconstruct IMAGE=/absolute/path/to/form.png
```

这两个命令在当前提交中仍是占位实现，不应作为 workbench 工作流的前置步骤。

## workbench 会话接口

当前会话接口统一挂在 `/api/sessions`：

- `POST /api/sessions`：创建会话，上传图片文件 `image`
- `GET /api/sessions/{session_id}`：读取当前会话快照
- `POST /api/sessions/{session_id}/messages`：发送一条自然语言修改请求
- `POST /api/sessions/{session_id}/rollback`：回退到上一版

### 创建会话示例

```bash
curl -X POST http://127.0.0.1:8000/api/sessions \
  -F 'image=@/absolute/path/to/form.png'
```

成功后会返回会话快照，关键字段包括：

- `session_id`
- `version`
- `run_id`
- `source_image_name`
- `current_form_json`
- `current_html`
- `summary`
- `turns`

### 发送修改消息示例

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/<session-id>/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "请新增备注字段，并放在基础信息区域最后"
  }'
```

### 回退示例

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/<session-id>/rollback
```

## 推荐工作流

推荐按下面顺序执行：

1. 准备好表单图片文件
2. 启动 API：`make api-dev`
3. 让前端工作台上传图片创建会话
4. 在 workbench 中反复发送修改消息，并根据需要回退版本

如果只是调 prompt、换模型或比较会话编辑效果，可以直接复用已有 `backend/data/jobs/<run-id>/` 目录排查 `ocr_compact.json`、`prompt.txt` 和 `model_raw.txt`。

## 输入与输出

### 输入

- 单张图片文件
- `backend/app/prompts/workbench_init.md`
- `backend/app/prompts/workbench_edit.md`
- `backend/.env` 中的模型接口配置

### 输出

如果你已经通过其他链路生成了完整重建产物，单次运行目录下通常会有：

- `source.*`
- `ocr_raw.json`
- `ocr_compact.json`
- `prompt.txt`
- `model_raw.txt`
- `result.html`
- `metadata.json`

workbench API 自身返回的是会话快照 JSON，不会替代 `ARTIFACT_ROOT` 对应目录下的调试产物；默认就是 `backend/data/jobs/`。
