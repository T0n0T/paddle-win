PYTHON ?= uv run python
BACKEND_DIR := backend
FRONTEND_DIR := frontend
IMAGE ?=

.PHONY: ocr reconstruct latest api-dev frontend-dev

ocr:
	cd $(BACKEND_DIR) && $(PYTHON) main.py ocr "$(IMAGE)"

reconstruct:
	cd $(BACKEND_DIR) && $(PYTHON) main.py reconstruct "$(IMAGE)"

latest:
	cd $(BACKEND_DIR) && if [ -d runs ]; then find runs -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1 | sed 's#^#$(BACKEND_DIR)/#'; fi

api-dev:
	cd $(BACKEND_DIR) && uv run uvicorn app.server:create_app --factory --reload

frontend-dev:
	cd $(FRONTEND_DIR) && pnpm dev
