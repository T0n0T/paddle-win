from pathlib import Path

from typer.testing import CliRunner

from app.config import Settings
from app.models import PipelineState
from main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_settings_default_prompt_path_is_inside_backend() -> None:
    settings = Settings(_env_file=None)
    assert settings.prompt_template_path == Path("app/prompts/reconstruct_html.md")


def test_settings_default_run_root_is_backend_runs(monkeypatch) -> None:
    monkeypatch.delenv("RUN_ROOT", raising=False)
    monkeypatch.delenv("ARTIFACT_ROOT", raising=False)

    settings = Settings(_env_file=None)
    assert settings.run_root == BACKEND_ROOT / "runs"


def test_settings_accepts_artifact_root_for_run_root(monkeypatch) -> None:
    monkeypatch.delenv("RUN_ROOT", raising=False)
    monkeypatch.setenv("ARTIFACT_ROOT", "data/jobs")

    settings = Settings(_env_file=None)
    assert settings.run_root == BACKEND_ROOT / "data/jobs"


def test_settings_accepts_run_root_relative_to_backend(monkeypatch) -> None:
    monkeypatch.delenv("ARTIFACT_ROOT", raising=False)
    monkeypatch.setenv("RUN_ROOT", "tmp/output")

    settings = Settings(_env_file=None)
    assert settings.run_root == BACKEND_ROOT / "tmp/output"


def test_main_shows_help_without_args() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert "Usage:" in result.stdout
    assert "reconstruct" in result.stdout
    assert "ocr" in result.stdout


def test_pipeline_state_uses_structured_metadata_model() -> None:
    state = PipelineState(image_path=Path("/tmp/form.png"))

    assert hasattr(state.metadata, "run_id")
    assert state.metadata.run_id is None
    assert state.metadata.source_kind == "external"
    assert state.metadata.model_dump() == {
        "run_id": None,
        "source_kind": "external",
        "notes": [],
    }
