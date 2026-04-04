from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from openai import OpenAI


class MultimodalLLMService:
    def __init__(self, api_key: str, model: str, base_url: str = "") -> None:
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)
        self.model = model

    def generate_text(self, image_path: Path, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required before running reconstruct")

        mime_type, _ = mimetypes.guess_type(image_path.name)
        data_url = self._to_data_url(image_path, mime_type or "application/octet-stream")
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
        )
        content = completion.choices[0].message.content
        if isinstance(content, str) and content.strip():
            return content
        raise ValueError("Model response did not contain text content")

    def generate_html(self, image_path: Path, prompt: str) -> str:
        return self.generate_text(image_path=image_path, prompt=prompt)

    def _to_data_url(self, image_path: Path, mime_type: str) -> str:
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
