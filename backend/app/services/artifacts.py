from __future__ import annotations

from datetime import datetime
from pathlib import Path
from shutil import copy2
from uuid import uuid4


class ArtifactStore:
    def __init__(self, run_root: Path) -> None:
        self.run_root = run_root
        self.run_root.mkdir(parents=True, exist_ok=True)

    def create_run(self, image_path: Path) -> tuple[Path, Path]:
        run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
        run_dir = self.run_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)

        copied_image = run_dir / f"source{image_path.suffix.lower()}"
        copy2(image_path, copied_image)
        return run_dir, copied_image

    def write_text(self, run_dir: Path, filename: str, content: str) -> Path:
        path = self._resolve_run_path(run_dir, filename)
        path.write_text(content, encoding="utf-8")
        return path

    def write_bytes(self, run_dir: Path, filename: str, content: bytes) -> Path:
        path = self._resolve_run_path(run_dir, filename)
        path.write_bytes(content)
        return path

    def latest_run(self) -> Path | None:
        runs = [path for path in self.run_root.iterdir() if path.is_dir()]
        if not runs:
            return None
        return max(runs, key=lambda path: (path.stat().st_mtime_ns, path.name))

    def _resolve_run_path(self, run_dir: Path, filename: str) -> Path:
        base_dir = run_dir.resolve()
        path = (base_dir / filename).resolve()
        try:
            path.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError("artifact path must stay inside run_dir") from exc
        return path
