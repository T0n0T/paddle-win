# 表单重建与对话编辑一体化工作台设计文档

## 1. 背景与目标

当前项目已经有两条独立能力：

- 一条后端重建链路：输入图片，运行 OCR、拼接 prompt、调用模型生成 HTML，并写入 `backend/runs/<run-id>/`
- 一条前后端 workbench 链路：基于已有 `image_path + ocr_json_path` 创建会话，随后通过多轮对话编辑 `form_json + html`

这两条链路的边界对开发调试有帮助，但不是最终用户应面对的形态。最终产品形态应当收敛为：

1. 用户在前端上传一张表单图片
2. 后端同步完成首轮 `OCR + LLM 重建`
3. 前端拿到初始会话快照并进入工作台
4. 用户继续通过自然语言做多轮编辑

本次设计的目标是把“首轮重建”和“后续对话编辑”合并为一条一致的产品流程，同时保留后端调试产物与最小 CLI 入口。

## 2. 范围

### 2.1 本阶段范围内

- 前端创建会话时改为上传图片文件，不再手工输入路径
- 后端 `POST /api/sessions` 同步执行：
  - 保存原图
  - 运行 OCR
  - 生成首轮 `form_json + html + change_summary`
  - 写入 `backend/runs/<run-id>/`
  - 创建会话并返回 `SessionSnapshot`
- 后续编辑仍使用现有对话式 workbench
- 前端仍采用经典双栏布局
- 后端保留最小 CLI 作为开发调试入口

### 2.2 本阶段范围外

- 异步任务队列
- 数据库存储
- 多用户协作
- 拖拽式编辑器
- 像素级版面 DSL
- LangGraph 主流程编排

## 3. 用户成功标准

以下条件全部满足时，视为本阶段目标完成：

1. 用户只需上传一张图片即可创建编辑会话
2. 创建会话时无需提供 `ocr_json_path`
3. 后端创建会话时会自动完成 OCR 和首轮表单重建
4. 前端进入工作台后，可继续通过自然语言修改表单
5. 后端继续写出 `backend/runs/<run-id>/` 调试产物
6. 后续编辑、回退、历史记录能力不退化

## 4. 总体方案

本次采用“同步 bootstrap + 会话编辑”的两段式方案：

- 第一段是初始化 bootstrap
  - 输入：上传图片
  - 输出：首轮 `form_json + html + change_summary`，以及调试产物目录
- 第二段是会话编辑
  - 输入：现有会话状态 + 用户自然语言指令
  - 输出：更新后的 `form_json + html + change_summary`

前端只看到一个统一入口，但后端内部明确拆成两个职责层：

- `WorkbenchBootstrapService`
- `WorkbenchService`

这样可以避免把 OCR、首轮重建、会话编辑全部揉进一个 service，同时为未来把 bootstrap 替换成 LangGraph 或异步任务保留干净边界。

## 5. 架构设计

### 5.1 `WorkbenchBootstrapService`

职责：

- 接收上传的图片文件
- 生成 `run_id`
- 将图片写入 `backend/runs/<run-id>/source.<ext>`
- 运行 OCR
- 写入 `ocr_raw.json` 与 `ocr_compact.json`
- 读取初始化 prompt 模板
- 调用模型生成首轮 `form_json + html + change_summary`
- 写入 `prompt.txt`、`model_raw.txt`、`result.html`、`metadata.json`
- 返回创建会话所需的初始状态

它是“图片 -> 首轮会话状态”的唯一入口。

### 5.2 `WorkbenchService`

职责：

- 作为会话创建的唯一应用层入口
- `create_session` 时调用 bootstrap 服务
- 将 bootstrap 返回的初始状态写入会话存储
- `send_message` 时组织多轮编辑 prompt
- `rollback` 时恢复到上一轮状态

约束：

- router 不直接调用 `WorkbenchBootstrapService`
- router 只调用 `WorkbenchService.create_session`
- `WorkbenchBootstrapService` 只作为 `WorkbenchService` 的内部依赖

这样可以确保创建入口唯一，避免 API 层、bootstrap 层和 store 层各自重复处理错误与状态写入。

### 5.3 前端工作台

职责保持不变，但创建区改成文件上传模式：

- 左栏：
  - 文件选择器
  - 创建状态提示
  - 聊天历史
  - 修改摘要
  - 输入框
- 右栏：
  - HTML 预览
  - 当前版本
  - 回退操作

### 5.4 最小 CLI

CLI 不再定义产品主流程，只保留后端调试入口：

- `make ocr IMAGE=...`
- `make reconstruct IMAGE=...`

`reconstruct-from-ocr` 可以继续保留给开发排查，但不应再作为 README 的主推荐路径。

## 6. 状态模型

### 6.1 `form_json`

仍作为会话内的语义真相，承载：

- 标题
- 描述
- 分区
- 字段
- 粗粒度布局提示

它不是 OCR 结果，也不是像素级布局 DSL。

### 6.2 `html`

仍作为当前会话下的直接预览结果，用于：

- 前端即时预览
- 版面类指令上下文
- 回退后的可视化结果

### 6.3 `change_summary`

每轮最少包含：

- `user_intent`
- `applied`
- `warnings`
- `unresolved`
- `touched_field_ids`

### 6.4 会话内部状态

后端会话内部建议至少保存：

- `session_id`
- `version`
- `run_id`
- `source_image_path`
- `ocr_json_path`
- `current_form_json`
- `current_html`
- `summary`
- `turns`

其中 `source_image_path` 和 `ocr_json_path` 属于后端内部字段，不需要对前端公开。

## 7. API 设计

### 7.1 `POST /api/sessions`

请求格式改为 `multipart/form-data`。

输入：

- `image`: 上传图片文件

处理流程：

1. 校验上传文件
2. router 调用 `WorkbenchService.create_session`
3. `WorkbenchService.create_session` 调用 `WorkbenchBootstrapService`
4. bootstrap 生成首轮会话状态
5. `WorkbenchService` 将初始状态写入会话存储
6. 返回 `SessionSnapshot`

### 7.2 `GET /api/sessions/{session_id}`

保持现状，用于刷新恢复。

### 7.3 `POST /api/sessions/{session_id}/messages`

保持现状，用于后续自然语言编辑。

### 7.4 `POST /api/sessions/{session_id}/rollback`

保持现状，用于回退上一轮。

## 8. API 响应模型调整

`SessionSnapshot` 建议从对前端暴露路径字段，改为暴露可展示但不泄露服务端路径的字段。

建议包含：

- `session_id`
- `version`
- `source_image_name`
- `run_id`
- `current_form_json`
- `current_html`
- `summary`
- `turns`

建议不向前端暴露：

- `source_image_path`
- `ocr_json_path`
- `artifact_dir`

原因：

- 前端不应依赖服务端文件系统路径
- `run_id` 已足够关联后端调试产物
- 后续若存储位置变化，前端模型无需调整

该约束必须同时适用于四个返回 `SessionSnapshot` 的接口：

- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/messages`
- `POST /api/sessions/{session_id}/rollback`

## 9. 前端交互设计

### 9.1 创建区

创建区由两个路径输入框改为单个文件选择器：

- 选择表单图片
- 显示已选文件名
- 点击“创建会话”

按钮禁用条件：

- 未选择文件
- 正在提交

### 9.2 创建状态

前端至少区分三种状态：

- `idle`
- `submitting`
- `error`

`submitting` 文案建议明确为：

- “正在分析图片并重建表单...”

不要只显示“创建中...”，否则用户难以理解当前耗时来自哪里。

### 9.3 工作台进入条件

只有在 `POST /api/sessions` 成功返回后，前端才进入正常会话态。

后续聊天区、预览区、回退区保持现有交互，不再关心 OCR 输入。

## 10. 调试产物策略

创建会话时仍然保留 `backend/runs/<run-id>/` 目录，至少写出：

- `source.*`
- `ocr_raw.json`
- `ocr_compact.json`
- `prompt.txt`
- `model_raw.txt`
- `result.html`
- `metadata.json`

其中 `metadata.json` 必须能够对齐“首轮会话真相”，至少包含：

- `run_id`
- `source_image_name`
- `form_json`
- `change_summary`
- 关键运行元信息

这样既满足产品端“只传图片”的简洁体验，又不牺牲后端排障能力。

## 11. 错误处理

### 11.1 上传错误

包括：

- 未传文件
- 空文件
- 非图片文件

处理：

- 返回 `422`
- 前端在创建区就地展示错误

### 11.2 OCR 阶段失败

包括：

- OCR 服务不可用
- OCR 输出格式异常
- runs 写入失败

处理：

- 返回 `500`
- 文案为“初始化失败：OCR 处理未完成”
- 已生成的 `run_id` 和中间产物尽量保留

### 11.3 首轮 LLM 重建失败

包括：

- API key 缺失
- 模型请求失败
- 模型输出结构不合法

处理：

- 返回 `500`
- 文案为“初始化失败：首轮表单重建未完成”
- 尽量保留 OCR 与 prompt 调试产物

约定：

- `422` 只用于上传输入错误
- OCR、模型请求失败、模型输出结构非法、产物写入失败都视为服务端初始化失败，统一返回 `500`
- 响应体应返回稳定、可展示的 `detail`

### 11.4 编辑阶段失败

保持现有 workbench 错误语义：

- `404`：会话不存在
- `422`：消息或模型输出非法
- `500`：后端异常

## 12. LangGraph 接入策略

本阶段仍不建议让 LangGraph 进入主链路。

但应保留清晰替换边界：

- `WorkbenchBootstrapService`
  未来可替换为 LangGraph 的初始化图
- `WorkbenchService.send_message`
  未来可替换为 LangGraph 的编辑图

当前阶段先用普通 service 跑通同步链路，后续如需要：

- 工具调用
- 条件分支
- 自动修复
- 审批流

再迁移到 LangGraph。

## 13. 实施顺序

### 13.1 第一步：引入 bootstrap 服务

- 抽出共享的初始化链路
- 复用现有 OCR 与重建能力
- 写入 `backend/runs/<run-id>/`

### 13.2 第二步：让 `WorkbenchService.create_session` 接入 bootstrap

- 保持 router 入口不变
- 先在应用层打通“同步初始化 -> 写入会话”
- 确认创建入口唯一

### 13.3 第三步：更新会话创建接口与前端 API

- `POST /api/sessions` 改为接收上传文件
- 更新请求模型
- 前端改为 `FormData`

### 13.4 第四步：调整会话模型

- 对前端移除路径字段
- 增加 `source_image_name` 与 `run_id`
- 后端内部保留调试路径

### 13.5 第五步：更新前端创建区

- 文本路径输入改成文件选择器
- 使用 `FormData` 创建会话
- 增加创建中的状态提示与错误提示

### 13.6 第六步：保留最小 CLI

- 保证 `ocr`、`reconstruct` 仍可用于后端调试
- 将 README 主流程改成“上传图片创建会话”

## 14. 测试策略

### 14.1 后端单元测试

- bootstrap 服务成功生成初始会话状态
- OCR 失败路径
- 首轮模型输出非法路径
- 调试产物写出验证

### 14.2 后端 API 测试

- `multipart/form-data` 上传成功创建会话
- 缺失文件返回 `422`
- 非法文件返回预期错误
- 创建失败时返回明确错误消息
- 四个 `SessionSnapshot` 接口都不再暴露 `source_image_path` 与 `ocr_json_path`

### 14.3 前端组件测试

- 未选文件时按钮禁用
- 选择文件后可提交
- 创建会话使用 `FormData`
- 错误信息正确渲染

### 14.4 回归测试

- 多轮消息编辑仍可用
- 回退仍可用
- 预览仍可刷新
- 本地双栏工作台布局不退化
- 旧路径字段在前端类型、API 解析和测试中彻底下线

## 15. 决策结论

本阶段的正式产品形态定为：

- 前端：用户上传图片创建会话
- 后端：同步完成 `OCR + 首轮 LLM 重建`
- 工作台：继续基于 `form_json + html + change_summary` 做多轮对话编辑
- 调试：继续保留 `backend/runs/<run-id>/`
- CLI：仅作为后端调试入口，收缩为最小能力

这是当前复杂度最低、边界最清晰、又不阻断后续 LangGraph 演进的方案。
