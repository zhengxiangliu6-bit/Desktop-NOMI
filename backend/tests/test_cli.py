import pytest

from app.cli import main


def test_cli_configuration_failure_has_no_sensitive_echo(monkeypatch, capsys):
    monkeypatch.setenv("NOMI_LLM_BASE_URL", "https://fake-user:fake-private-value@provider.example")
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert "Invalid NOMI configuration" in output.err
    assert "fake-private-value" not in output.err
    assert "provider.example" not in output.err


def test_cli_honors_local_bind_and_forces_one_worker(monkeypatch):
    calls = []
    monkeypatch.setenv("NOMI_PORT", "8123")
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    monkeypatch.setattr("app.cli.uvicorn.run", lambda app, **kwargs: calls.append(kwargs))
    main()
    assert calls == [{"host": "127.0.0.1", "port": 8123, "access_log": False, "workers": 1}]
