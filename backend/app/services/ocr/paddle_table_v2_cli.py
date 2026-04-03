from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.services.ocr.paddle_table_v2 import PaddleTableV2Client


def run_ocr_export(
    image_path: Path,
    output_path: Path,
    client: PaddleTableV2Client | None = None,
) -> dict[str, object]:
    resolved_client = client or PaddleTableV2Client()
    payload = resolved_client.run(image_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PaddleOCR TableRecognitionPipelineV2 on one image.")
    parser.add_argument("--image", required=True, type=Path, help="Path to the source image.")
    parser.add_argument(
        "--output",
        required=False,
        type=Path,
        default=Path("data/manual/ocr.json"),
        help="Path to write the raw OCR JSON artifact.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = run_ocr_export(image_path=args.image, output_path=args.output)
    print(args.output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
