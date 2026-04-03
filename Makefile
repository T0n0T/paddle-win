.PHONY: help backend-dev backend-test ocr semantic-tune semantic-validate-raw semantic-compile-formily semantic-to-formily

IMAGE ?= test.jpg
OCR ?= ocr.json
PROMPT ?= backend/app/services/llm/prompts/semantic_enrich.md
SEMANTIC_OUTPUT ?= backend/data/manual/semantic-result.raw.json
SEMANTIC_VALIDATED_OUTPUT ?= backend/data/manual/semantic-result.validated.json
FORMILY_OUTPUT ?= backend/data/manual/semantic-result.formily.json
STRICT ?= 0

help:
	@echo "可用命令："
	@echo "  make backend-dev              启动后端服务"
	@echo "  make backend-test             运行后端 smoke test"
	@echo "  make ocr IMAGE=test.jpg       导出 OCR JSON"
	@echo "  make semantic-tune            运行 prompt 调优"
	@echo "  make semantic-validate-raw    本地提取并校验 raw 响应"
	@echo "  make semantic-compile-formily 从语义 JSON 编译 Formily"
	@echo "  make semantic-to-formily      从语义 JSON 编译 Formily（简写）"
	@echo ""
	@echo "可覆盖变量："
	@echo "  IMAGE=$(IMAGE)"
	@echo "  OCR=$(OCR)"
	@echo "  PROMPT=$(PROMPT)"
	@echo "  SEMANTIC_OUTPUT=$(SEMANTIC_OUTPUT)"
	@echo "  SEMANTIC_VALIDATED_OUTPUT=$(SEMANTIC_VALIDATED_OUTPUT)"
	@echo "  FORMILY_OUTPUT=$(FORMILY_OUTPUT)"
	@echo "  STRICT=$(STRICT)"

backend-dev:
	uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011

backend-test:
	uv run --project backend pytest backend/tests/test_app_smoke.py -v

ocr:
	cd backend && uv run python -m app.services.ocr.paddle_table_v2_cli --image ../$(IMAGE) --output ../$(OCR)

semantic-tune:
	cd backend && uv run python -m app.services.llm.semantic_enricher_cli --image ../$(IMAGE) --ocr ../$(OCR) --prompt ../$(PROMPT) --output ../$(SEMANTIC_OUTPUT) $(if $(filter 1 true TRUE yes YES,$(STRICT)),,--raw-response-output)

semantic-validate-raw:
	cd backend && uv run python -m app.services.llm.semantic_enricher_cli --from-raw-response ../$(SEMANTIC_OUTPUT) --output ../$(SEMANTIC_VALIDATED_OUTPUT)

semantic-compile-formily:
	cd backend && uv run python -m app.services.compiler.formily_compiler_cli --semantic ../$(SEMANTIC_VALIDATED_OUTPUT) --output ../$(FORMILY_OUTPUT)

semantic-to-formily: semantic-compile-formily
