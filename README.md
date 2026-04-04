# paddle-win

## 项目简介

`paddle-win` 当前已提交的能力主要集中在表单编辑 workbench：

1. 后端 workbench 会话接口：接收上传的表单图片，同步完成 OCR、首轮 HTML 重建并初始化编辑会话，维护 `form_json`、HTML 预览和变更摘要。
2. 前端对话工作台：基于后端会话 API 创建编辑会话，支持多轮自然语言修改、预览当前 HTML、回退上一轮版本。

当前推荐的使用方式是直接上传表单图片进入 workbench 做会话化联调。仓库里仍保留 `make ocr` / `make reconstruct` 入口，但这两条 CLI 在当前提交中还不是完整实现。

## 环境准备

### 依赖

- Python 3.13
- `uv`
- Node.js 20+
- `pnpm`
- 可用的 OpenAI 兼容多模态接口

### 环境变量

后端：

```bash
cp backend/.env.example backend/.env
```

前端：

```bash
cp frontend/.env.example frontend/.env.local
```

至少需要检查这些变量：

- `OPENAI_API_KEY`：模型接口密钥
- `OPENAI_BASE_URL`：OpenAI 兼容接口地址，直连官方可留空
- `OPENAI_MODEL`：多模态模型名
- `ARTIFACT_ROOT`：后端产物目录，当前默认是 `backend/data/jobs`
- `WORKBENCH_INIT_PROMPT_PATH`：初始化会话 prompt 模板路径
- `WORKBENCH_EDIT_PROMPT_PATH`：多轮编辑 prompt 模板路径
- `WORKBENCH_MAX_VALIDATION_RETRIES`：模型输出校验失败时的重试次数
- `NEXT_PUBLIC_BACKEND_BASE_URL`：前端请求后端 API 的地址，默认 `http://127.0.0.1:8000`

## 常用命令

### 运行 workbench

```bash
make latest
make api-dev
make frontend-dev
```

- `make latest`：查看当前 `ARTIFACT_ROOT` 下最近一次产物目录；默认对应 `backend/data/jobs/`
- `make api-dev` 会在 `http://127.0.0.1:8000` 启动 FastAPI 会话接口
- `make frontend-dev` 会在 `http://localhost:3000` 启动前端 workbench

如果你需要试验仓库中预留的 CLI 入口，也可以执行：

```bash
make ocr IMAGE=/absolute/path/to/form.png
make reconstruct IMAGE=/absolute/path/to/form.png
```

这两条命令当前仍处于占位阶段，不作为 workbench 联调主流程的一部分。

## 推荐联调流程

推荐按下面顺序操作：

1. 准备好原始表单图片文件
2. 启动后端 API：`make api-dev`
3. 启动前端工作台：`make frontend-dev`
4. 在工作台里上传图片并创建会话
5. 通过自然语言发送修改请求，观察 HTML 预览和回退结果

示例：

```bash
make api-dev
make frontend-dev
```

创建会话时只需要选择图片文件。后端会在创建阶段自动完成 OCR、首轮 HTML 重建和调试产物写出。

## 调试产物

如果你已经通过 workbench 或其他链路生成过 `backend/data/jobs/<run-id>/` 产物目录，里面通常会有：

- `source.*`
- `ocr_raw.json`
- `ocr_compact.json`
- `prompt.txt`
- `model_raw.txt`
- `result.html`
- `metadata.json`

其中 `ocr_compact.json` 是后端创建会话时自动生成的关键中间产物，建议在需要排查 OCR 质量时优先查看这份文件。

## 相关文档

- 后端接口与运行说明见 [`backend/README.md`](./backend/README.md)
- 前端工作台说明见 [`frontend/README.md`](./frontend/README.md)
- 后端环境变量示例见 [`backend/.env.example`](./backend/.env.example)
- 前端环境变量示例见 [`frontend/.env.example`](./frontend/.env.example)
