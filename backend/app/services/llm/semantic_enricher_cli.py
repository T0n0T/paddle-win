from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from app.models.semantic import SemanticFormModel
from app.services.llm.openai_client import OpenAIResponsesClient, extract_structured_output
from app.services.llm.semantic_enricher import build_semantic_request, load_prompt
from app.services.ocr.layout_normalizer import normalize_layout


def extract_semantic_model_from_raw_response(raw_response_path: Path) -> SemanticFormModel:
    payload = json.loads(raw_response_path.read_text(encoding="utf-8"))
    try:
        return extract_structured_output(payload, SemanticFormModel)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Could not extract a valid semantic payload from raw response") from exc


def run_prompt_tuning(
    image_path: Path,
    ocr_json_path: Path,
    prompt_path: Path,
    output_path: Path,
    client: OpenAIResponsesClient | None = None,
    raw_response_output: bool = False,
) -> SemanticFormModel | dict[str, Any]:
    raw_ocr_payload = json.loads(ocr_json_path.read_text(encoding="utf-8"))
    layout = normalize_layout(raw_ocr_payload)
    request = build_semantic_request(
        layout,
        image_path=image_path,
        raw_ocr_payload=raw_ocr_payload,
        prompt_text=prompt_path.read_text(encoding="utf-8"),
    )
    resolved_client = client or OpenAIResponsesClient()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_response_output:
        result = resolved_client.generate_raw(request)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    result = resolved_client.generate_structured(request, SemanticFormModel)
    output_path.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run semantic prompt tuning against one OCR artifact.")
    parser.add_argument("--image", required=False, type=Path, help="Path to the source image.")
    parser.add_argument("--ocr", required=False, type=Path, help="Path to the raw OCR JSON artifact.")
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
    parser.add_argument(
        "--raw-response-output",
        action="store_true",
        help="Skip SemanticFormModel validation and write the full raw model response JSON to --output.",
    )
    parser.add_argument(
        "--from-raw-response",
        required=False,
        type=Path,
        help="Read an existing raw response JSON file, extract payload locally, and validate as SemanticFormModel without calling the model.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.from_raw_response is not None:
        result = extract_semantic_model_from_raw_response(args.from_raw_response)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(args.output)
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        return 0

    if args.image is None or args.ocr is None:
        parser.error("--image and --ocr are required unless --from-raw-response is used")

    result = run_prompt_tuning(
        image_path=args.image,
        ocr_json_path=args.ocr,
        prompt_path=args.prompt,
        output_path=args.output,
        raw_response_output=args.raw_response_output,
    )
    print(args.output)
    if isinstance(result, SemanticFormModel):
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
