from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
BACKEND_ROOT = ENV_FILE.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4.1-mini"
    run_root: Path = Field(default=Path("runs"), validation_alias=AliasChoices("RUN_ROOT", "ARTIFACT_ROOT"))
    prompt_template_path: Path = Path("app/prompts/reconstruct_html.md")
    workbench_init_prompt_path: Path = Path("app/prompts/workbench_init.md")
    workbench_edit_prompt_path: Path = Path("app/prompts/workbench_edit.md")
    workbench_session_root: Path = Path("data/sessions")
    workbench_max_validation_retries: int = 1
    enable_dev_artifacts: bool = True

    @field_validator("run_root", "workbench_session_root", mode="after")
    @classmethod
    def resolve_backend_relative_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return BACKEND_ROOT / value
