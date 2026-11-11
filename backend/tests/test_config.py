import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_process_environment_overrides_dotenv_and_secrets_are_redacted(monkeypatch, tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "NOMI_LLM_PROVIDER=openai\nNOMI_LLM_MODEL=file-model\nNOMI_LLM_API_KEY=fictional-key\nNOMI_LLM_BASE_URL=https://provider.example/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("NOMI_LLM_MODEL", "environment-model")
    settings = Settings(_env_file=dotenv)
    assert settings.llm_model == "environment-model"
    assert settings.chat_available
    assert "fictional-key" not in repr(settings)
    assert "fictional-key" not in settings.model_dump_json()
    assert "provider.example" not in repr(settings)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://remote.example/v1",
        "https://user:password@provider.example/v1",
        "not-a-url",
        "https://provider.example/v1?api_key=fictional",
        "https://provider.example/v1#fragment",
        "https://provider.example:bad/v1",
        "https://bad host/v1",
    ],
)
def test_invalid_urls_fail_without_echoing_input(settings_factory, base_url):
    with pytest.raises(ValidationError) as error:
        settings_factory(llm_base_url=base_url)
    assert base_url not in str(error.value)


def test_local_http_origins_limits_and_explicit_provider(settings_factory):
    assert settings_factory(llm_base_url="http://localhost:1234/v1").llm_base_url
    assert settings_factory(
        allowed_origins="http://localhost:5173,http://127.0.0.1:5173"
    ).allowed_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    for values in [
        {"llm_provider": "unknown"},
        {"host": "0.0.0.0"},
        {"allowed_origins": "http://*.example"},
        {"llm_timeout_seconds": 0},
        {"context_max_chars": 100},
        {"max_sessions": 0},
    ]:
        with pytest.raises(ValidationError):
            settings_factory(**values)
