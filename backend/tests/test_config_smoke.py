from pathlib import Path

from typer.testing import CliRunner

from app.config import Settings
from main import app


def test_settings_default_prompt_path_is_inside_backend() -> None:
    settings = Settings(_env_file=None)
    assert settings.prompt_template_path == Path("app/prompts/reconstruct_html.md")


def test_settings_default_run_root_is_backend_runs(monkeypatch) -> None:
    monkeypatch.delenv("RUN_ROOT", raising=False)
    monkeypatch.delenv("ARTIFACT_ROOT", raising=False)

    settings = Settings(_env_file=None)
    assert settings.run_root == Path("runs")


def test_settings_accepts_artifact_root_for_run_root(monkeypatch) -> None:
    monkeypatch.delenv("RUN_ROOT", raising=False)
    monkeypatch.setenv("ARTIFACT_ROOT", "data/jobs")

    settings = Settings(_env_file=None)
    assert settings.run_root == Path("data/jobs")


def test_main_shows_help_without_args() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert "Usage:" in result.stdout
    assert "reconstruct" in result.stdout
    assert "ocr" in result.stdout
