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


def test_readmes_make_external_ocr_json_boundary_explicit() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    root_readme = (repo_root / "README.md").read_text(encoding="utf-8")
    backend_readme = (repo_root / "backend/README.md").read_text(encoding="utf-8")

    assert "ocr_compact.json 需要由仓库外部链路预先生成" in root_readme
    assert "ocr_compact.json 需要由仓库外部链路预先生成" in backend_readme


def test_zero_shot_plan_is_marked_as_paused_in_favor_of_workbench() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    plan = (
        repo_root / "docs/superpowers/plans/2026-04-03-zero-shot-form-reconstruction.md"
    ).read_text(encoding="utf-8")

    assert "状态：已暂停，不再作为当前主线实施计划" in plan
    assert "当前受支持主线为“外部 OCR JSON + workbench 会话编辑”" in plan
