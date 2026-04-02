from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.models.semantic import SemanticFormModel
from app.services.llm.openai_client import OpenAIResponsesClient
from app.services.llm.semantic_enricher import build_semantic_request, load_prompt
from app.services.ocr.layout_normalizer import normalize_layout


def run_prompt_tuning(
    image_path: Path,
    ocr_json_path: Path,
    prompt_path: Path,
    output_path: Path,
    client: OpenAIResponsesClient | None = None,
) -> SemanticFormModel:
    raw_ocr_payload = json.loads(ocr_json_path.read_text(encoding="utf-8"))
    layout = normalize_layout(raw_ocr_payload)
    request = build_semantic_request(
        layout,
        image_path=image_path,
        raw_ocr_payload=raw_ocr_payload,
        prompt_text=prompt_path.read_text(encoding="utf-8"),
    )
    resolved_client = client or OpenAIResponsesClient()
    result = resolved_client.generate_structured(request, SemanticFormModel)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run semantic prompt tuning against one OCR artifact.")
    parser.add_argument("--image", required=True, type=Path, help="Path to the source image.")
    parser.add_argument("--ocr", required=True, type=Path, help="Path to the raw OCR JSON artifact.")
    parser.add_argument(
        "--prompt",
        required=False,
        type=Path,
        default=Path(__file__).parent / "prompts" / "semantic_enrich.md",
        help="Path to the prompt markdown file.",
    )
    parser.add_argument(
        "--output",
        required=False,
        type=Path,
        default=Path("data/manual/semantic-result.json"),
        help="Path to write the validated SemanticFormModel JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_prompt_tuning(
        image_path=args.image,
        ocr_json_path=args.ocr,
        prompt_path=args.prompt,
        output_path=args.output,
    )
    print(args.output)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
