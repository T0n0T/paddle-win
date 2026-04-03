from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.services.compiler.formily_compiler import compile_formily
from app.services.compiler.validator import load_semantic_model_from_file


def run_formily_compile(semantic_path: Path, output_path: Path):
    model = load_semantic_model_from_file(semantic_path)
    envelope = compile_formily(model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(envelope.model_dump(by_alias=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return envelope


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile a validated SemanticFormModel JSON file into Formily schema JSON."
    )
    parser.add_argument("--semantic", required=True, type=Path, help="Path to validated semantic JSON.")
    parser.add_argument(
        "--output",
        required=False,
        type=Path,
        default=Path("data/manual/semantic-result.formily.json"),
        help="Path to write the compiled Formily schema JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    envelope = run_formily_compile(semantic_path=args.semantic, output_path=args.output)
    print(args.output)
    print(json.dumps(envelope.model_dump(by_alias=True), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
