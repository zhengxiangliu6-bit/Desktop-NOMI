import os

import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    # Tests never read an injected real account configuration.
    for name in list(os.environ):
        if name.startswith("NOMI_"):
            monkeypatch.delenv(name)


@pytest.fixture
def settings_factory():
    def make(**values):
        return Settings(_env_file=None, **values)

    return make
