# 前端工作台说明

## 目录职责

`frontend/` 是基于 Next.js App Router 的表单重建对话工作台，负责：

- 让用户用图片路径和 OCR JSON 路径创建会话
- 显示聊天历史、当前版本摘要和错误信息
- 通过 iframe 预览后端返回的最新 HTML
- 优先展示会话的 `run_id` 与 `source_image_name`，作为调试和联调的主识别信息
- 支持发送修改消息和回退上一轮版本

## 环境准备

先复制环境变量示例：

```bash
cp .env.example .env.local
```

默认需要配置：

- `NEXT_PUBLIC_BACKEND_BASE_URL`：后端 API 基础地址，默认 `http://127.0.0.1:8000`

如果后端不是本机默认端口，请同步修改这个变量。

## 开发命令

启动本地开发服务器：

```bash
pnpm dev
```

默认访问地址是 `http://localhost:3000`。

## 测试与质量检查

运行组件测试：

```bash
pnpm test --run
```

运行 ESLint：

```bash
pnpm lint
```

执行生产构建检查：

```bash
pnpm build
```

## 联调建议

推荐与仓库根目录的后端命令配合使用：

```bash
make ocr IMAGE=/absolute/path/to/form.png
make api-dev
pnpm dev
```

在页面里创建会话时，需要填写：

- `image_path`：原始图片绝对路径
- `ocr_json_path`：OCR 生成的 `ocr_compact.json` 绝对路径

会话创建成功后，前端应优先使用后端返回的以下字段识别当前工作对象：

- `run_id`：对应 `backend/runs/<run-id>/` 调试产物目录
- `source_image_name`：当前表单源图文件名

也就是说，`image_path` 和 `ocr_json_path` 目前仍是过渡阶段的创建输入，但不再适合作为后续联调、截图和问题定位时的主契约。

只有当 OCR 本身有误时，才建议回到后端重跑 `make ocr`；否则应保持同一份 OCR JSON，专注验证多轮编辑效果。
