from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import create_sessions_router
from app.config import BACKEND_ROOT, Settings
from app.services.multimodal_llm import MultimodalLLMService
from app.workbench import InMemorySessionStore, WorkbenchService


class FakeWorkbenchLLMService:
    def generate_text(self, image_path: Path, prompt: str) -> str:
        del image_path
        if "当前表单 JSON:" not in prompt:
            return (
                '{"form_json":{"title":"客户登记表","sections":[{"id":"basic","title":"基础信息"}],'
                '"fields":[{"id":"name","section_id":"basic","label":"姓名","type":"text","required":true}]},'
                '"html":"<form>v1</form>",'
            '"change_summary":{"user_intent":"初始化","applied":["生成首版"],"warnings":[],'
            '"unresolved":[],"touched_field_ids":[]}}'
            )
        return (
            '{"form_json":{"title":"客户登记表 v2","sections":[{"id":"basic","title":"基础信息"}],'
            '"fields":[{"id":"name","section_id":"basic","label":"姓名","type":"text","required":true},'
            '{"id":"remark","section_id":"basic","label":"备注","type":"textarea","required":false}]},'
            '"html":"<form>v2</form>",'
            '"change_summary":{"user_intent":"新增备注","applied":["新增备注字段"],"warnings":[],'
            '"unresolved":[],"touched_field_ids":["remark"]}}'
        )


LOCAL_DEV_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def create_app(*, fake_mode: bool = False, settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    init_prompt_path = _resolve_backend_path(app_settings.workbench_init_prompt_path)
    edit_prompt_path = _resolve_backend_path(app_settings.workbench_edit_prompt_path)
    llm_service = (
        FakeWorkbenchLLMService()
        if fake_mode
        else MultimodalLLMService(
            api_key=app_settings.openai_api_key,
            model=app_settings.openai_model,
            base_url=app_settings.openai_base_url,
        )
    )
    service = WorkbenchService(
        store=InMemorySessionStore(),
        llm_service=llm_service,
        init_prompt_path=init_prompt_path,
        edit_prompt_path=edit_prompt_path,
        max_validation_retries=app_settings.workbench_max_validation_retries,
    )

    app = FastAPI(title="Paddle Win Backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_DEV_CORS_ORIGINS),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(create_sessions_router(service))
    return app


def _resolve_backend_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return BACKEND_ROOT / path
