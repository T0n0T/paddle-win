from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_backend_env_file(config_file: Path) -> Path:
    return config_file.resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=resolve_backend_env_file(Path(__file__)),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-mini"
    ARTIFACT_ROOT: Path = Field(default=Path("artifacts"))
    ENABLE_DEV_ARTIFACTS: bool = False
