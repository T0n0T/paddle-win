from __future__ import annotations

import base64
import json
import mimetypes
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
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_structured(
        self,
        request: Any,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        response = self._client.responses.create(**build_responses_request(request, model=self.model))
        payload = _extract_output_text(response)
        return response_model.model_validate_json(payload)


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text
    raise ValueError("OpenAI response did not include output_text")
