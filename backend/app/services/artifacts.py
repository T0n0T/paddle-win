from __future__ import annotations

from datetime import datetime
from pathlib import Path
from shutil import copy2
import re


RUN_DIR_PATTERN = re.compile(r"^(?P<timestamp>\d{8}-\d{6})-(?P<sequence>\d{6})$")


class ArtifactStore:
    def __init__(self, run_root: Path) -> None:
        self.run_root = run_root
        self.run_root.mkdir(parents=True, exist_ok=True)

    def create_run(self, image_path: Path) -> tuple[Path, Path]:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        next_sequence = self._next_sequence_for_timestamp(timestamp)
        run_id = f"{timestamp}-{next_sequence:06d}"
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
        runs = [path for path in self.run_root.iterdir() if self._is_valid_run_dir(path)]
        if not runs:
            return None
        return max(runs, key=lambda path: self._run_dir_sort_key(path))

    def _resolve_run_path(self, run_dir: Path, filename: str) -> Path:
        self._ensure_valid_run_dir(run_dir)
        base_dir = run_dir.resolve()
        path = (base_dir / filename).resolve()
        try:
            path.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError("artifact path must stay inside run_dir") from exc
        return path

    def _next_sequence_for_timestamp(self, timestamp: str) -> int:
        sequences = [
            self._run_dir_sort_key(path)[1]
            for path in self.run_root.iterdir()
            if self._is_valid_run_dir(path) and self._run_dir_sort_key(path)[0] == timestamp
        ]
        if not sequences:
            return 1
        return max(sequences) + 1

    def _is_valid_run_dir(self, path: Path) -> bool:
        if not path.is_dir() or path.is_symlink():
            return False
        return RUN_DIR_PATTERN.match(path.name) is not None

    def _ensure_valid_run_dir(self, run_dir: Path) -> None:
        if run_dir.is_symlink():
            raise ValueError("run_dir symlink is not allowed")
        if not self._is_valid_run_dir(run_dir):
            raise ValueError("run_dir must be a direct run directory inside run_root")
        try:
            run_dir.resolve().relative_to(self.run_root.resolve())
        except ValueError as exc:
            raise ValueError("run_dir must be inside run_root") from exc

    def _run_dir_sort_key(self, path: Path) -> tuple[str, int]:
        match = RUN_DIR_PATTERN.match(path.name)
        if match is None:
            raise ValueError(f"invalid run directory name: {path.name}")
        return match.group("timestamp"), int(match.group("sequence"))
