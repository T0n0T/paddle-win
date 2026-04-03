from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4.1-mini"
    run_root: Path = Field(default=Path("runs"), validation_alias=AliasChoices("RUN_ROOT", "ARTIFACT_ROOT"))
    prompt_template_path: Path = Path("app/prompts/reconstruct_html.md")
    enable_dev_artifacts: bool = True
