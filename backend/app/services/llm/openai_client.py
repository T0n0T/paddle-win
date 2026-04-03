from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import Settings


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


def build_responses_request(request: Any, model: str) -> dict[str, Any]:
    image_path = Path(request.image_path)
    image_bytes = image_path.read_bytes()
    media_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    image_data = base64.b64encode(image_bytes).decode("ascii")

    structured_input = {
        "raw_ocr_json": request.raw_ocr_json,
        "layout_json": request.layout_json,
    }

    return {
        "model": model,
        "instructions": request.instructions,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(structured_input, ensure_ascii=False, indent=2),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{media_type};base64,{image_data}",
                    },
                ],
            }
        ],
    }


class OpenAIResponsesClient:
    def __init__(self, model: str | None = None, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self.model = model or "gpt-4.1-mini"
            self._client = sdk_client
            return

        settings = Settings()
        self.model = model or settings.OPENAI_MODEL
        client_kwargs: dict[str, Any] = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        self._client = OpenAI(**client_kwargs)

    def generate_structured(
        self,
        request: Any,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        response = self._client.responses.create(**build_responses_request(request, model=self.model))
        if hasattr(response, "model_dump") and callable(response.model_dump):
            normalized_response: Any = _normalize_raw_response_payload(response.model_dump())
        elif isinstance(response, dict):
            normalized_response = _normalize_raw_response_payload(response)
        elif isinstance(response, str):
            normalized_response = _normalize_raw_response_payload(response)
        else:
            normalized_response = _normalize_raw_response_payload(
                json.loads(json.dumps(response, default=_json_default, ensure_ascii=False))
            )
        return extract_structured_output(normalized_response, response_model)

    def generate_raw(self, request: Any) -> dict[str, Any]:
        response = self._client.responses.create(**build_responses_request(request, model=self.model))
        if hasattr(response, "model_dump") and callable(response.model_dump):
            return _normalize_raw_response_payload(response.model_dump())
        if isinstance(response, dict):
            return _normalize_raw_response_payload(response)
        return _normalize_raw_response_payload(
            json.loads(json.dumps(response, default=_json_default, ensure_ascii=False))
        )


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text is None and isinstance(response, dict):
        output_text = response.get("output_text")
    if isinstance(output_text, str):
        return _normalize_model_text(output_text)

    output_items = getattr(response, "output", None)
    if output_items is None and isinstance(response, dict):
        output_items = response.get("output")

    for item in output_items or []:
        content_items = getattr(item, "content", None)
        if content_items is None and isinstance(item, dict):
            content_items = item.get("content")
        if not content_items:
            continue
        for content in content_items:
            content_type = getattr(content, "type", None)
            if content_type is None and isinstance(content, dict):
                content_type = content.get("type")
            if content_type != "output_text":
                continue
            text = getattr(content, "text", None)
            if text is None and isinstance(content, dict):
                text = content.get("text")
            if isinstance(text, str):
                return _normalize_model_text(text)

    raise ValueError("OpenAI response did not include output_text")


def extract_structured_output(
    payload: Any,
    response_model: type[StructuredModel],
) -> StructuredModel:
    if isinstance(payload, dict):
        output_json = payload.get("output_json")
        if output_json is not None:
            return response_model.model_validate(output_json)

        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return response_model.model_validate_json(_normalize_model_text(output_text))

    output_text = _extract_output_text(payload)
    return response_model.model_validate_json(output_text)


def _normalize_model_text(text: str) -> str:
    stripped = text.strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()
    return stripped


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return value.__dict__
    return repr(value)


def _normalize_raw_response_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, str):
        output_text = _extract_output_text_from_sse(payload)
        normalized: dict[str, Any] = {
            "response_format": "sse_text",
            "raw_response": payload,
            "output_text": output_text,
        }
        if output_text is not None:
            normalized["output_json"] = _try_parse_json(output_text)
        return normalized

    if isinstance(payload, dict):
        output_text = None
        try:
            output_text = _extract_output_text(payload)
        except ValueError:
            output_text = None

        normalized = {
            "response_format": "json",
            "response": payload,
            "output_text": output_text,
        }
        if output_text is not None:
            normalized["output_json"] = _try_parse_json(output_text)
        return normalized

    return {
        "response_format": "unknown",
        "raw_response": payload,
        "output_text": None,
    }


def _extract_output_text_from_sse(payload: str) -> str | None:
    deltas: list[str] = []
    for chunk in payload.split("\n\n"):
        lines = [line for line in chunk.splitlines() if line]
        if not lines:
            continue
        event_name = None
        data_parts: list[str] = []
        for line in lines:
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_parts.append(line.split(":", 1)[1].lstrip())
        if event_name != "response.output_text.delta" or not data_parts:
            continue
        try:
            data = json.loads("\n".join(data_parts))
        except json.JSONDecodeError:
            continue
        delta = data.get("delta")
        if isinstance(delta, str):
            deltas.append(delta)
    if not deltas:
        return None
    return _normalize_model_text("".join(deltas))


def _try_parse_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
