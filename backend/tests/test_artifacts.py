from datetime import datetime
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
    run_dir = store.run_root / "20260403-000001-000001"
    run_dir.mkdir(parents=True)

    text_path = store.write_text(run_dir, "prompt.txt", "你好，世界")
    bytes_path = store.write_bytes(run_dir, "image.bin", b"\x00\x01")

    assert text_path == run_dir / "prompt.txt"
    assert text_path.read_text(encoding="utf-8") == "你好，世界"
    assert bytes_path == run_dir / "image.bin"
    assert bytes_path.read_bytes() == b"\x00\x01"


def test_latest_run_returns_most_recent_directory(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    first_dir = store.run_root / "20260403-000001-000001"
    second_dir = store.run_root / "20260403-000002-000001"
    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)

    assert store.latest_run() == second_dir


def test_create_run_assigns_incrementing_suffix_within_same_second(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"fake-image")
    store = ArtifactStore(tmp_path / "runs")

    class FrozenDatetime:
        @staticmethod
        def now() -> datetime:
            return datetime(2026, 4, 3, 12, 0, 1)

    monkeypatch.setattr("app.services.artifacts.datetime", FrozenDatetime)

    first_run, _ = store.create_run(image)
    second_run, _ = store.create_run(image)

    assert first_run.name == "20260403-120001-000001"
    assert second_run.name == "20260403-120001-000002"
    assert store.latest_run() == second_run


def test_latest_run_ignores_old_run_written_later(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    older_dir = store.run_root / "20260403-000001-000001"
    newer_dir = store.run_root / "20260403-000001-000002"
    older_dir.mkdir(parents=True)
    newer_dir.mkdir(parents=True)

    store.write_text(older_dir, "after.txt", "written later")

    assert store.latest_run() == newer_dir


def test_latest_run_returns_none_when_run_root_is_empty(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")

    assert store.latest_run() is None


def test_write_operations_reject_paths_outside_run_dir(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_dir = store.run_root / "20260403-000001-000001"
    run_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="run_dir"):
        store.write_text(run_dir, "../escaped.txt", "bad")

    with pytest.raises(ValueError, match="run_dir"):
        store.write_bytes(run_dir, "../escaped.bin", b"bad")

    assert not (store.run_root / "escaped.txt").exists()
    assert not (store.run_root / "escaped.bin").exists()


def test_latest_run_ignores_symlink_directories(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    real_run = store.run_root / "20260403-000001-000001"
    real_run.mkdir(parents=True)

    external_run = tmp_path / "external-run"
    external_run.mkdir()
    symlink_run = store.run_root / "20260403-999999-999999"
    symlink_run.symlink_to(external_run, target_is_directory=True)

    assert symlink_run.is_dir()
    assert store.latest_run() == real_run


def test_write_operations_reject_symlink_run_dir(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    external_run = tmp_path / "external-run"
    external_run.mkdir()
    symlink_run = store.run_root / "20260403-000001-000001"
    symlink_run.symlink_to(external_run, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        store.write_text(symlink_run, "artifact.txt", "bad")

    with pytest.raises(ValueError, match="symlink"):
        store.write_bytes(symlink_run, "artifact.bin", b"bad")

    assert not (external_run / "artifact.txt").exists()
    assert not (external_run / "artifact.bin").exists()
