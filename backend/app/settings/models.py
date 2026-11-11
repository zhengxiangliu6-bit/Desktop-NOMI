from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

# Exact official-compatible API roots only; never accept user-controlled hosts/paths.
BAILIAN_ROOTS = (
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
)


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    provider: Literal["mock", "openai"] = "mock"
    base_url: str = ""
    model: str = ""
    api_key: SecretStr | None = Field(default=None, repr=False)
    max_tokens: int = Field(default=1024, ge=64, le=8192)
    token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    json_mode: bool = False
    managed: bool = False


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    provider: Literal["mock", "openai"]
    base_url: str = Field(max_length=160)
    model: str = Field(max_length=200, pattern=r"^[A-Za-z0-9_.:/-]*$")
    key_action: Literal["keep", "replace", "clear"] = "keep"
    api_key: SecretStr | None = Field(default=None, repr=False)
    max_tokens: int = Field(default=1024, ge=64, le=8192)
    token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    json_mode: bool = False

    @field_validator("base_url")
    @classmethod
    def allowed_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value and value not in BAILIAN_ROOTS:
            raise ValueError("Only approved Bailian HTTPS API roots are supported")
        return value

    @field_validator("api_key")
    @classmethod
    def valid_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            raw = value.get_secret_value()
            if not 1 <= len(raw) <= 1024 or any(not 33 <= ord(c) <= 126 for c in raw):
                raise ValueError("Invalid credential")
        return value


class PairRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    code: SecretStr = Field(repr=False)


class ConnectionTest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_paid_request: Literal[True]
    revision: int

    @field_validator("confirm_paid_request", mode="before")
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError("A literal true confirmation is required")
        return value
