import json
import os
from pathlib import Path
from subprocess import run


def test_makefile_contains_required_targets() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    content = (repo_root / "Makefile").read_text(encoding="utf-8")

    assert "OCR_JSON ?=" in content
    assert "ocr:" in content
    assert "reconstruct:" in content
    assert "reconstruct-from-ocr:" in content
    assert "latest:" in content
    assert "prompt-show:" in content
    assert 'cd $(BACKEND_DIR) && $(PYTHON) main.py reconstruct-from-ocr "$(IMAGE)" "$(OCR_JSON)"' in content
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


def test_make_prompt_show_outputs_ocr_placeholder() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = run(
        ["make", "prompt-show"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "{{OCR_JSON}}" in result.stdout


def test_make_reconstruct_from_ocr_runs_until_openai_key_check(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    ocr_json_path = tmp_path / "ocr_compact.json"
    ocr_json_path.write_text(
        json.dumps([{"text": "姓名", "bbox": [0, 0, 10, 10], "block_type": "text"}], ensure_ascii=False),
        encoding="utf-8",
    )

    run_root = tmp_path / "runs-out"
    env = os.environ.copy()
    env["RUN_ROOT"] = str(run_root)
    env["OPENAI_API_KEY"] = ""

    result = run(
        [
            "make",
            "reconstruct-from-ocr",
            f"IMAGE={image_path}",
            f"OCR_JSON={ocr_json_path}",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    combined_output = result.stdout + result.stderr
    run_dirs = [path for path in run_root.iterdir() if path.is_dir()]

    assert result.returncode != 0
    assert "OPENAI_API_KEY" in combined_output
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "ocr_compact.json").exists()
    assert (run_dirs[0] / "prompt.txt").exists()
