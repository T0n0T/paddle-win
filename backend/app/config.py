from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4.1-mini"
    run_root: Path = Path("runs")
    prompt_template_path: Path = Path("app/prompts/reconstruct_html.md")
    enable_dev_artifacts: bool = True
