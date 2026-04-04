# paddle-win

## 项目简介

`paddle-win` 当前已提交的能力主要集中在表单编辑 workbench：

1. 后端 workbench 会话接口：接收已有的表单图片路径与 OCR JSON 路径，初始化编辑会话，维护 `form_json`、HTML 预览和变更摘要。
2. 前端对话工作台：基于后端会话 API 创建编辑会话，支持多轮自然语言修改、预览当前 HTML、回退上一轮版本。

当前推荐的使用方式是先准备稳定的 OCR JSON，再进入 workbench 做会话化联调。ocr_compact.json 需要由仓库外部链路预先生成；仓库里仍保留 `make ocr` / `make reconstruct` 入口，但这两条 CLI 在当前提交中还不是完整实现。

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

- `make latest`：如果你的 `backend/runs/` 下已经有历史产物，用它查看最近一次运行目录
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

1. 准备好原始表单图片绝对路径和已有的 `ocr_compact.json`
   `ocr_compact.json` 需要由仓库外部链路预先生成，本仓库当前不提供受支持的生成命令
2. 启动后端 API：`make api-dev`
3. 启动前端工作台：`make frontend-dev`
4. 在工作台里创建会话，输入 `image_path` 和 `ocr_json_path`
5. 通过自然语言发送修改请求，观察 HTML 预览和回退结果

示例：

```bash
make api-dev
make frontend-dev
```

创建会话时请填写：

- `image_path`：原始表单图片绝对路径
- `ocr_json_path`：仓库外部链路预先生成的 `ocr_compact.json` 绝对路径

这样做可以把 OCR 质量问题和 prompt / 多轮编辑问题分开分析。当前 workbench 不要求 OCR 一定由本仓库生成，只要求你提供可用的 JSON 文件。

## 调试产物

如果你已经通过别的链路生成过 `backend/runs/<run-id>/` 产物目录，里面通常会有：

- `source.*`
- `ocr_raw.json`
- `ocr_compact.json`
- `prompt.txt`
- `model_raw.txt`
- `result.html`
- `metadata.json`

其中 `ocr_compact.json` 是 workbench 创建会话时最关键的输入，建议先人工确认其质量，再把它作为后续联调基线。当前这份输入需要由仓库外部链路预先生成。

## 相关文档

- 后端接口与运行说明见 [`backend/README.md`](./backend/README.md)
- 前端工作台说明见 [`frontend/README.md`](./frontend/README.md)
- 后端环境变量示例见 [`backend/.env.example`](./backend/.env.example)
- 前端环境变量示例见 [`frontend/.env.example`](./frontend/.env.example)
