# Frontend

前端是一个基于 Next.js 的轻量操作台，用于承接图片上传、任务轮询与结果展示。

更完整的项目说明请优先查看根目录文档：

- [`README.md`](/home/Tiger/Documents/code/agent/paddle-win/README.md)

## 本地开发

在 `frontend/` 目录执行：

```bash
pnpm dev
```

默认访问地址：

- `http://localhost:3000`

## 常用命令

安装依赖：

```bash
pnpm install
```

启动开发服务器：

```bash
pnpm dev
```

构建生产版本：

```bash
pnpm build
```

## 说明

- 页面入口通常在 `app/page.tsx`
- 全局样式位于 `app/globals.css`
- 如果需要联调后端，请同时启动 `backend/` 中的 FastAPI 服务
