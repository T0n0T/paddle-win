# 后端骨架说明

这里是 Task 1 的后端骨架入口目录，用于承载命令行入口、基础配置和后续流水线实现。

当前可用的最小验证命令：

```bash
cd backend
uv run pytest tests/test_config_smoke.py -v
```

配置示例见 [`./.env.example`](./.env.example)，实际运行时默认读取 `backend/.env`。
