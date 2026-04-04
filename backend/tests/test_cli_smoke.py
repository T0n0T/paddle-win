from pathlib import Path
from subprocess import run


def test_makefile_contains_required_targets() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    content = (repo_root / "Makefile").read_text(encoding="utf-8")

    assert "ocr:" in content
    assert "reconstruct:" in content
    assert "latest:" in content
    assert "reconstruct-from-ocr:" not in content
    assert "prompt-show:" not in content
    assert "sed 's#^#$(BACKEND_DIR)/#'" in content


def test_makefile_contains_workbench_targets() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    content = (repo_root / "Makefile").read_text(encoding="utf-8")

    assert "api-dev:" in content
    assert "frontend-dev:" in content


def test_make_latest_succeeds_when_runs_directory_is_missing(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = run(
        ["make", "--silent", "latest", f"BACKEND_DIR={tmp_path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert "No such file or directory" not in result.stdout
    assert "No such file or directory" not in result.stderr


def test_make_latest_outputs_latest_run_directory(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = tmp_path / "backend"
    runs_dir = backend_dir / "runs"
    runs_dir.mkdir(parents=True)
    older_run = runs_dir / "20260403-101500-000001"
    newer_run = runs_dir / "20260403-101500-000002"
    older_run.mkdir()
    newer_run.mkdir()

    result = run(
        ["make", "--silent", "latest", f"BACKEND_DIR={backend_dir}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == f"{backend_dir}/runs/{newer_run.name}"
    assert "No such file or directory" not in result.stderr
