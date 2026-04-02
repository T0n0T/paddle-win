from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.models.semantic import SemanticFormModel
from app.services.llm.openai_client import OpenAIResponsesClient
from app.services.ocr.layout_normalizer import LayoutSkeleton


PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class SemanticPromptRequest:
    instructions: str
    image_path: Path
    raw_ocr_json: dict[str, Any]
    layout_json: dict[str, Any]


def load_prompt(prompt_name: str) -> str:
    return (PROMPTS_DIR / prompt_name).read_text(encoding="utf-8")


def build_semantic_request(
    layout: LayoutSkeleton,
    image_path: str | Path,
    raw_ocr_payload: dict[str, Any],
    prompt_text: str | None = None,
) -> SemanticPromptRequest:
    return SemanticPromptRequest(
        instructions=prompt_text or load_prompt("semantic_enrich.md"),
        image_path=Path(image_path),
        raw_ocr_json=raw_ocr_payload,
        layout_json=asdict(layout),
    )


class SemanticEnricher:
    def __init__(self, client: OpenAIResponsesClient) -> None:
        self._client = client

    def enrich(
        self,
        layout: LayoutSkeleton,
        image_path: str | Path,
        raw_ocr_payload: dict[str, Any],
        prompt_text: str | None = None,
    ) -> SemanticFormModel:
        request = build_semantic_request(
            layout,
            image_path=image_path,
            raw_ocr_payload=raw_ocr_payload,
            prompt_text=prompt_text,
        )
        return self._client.generate_structured(request, SemanticFormModel)
