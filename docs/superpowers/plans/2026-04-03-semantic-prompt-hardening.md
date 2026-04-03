# 语义 Prompt 收紧与长 OCR 拆分预案 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收紧语义抽取 prompt，使其优先稳定产出当前后端严格 `SemanticFormModel`，并补充长 OCR 输入的拆分策略说明。

**Architecture:** 保持现有单次 `raw_ocr_json + layout_json + image` 调用链不变，只通过 prompt 和调优文档约束模型行为。将长 OCR 拆分作为后续 LangGraph 编排能力的预案记录，不在本次直接实现自动拆分。

**Tech Stack:** Markdown prompt、README 文档、Pydantic 契约、OpenAI Responses 调用链

---

### Task 1: 收紧语义抽取 Prompt

**Files:**
- Modify: `backend/app/services/llm/prompts/semantic_enrich.md`

- [ ] **Step 1: 明确允许输出的顶层与子字段**

在 prompt 中显式列出 `SemanticFormModel` 允许的字段名、字段含义和最小要求，重点覆盖：

```text
form_meta.title
form_meta.document_type
form_meta.document_number
sections[].field_keys
sections[].order
sections[].section_type
fields[].kind
fields[].table_columns[].order
fields[].evidence[].source_id
fields[].evidence[].source_type
fields[].evidence[].bbox
fields[].evidence[].page
layout_hints.section_order
layout_hints.preferred_columns
layout_hints.section_spans
warnings[].code
warnings[].message
warnings[].severity
warnings[].related_field_keys
```

- [ ] **Step 2: 明确禁止模型输出漂移字段**

在 prompt 中加入禁止规则，明确不要输出本轮调优中已经出现的非契约字段：

```text
document_title
form_type
document_id
language
page_count
source_image_size
reading_order
table_ids
checkbox_region_ids
underline_fill_region_ids
layout_id
text
kind = "text"
```

- [ ] **Step 3: 加入保守抽取规则**

在 prompt 中增加“宁缺勿滥”的硬约束：

```text
- 不确定时允许 value 为 null
- 不确定时优先添加 warning，而不是发明字段或结构
- 没有几何信息时，只能依据 layout_json 中已有 bbox
- sections 与 fields 必须互相闭合引用
- array-table 必须补齐 table_columns 与行值
```

- [ ] **Step 4: 明确输出风格**

在 prompt 中强制：

```text
- 只返回 JSON
- 不要 Markdown 代码块
- 不要解释文字
- 不要返回 schema 以外的包裹层
```

### Task 2: 补充中文调优说明

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 增加“当前调优目标”说明**

在 README 的 prompt 调优部分补充中文说明，明确当前阶段目标是：

```text
先让模型稳定输出严格 SemanticFormModel，
而不是直接生成最终 Formily Schema。
```

- [ ] **Step 2: 增加“如何判断一次调优是否有效”说明**

补充面向开发者的判断标准：

```text
- output_json 是否存在
- 字段名是否与 semantic.py 契约一致
- kind 是否只使用允许枚举
- sections 是否补齐 field_keys/order/section_type
- evidence 是否补齐 source_id/source_type/bbox/page
```

- [ ] **Step 3: 增加“长 OCR 拆分策略预案”说明**

用中文写清楚：

```text
- 当前默认仍是单次请求
- 当 OCR 与 layout 规模增大时，需要评估拆分
- 拆分优先按 section 或 table 区块，而不是按纯文本长度均分
- 自动拆分更适合在 LangGraph 接入后实现
```

### Task 3: 自检文案一致性

**Files:**
- Modify: `backend/app/services/llm/prompts/semantic_enrich.md`
- Modify: `README.md`

- [ ] **Step 1: 对照 semantic 契约自检字段名**

逐项核对 [semantic.py](/home/Tiger/Documents/code/agent/paddle-win/backend/app/models/semantic.py) 中的模型字段，确保 prompt 和 README 中使用的字段名与代码完全一致。

- [ ] **Step 2: 确认文档表述与当前实现一致**

确保文档没有声称“已经自动拆分”或“已经接入 LangGraph 运行时”，只描述当前事实和后续预案。
