import ctypes

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.errors import AppError
from app.main import create_app
from app.settings.manager import LocalSettings
from app.settings.models import BAILIAN_ROOTS, Profile, ProfileUpdate
from app.settings.network import PublicNetworkBackend, secure_client
from app.settings.vault import Credential, MemoryVault, VaultError, WindowsVault
from tests.helpers import ScriptedProvider, reply_json

CODE = "fictional-one-time-code"
ORIGIN = {"Origin": "http://localhost:5173", "Sec-Fetch-Site": "same-origin"}


def client_for(settings_factory, *, vault=None, factory=None, clock=None):
    settings = settings_factory()
    kwargs = {}
    if factory is not None:
        kwargs["factory"] = factory
    if clock:
        kwargs["clock"] = clock
    admin = LocalSettings(settings, vault or MemoryVault(), CODE, **kwargs)
    client = TestClient(
        create_app(settings, local_admin=admin),
        base_url="http://localhost",
        client=("127.0.0.1", 40000),
    )
    return client, admin


def pair(client):
    response = client.post("/api/v0/settings/pair", json={"code": CODE}, headers=ORIGIN)
    assert response.status_code == 200
    return {**ORIGIN, "Authorization": f"Bearer {response.json()['token']}"}


def update(**changes):
    return {
        "provider": "openai",
        "base_url": BAILIAN_ROOTS[0],
        "model": "configured-model-id",
        "key_action": "replace",
        "api_key": "fictional-vault-key",
        **changes,
    }


def test_default_off_and_no_unauthorized_local_access(settings_factory):
    with TestClient(create_app(settings_factory()), base_url="http://localhost") as client:
        assert client.post("/api/v0/settings/read", json={}, headers=ORIGIN).status_code == 403
    client, _ = client_for(settings_factory)
    with client:
        assert client.post("/api/v0/settings/read", json={}, headers=ORIGIN).status_code == 403
        assert client.post("/api/v0/settings/pair", json={"code": CODE}).status_code == 403
        assert (
            client.post(
                "/api/v0/settings/pair",
                json={"code": CODE},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v0/settings/pair",
                json={"code": CODE},
                headers={**ORIGIN, "Sec-Fetch-Site": "cross-site"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v0/settings/pair",
                json={"code": CODE},
                headers={**ORIGIN, "Host": "rebind.evil"},
            ).status_code
            == 403
        )
        headers = pair(client)
        assert client.post("/api/v0/settings/read", json={}, headers=headers).status_code == 200
        assert (
            client.post(
                "/api/v0/settings/read", json={}, headers={**headers, "Origin": "null"}
            ).status_code
            == 403
        )
        assert (
            client.post("/api/v0/settings/pair", json={"code": CODE}, headers=ORIGIN).status_code
            == 403
        )


def test_non_loopback_peer_and_duplicate_headers_rejected(settings_factory):
    settings = settings_factory()
    admin = LocalSettings(settings, MemoryVault(), CODE)
    with TestClient(
        create_app(settings, local_admin=admin),
        base_url="http://localhost",
        client=("192.168.1.2", 1234),
    ) as client:
        assert (
            client.post("/api/v0/settings/pair", json={"code": CODE}, headers=ORIGIN).status_code
            == 403
        )
    client, _ = client_for(settings_factory)
    with client:
        response = client.post(
            "/api/v0/settings/pair",
            json={"code": CODE},
            headers=[("Origin", ORIGIN["Origin"]), ("Origin", ORIGIN["Origin"])],
        )
        assert response.status_code == 403


def test_pairing_expiry_attempt_limit_and_token_expiry(settings_factory):
    now = [100.0]
    client, admin = client_for(settings_factory, clock=lambda: now[0])
    with client:
        for _ in range(5):
            assert (
                client.post(
                    "/api/v0/settings/pair", json={"code": "wrong"}, headers=ORIGIN
                ).status_code
                == 403
            )
        assert (
            client.post("/api/v0/settings/pair", json={"code": CODE}, headers=ORIGIN).status_code
            == 403
        )
    client, admin = client_for(settings_factory, clock=lambda: now[0])
    with client:
        headers = pair(client)
        now[0] += 1801
        assert client.post("/api/v0/settings/read", json={}, headers=headers).status_code == 403
    client, admin = client_for(settings_factory, clock=lambda: now[0])
    now[0] += 301
    with client:
        assert (
            client.post("/api/v0/settings/pair", json={"code": CODE}, headers=ORIGIN).status_code
            == 403
        )


def test_save_clear_reload_and_no_secret_in_responses_or_logs(settings_factory, caplog):
    vault = MemoryVault()
    client, admin = client_for(settings_factory, vault=vault)
    with client:
        headers = pair(client)
        with caplog.at_level("INFO"):
            response = client.put("/api/v0/settings", json=update(), headers=headers)
        assert response.status_code == 200
        assert response.json()["key_configured"] is True
        assert "fictional-vault-key" not in response.text + caplog.text
        assert "api_key" not in response.json()
        for _ in range(2):
            assert (
                "fictional-vault-key"
                not in client.post("/api/v0/settings/read", json={}, headers=headers).text
            )
        cleared = client.put(
            "/api/v0/settings", json=update(key_action="clear", api_key=None), headers=headers
        )
        assert cleared.status_code == 200
        assert cleared.json()["key_configured"] is False
        assert vault.load().api_key is None
        missing = client.post("/api/v0/chat", json={"text": "no key"}, headers=headers)
        assert missing.status_code == 503
        assert missing.json()["error"]["code"] == "CONFIGURATION_MISSING"
    restarted = LocalSettings(settings_factory(llm_api_key="old-env-key"), vault, CODE)
    assert not restarted.public()["key_configured"]
    assert restarted.initial.llm_api_key is None


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:1234/v1",
        "https://127.0.0.1/v1",
        "https://169.254.169.254/v1",
        "https://dashscope.aliyuncs.com.evil/compatible-mode/v1",
        "https://user:pass@dashscope.aliyuncs.com/compatible-mode/v1",
        BAILIAN_ROOTS[0] + "?token=example",
        BAILIAN_ROOTS[0] + "#fragment",
        BAILIAN_ROOTS[0] + "/../admin",
        "https://dashscope.aliyuncs.com:444/compatible-mode/v1",
    ],
)
def test_unsafe_base_urls_are_rejected(settings_factory, url):
    client, admin = client_for(settings_factory)
    with client:
        headers = pair(client)
        response = client.put("/api/v0/settings", json=update(base_url=url), headers=headers)
        assert response.status_code == 422
        assert admin.revision == 0
        assert "fictional-vault-key" not in response.text


def test_storage_failure_rolls_back_and_scope_change_requires_key_decision(settings_factory):
    class FailingVault(MemoryVault):
        def save(self, profile):
            raise VaultError("private failure")

    client, admin = client_for(settings_factory, vault=FailingVault())
    with client:
        response = client.put("/api/v0/settings", json=update(), headers=pair(client))
        assert response.status_code == 503
        assert admin.revision == 0 and admin.profile.provider == "mock"
    client, admin = client_for(settings_factory)
    with client:
        headers = pair(client)
        assert client.put("/api/v0/settings", json=update(), headers=headers).status_code == 200
        assert (
            client.put(
                "/api/v0/settings",
                json=update(base_url=BAILIAN_ROOTS[1], key_action="keep", api_key=None),
                headers=headers,
            ).status_code
            == 409
        )


def test_hot_update_new_requests_and_explicit_single_test(settings_factory):
    captured = []

    def factory(settings, managed):
        captured.append(
            (
                settings.llm_model,
                settings.llm_max_output_tokens,
                settings.llm_token_parameter,
                managed,
            )
        )
        provider = ScriptedProvider(reply_json())
        provider.name = settings.llm_provider
        return provider

    client, admin = client_for(settings_factory, factory=factory)
    with client:
        headers = pair(client)
        first = client.post("/api/v0/chat", json={"text": "hello"}).json()
        assert first["provider"] == "mock"
        saved = client.put(
            "/api/v0/settings",
            json=update(token_parameter="max_completion_tokens", json_mode=True),
            headers=headers,
        )
        assert saved.status_code == 200
        assert len(captured) == 1  # Saving never calls a Provider.
        assert (
            client.post("/api/v0/chat", json={"text": "unauthorized"}, headers=ORIGIN).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v0/chat",
                json={"text": "new", "session_id": first["session_id"]},
                headers=headers,
            ).status_code
            == 404
        )
        response = client.post("/api/v0/chat", json={"text": "new"}, headers=headers)
        assert response.json()["provider"] == "openai"
        assert captured[-1] == ("configured-model-id", 1024, "max_completion_tokens", True)
        assert (
            client.post(
                "/api/v0/settings/test", json={"revision": admin.revision}, headers=headers
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v0/settings/test",
                json={"revision": admin.revision, "confirm_paid_request": False},
                headers=headers,
            ).status_code
            == 422
        )
        count = len(captured)
        tested = client.post(
            "/api/v0/settings/test",
            json={"revision": admin.revision, "confirm_paid_request": True},
            headers=headers,
        )
        assert tested.json() == {"ok": True, "provider": "openai", "revision": admin.revision}
        assert len(captured) == count + 1
        assert captured[-1][1] == 256
        assert "reply" not in tested.json()


async def test_updates_reject_busy_chat_and_failed_test_is_not_verified(settings_factory):
    client, admin = client_for(settings_factory)
    async with client.app.router.lifespan_context(client.app):
        service = client.app.state.conversation
        key, session, _ = service.reserve(None)
        with pytest.raises(AppError) as error:
            admin.update(ProfileUpdate(**update()), service)
        assert error.value.code == "CONFIGURATION_BUSY"
        session.busy = False
        admin.update(
            ProfileUpdate(**update(provider="mock", key_action="clear", api_key=None)), service
        )
        admin.factory = lambda *_: ScriptedProvider("malformed")
        with pytest.raises(AppError):
            await admin.test_connection(admin.revision)
        assert not admin.tested and not admin.testing


@pytest.mark.parametrize(
    "ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "224.0.0.1"]
)
async def test_dns_rebinding_and_private_destinations_fail_at_connect(ip):
    async def resolver(*_, **kwargs):
        return [(2, 1, 6, "", (ip, 443))]

    backend = PublicNetworkBackend(resolver=resolver)
    with pytest.raises(Exception, match="destination rejected"):
        await backend.connect_tcp("dashscope.aliyuncs.com", 443)


async def test_public_resolution_is_pinned_to_numeric_ip():
    calls = []

    async def resolver(*_, **kwargs):
        return [(2, 1, 6, "", ("8.8.8.8", 443))]

    class Network:
        async def connect_tcp(self, host, port, **kwargs):
            calls.append((host, port))
            return object()

    await PublicNetworkBackend(resolver, Network()).connect_tcp("dashscope.aliyuncs.com", 443)
    assert calls == [("8.8.8.8", 443)]


def test_proxy_environment_fails_closed(monkeypatch):
    monkeypatch.setattr("app.settings.network.getproxies", lambda: {"https": "configured-proxy"})
    with pytest.raises(AppError) as error:
        secure_client(10)
    assert error.value.code == "SECURE_TRANSPORT_UNAVAILABLE"


def test_windows_vault_write_read_and_clear_with_fake_winapi():
    class API:
        blob = None
        allocations = []

        def CredWriteW(self, pointer, flags):
            credential = ctypes.cast(pointer, ctypes.POINTER(Credential)).contents
            self.blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            return True

        def CredReadW(self, name, kind, flags, output):
            buffer = (ctypes.c_ubyte * len(self.blob)).from_buffer_copy(self.blob)
            credential = Credential(CredentialBlobSize=len(self.blob), CredentialBlob=buffer)
            self.allocations.extend([buffer, credential])
            ctypes.cast(output, ctypes.POINTER(ctypes.POINTER(Credential)))[0] = ctypes.pointer(
                credential
            )
            return True

        def CredFree(self, pointer):
            pass

    api = API()
    vault = WindowsVault(api)
    vault.save(Profile(api_key=SecretStr("fictional-protected-key"), managed=True))
    assert vault.load().api_key.get_secret_value() == "fictional-protected-key"
    vault.save(Profile(api_key=None, managed=True))
    assert vault.load().api_key is None
    assert b"fictional-protected-key" not in api.blob


def test_saved_profile_loads_without_enabling_management(settings_factory):
    vault = MemoryVault()
    vault.save(
        Profile(
            provider="openai",
            base_url=BAILIAN_ROOTS[0],
            model="persisted-model",
            api_key=SecretStr("fictional-saved-key"),
            managed=True,
        )
    )
    admin = LocalSettings(settings_factory(), vault, None)
    assert admin.settings().llm_model == "persisted-model"
    assert admin.settings().chat_available
    assert not admin.enabled
    with TestClient(
        create_app(settings_factory(), local_admin=admin),
        base_url="http://localhost",
        client=("127.0.0.1", 20000),
    ) as client:
        assert client.post("/api/v0/settings/read", json={}, headers=ORIGIN).status_code == 403
        assert client.get("/api/v0/health").json()["provider"] == "openai"


def test_confirmation_requires_literal_true(settings_factory):
    client, admin = client_for(settings_factory)
    with client:
        headers = pair(client)
        for value in [False, 1, "true", None]:
            response = client.post(
                "/api/v0/settings/test",
                json={"confirm_paid_request": value, "revision": 0},
                headers=headers,
            )
            assert response.status_code == 422
