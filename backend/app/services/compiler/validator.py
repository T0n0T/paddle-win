from __future__ import annotations

import json
from pathlib import Path

from app.models.semantic import SemanticFormModel


def validate_semantic_model(model: SemanticFormModel) -> SemanticFormModel:
    return SemanticFormModel.model_validate(model.model_dump())


def load_semantic_model_from_file(path: Path) -> SemanticFormModel:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SemanticFormModel.model_validate(payload)
