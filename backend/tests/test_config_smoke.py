from importlib import util
from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: Path):
    path = ROOT / relative_path
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


__main_module = _load_module("backend.main", Path("main.py"))
app = __main_module.app

__config_module = _load_module("backend.app.config", Path("app") / "config.py")
Settings = __config_module.Settings


def test_settings_default_prompt_path_is_inside_backend() -> None:
    settings = Settings()
    assert settings.prompt_template_path == Path("app/prompts/reconstruct_html.md")


def test_settings_default_run_root_is_backend_runs() -> None:
    settings = Settings()
    assert settings.run_root == Path("runs")


def test_main_shows_help_without_args() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "reconstruct" in result.stdout
    assert "ocr" in result.stdout
