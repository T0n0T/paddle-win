import os
from pathlib import Path

import pytest

from app.services.artifacts import ArtifactStore


def test_create_run_dir_copies_source_image(tmp_path: Path) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"fake-image")

    store = ArtifactStore(tmp_path / "runs")
    run_dir, copied_image = store.create_run(image)

    assert run_dir.exists()
    assert copied_image.exists()
    assert copied_image.read_bytes() == b"fake-image"
    assert copied_image.parent == run_dir
    assert copied_image.name == "source.png"


def test_write_text_and_bytes_create_files_in_run_dir(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_dir = store.run_root / "20260403-000001-a"
    run_dir.mkdir(parents=True)

    text_path = store.write_text(run_dir, "prompt.txt", "你好，世界")
    bytes_path = store.write_bytes(run_dir, "image.bin", b"\x00\x01")

    assert text_path == run_dir / "prompt.txt"
    assert text_path.read_text(encoding="utf-8") == "你好，世界"
    assert bytes_path == run_dir / "image.bin"
    assert bytes_path.read_bytes() == b"\x00\x01"


def test_latest_run_returns_most_recent_directory(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    first_dir = store.run_root / "20260403-000001-a"
    second_dir = store.run_root / "20260403-000002-b"
    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)

    assert store.latest_run() == second_dir


def test_latest_run_prefers_newest_directory_mtime_over_name(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    older_dir = store.run_root / "20260403-000001-z"
    newer_dir = store.run_root / "20260403-000001-a"
    older_dir.mkdir(parents=True)
    newer_dir.mkdir(parents=True)

    os.utime(older_dir, ns=(1_000_000_000, 1_000_000_000))
    os.utime(newer_dir, ns=(2_000_000_000, 2_000_000_000))

    assert store.latest_run() == newer_dir


def test_latest_run_returns_none_when_run_root_is_empty(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")

    assert store.latest_run() is None


def test_write_operations_reject_paths_outside_run_dir(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_dir = store.run_root / "20260403-000001-a"
    run_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="run_dir"):
        store.write_text(run_dir, "../escaped.txt", "bad")

    with pytest.raises(ValueError, match="run_dir"):
        store.write_bytes(run_dir, "../escaped.bin", b"bad")

    assert not (store.run_root / "escaped.txt").exists()
    assert not (store.run_root / "escaped.bin").exists()
