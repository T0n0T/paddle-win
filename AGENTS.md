# AGENTS

## 协作约定

- 本项目新增或修改的文档统一使用中文。
- README、设计文档、计划文档、使用说明、注释性说明文档，默认都使用中文编写。
- 如果必须引用英文原文，优先补充中文说明，避免只保留英文内容。

## 文档约定

- 根目录 `README.md` 作为项目入口说明，优先维护这里。
- 面向开发者的操作说明应尽量写清命令、输入文件、输出文件和依赖前提。
- 涉及 prompt 调优、OCR 产物、环境变量配置时，优先补充可直接执行的命令示例。
- 如果项目存在 `Makefile` 或脚本入口，文档应优先记录快捷命令，同时保留底层原始命令。

相关入口：

- [`README.md`](/home/Tiger/Documents/code/agent/paddle-win/README.md)
- [`backend/.env.example`](/home/Tiger/Documents/code/agent/paddle-win/backend/.env.example)
