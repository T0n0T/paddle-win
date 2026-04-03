from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typer.testing import CliRunner

from main import app


def test_settings_default_prompt_path_is_inside_backend() -> None:
    from app.config import Settings

    settings = Settings()
    assert settings.prompt_template_path == Path("app/prompts/reconstruct_html.md")


def test_settings_default_run_root_is_backend_runs() -> None:
    from app.config import Settings

    settings = Settings()
    assert settings.run_root == Path("runs")


def test_main_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "reconstruct" in result.stdout
    assert "ocr" in result.stdout
