from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NOMI_",
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )
    host: Literal["127.0.0.1", "localhost", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    llm_provider: Literal["mock", "openai"] = "mock"
    llm_base_url: str | None = Field(default=None, repr=False)
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=60, gt=0, le=120, allow_inf_nan=False)
    llm_max_output_tokens: int = Field(default=1024, ge=64, le=8192)
    llm_json_mode: bool = False
    llm_token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    context_max_turns: int = Field(default=10, ge=1, le=50)
    context_max_chars: int = Field(default=16000, ge=5000, le=128000)
    max_sessions: int = Field(default=100, ge=1, le=1000)
    session_ttl_seconds: float = Field(default=1800, gt=0, le=86400, allow_inf_nan=False)

    @field_validator("llm_base_url", "llm_model", mode="before")
    @classmethod
    def optional_string(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("llm_base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        url = urlsplit(value)
        if (
            any(char.isspace() for char in value)
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.scheme not in {"http", "https"}
        ):
            raise ValueError("BASE_URL must be an API root without credentials, query or fragment")
        if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Remote providers require HTTPS")
        try:
            _ = url.port
        except ValueError:
            raise ValueError("Invalid BASE_URL port") from None
        return value.rstrip("/")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        return (
            [item.strip() for item in value.split(",") if item.strip()]
            if isinstance(value, str)
            else value
        )

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            url = urlsplit(value)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
                or url.path
                or url.query
                or url.fragment
                or "*" in url.hostname
            ):
                raise ValueError(
                    "Origins must be exact HTTP(S) origins, without wildcards or paths"
                )
        return values

    @property
    def openai_configured(self) -> bool:
        return bool(
            self.llm_base_url
            and self.llm_model
            and self.llm_api_key
            and self.llm_api_key.get_secret_value().strip()
        )

    @property
    def chat_available(self) -> bool:
        return self.llm_provider == "mock" or self.openai_configured
