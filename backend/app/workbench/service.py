from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.workbench.models import (
    ChangeSummary,
    CreateSessionRequest,
    EditMessageRequest,
    FormDocument,
    SessionSnapshot,
)
from app.workbench.store import InMemorySessionStore


class InvalidPayloadError(ValueError):
    pass


class SessionNotFoundError(LookupError):
    pass


class WorkbenchService:
    def __init__(
        self,
        store: InMemorySessionStore,
        llm_service: Any,
        init_prompt_path: Path,
        edit_prompt_path: Path,
        max_validation_retries: int = 0,
    ) -> None:
        self.store = store
        self.llm_service = llm_service
        self.init_prompt_path = init_prompt_path
        self.edit_prompt_path = edit_prompt_path
        self.max_validation_retries = max_validation_retries

    def create_session(self, request: CreateSessionRequest) -> SessionSnapshot:
        prompt = self._render_init_prompt(
            image_path=request.image_path,
            ocr_json_path=request.ocr_json_path,
        )
        form_document, html, summary = self._generate_validated_response(
            image_path=request.image_path,
            prompt=prompt,
        )
        return self.store.create(
            image_path=request.image_path,
            ocr_json_path=request.ocr_json_path,
            form_document=form_document,
            html=html,
            summary=summary,
        )

    def send_message(self, session_id: str, request: EditMessageRequest) -> SessionSnapshot:
        session = self.get_session(session_id)
        prompt = self._render_edit_prompt(session=session, user_message=request.message)
        form_document, html, summary = self._generate_validated_response(
            image_path=session.image_path,
            prompt=prompt,
        )
        try:
            return self.store.append_turn(
                session_id=session_id,
                user_message=request.message,
                assistant_message=self._assistant_message(summary),
                form_document=form_document,
                html=html,
                summary=summary,
            )
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def get_session(self, session_id: str) -> SessionSnapshot:
        try:
            return self.store.get(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def rollback(self, session_id: str) -> SessionSnapshot:
        try:
            return self.store.rollback(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def _generate_validated_response(
        self,
        image_path: Path,
        prompt: str,
    ) -> tuple[FormDocument, str, ChangeSummary]:
        attempts = self.max_validation_retries + 1
        last_error: InvalidPayloadError | None = None
        for _ in range(attempts):
            response_text = self.llm_service.generate_text(image_path=image_path, prompt=prompt)
            try:
                payload = self._parse_payload(response_text)
                form_document = FormDocument.model_validate(payload["form_json"])
                summary = ChangeSummary.model_validate(payload["change_summary"])
                html = payload["html"]
                if not isinstance(html, str) or not html.strip():
                    raise InvalidPayloadError("html must be a non-empty string")
                return form_document, html, summary
            except (ValidationError, InvalidPayloadError) as exc:
                last_error = InvalidPayloadError(str(exc))

        if last_error is None:
            raise InvalidPayloadError("model payload validation failed")
        raise last_error

    def _parse_payload(self, response_text: str) -> dict[str, Any]:
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise InvalidPayloadError("model response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise InvalidPayloadError("model response must be a JSON object")
        required_keys = {"form_json", "html", "change_summary"}
        missing_keys = sorted(required_keys - payload.keys())
        if missing_keys:
            raise InvalidPayloadError(
                f"model response missing required keys: {', '.join(missing_keys)}"
            )
        return payload

    def _render_init_prompt(self, image_path: Path, ocr_json_path: Path) -> str:
        ocr_json = ocr_json_path.read_text(encoding="utf-8")
        return self._render_prompt(
            self.init_prompt_path,
            {
                "IMAGE_PATH": str(image_path),
                "OCR_JSON_PATH": str(ocr_json_path),
                "OCR_JSON": ocr_json,
            },
        )

    def _render_edit_prompt(self, session: SessionSnapshot, user_message: str) -> str:
        return self._render_prompt(
            self.edit_prompt_path,
            {
                "SESSION_ID": session.session_id,
                "VERSION": str(session.version),
                "USER_MESSAGE": user_message,
                "CURRENT_FORM_JSON": session.current_form_json.model_dump_json(),
                "CURRENT_HTML": session.current_html,
                "CURRENT_CHANGE_SUMMARY": session.summary.model_dump_json(),
            },
        )

    def _render_prompt(self, path: Path, variables: dict[str, str]) -> str:
        prompt = path.read_text(encoding="utf-8")
        return re.sub(
            r"\{\{([A-Z0-9_]+)\}\}",
            lambda match: variables.get(match.group(1), match.group(0)),
            prompt,
        )

    def _assistant_message(self, summary: ChangeSummary) -> str:
        if summary.applied:
            return "；".join(summary.applied)
        if summary.warnings:
            return "；".join(summary.warnings)
        return summary.user_intent
