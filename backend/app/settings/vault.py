import ctypes
import json
import os
from ctypes import wintypes
from typing import Protocol

from app.settings.models import Profile


class VaultError(Exception):
    pass


class Vault(Protocol):
    kind: str

    def load(self) -> Profile | None: ...
    def save(self, profile: Profile) -> None: ...


class MemoryVault:
    kind = "memory-only"

    def __init__(self):
        self.profile: Profile | None = None

    def load(self) -> Profile | None:
        return self.profile

    def save(self, profile: Profile) -> None:
        self.profile = profile


class Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsVault:
    """One protected Generic Credential; no plaintext config/key files or fallback."""

    kind = "windows-credential-manager"
    target = "Desktop-NOMI/AIConfiguration/v1"

    def __init__(self, api=None):
        if api is None:
            if os.name != "nt":
                raise VaultError("Windows credential storage unavailable")
            try:
                api = ctypes.WinDLL("Advapi32.dll", use_last_error=True, winmode=0x00000800)
            except OSError:
                raise VaultError("Windows credential API unavailable") from None
            api.CredReadW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.POINTER(ctypes.POINTER(Credential)),
            ]
            api.CredReadW.restype = wintypes.BOOL
            api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
            api.CredWriteW.restype = wintypes.BOOL
            api.CredFree.argtypes = [ctypes.c_void_p]
            api.CredFree.restype = None
        self.api = api

    def load(self) -> Profile | None:
        pointer = ctypes.POINTER(Credential)()
        if not self.api.CredReadW(self.target, 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == 1168:
                return None
            raise VaultError("Credential read failed")
        try:
            if pointer.contents.CredentialBlobSize > 2560:
                raise VaultError("Invalid credential record")
            raw = ctypes.string_at(
                pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize
            )
            return Profile.model_validate_json(raw)
        except Exception:
            raise VaultError("Credential record invalid") from None
        finally:
            ctypes.memset(pointer.contents.CredentialBlob, 0, pointer.contents.CredentialBlobSize)
            self.api.CredFree(pointer)

    def save(self, profile: Profile) -> None:
        # model_dump_json deliberately masks SecretStr; unwrap only inside the protected vault.
        value = profile.model_dump(mode="json")
        value["api_key"] = profile.api_key.get_secret_value() if profile.api_key else None
        raw = json.dumps(value, ensure_ascii=True).encode("utf-8")
        if len(raw) > 2560:
            raise VaultError("Credential record too large")
        buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        credential = Credential(
            Type=1,
            TargetName=self.target,
            Persist=2,
            UserName="Desktop-NOMI",
            CredentialBlobSize=len(raw),
            CredentialBlob=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
        )
        try:
            if not self.api.CredWriteW(ctypes.byref(credential), 0):
                raise VaultError("Credential write failed")
        finally:
            ctypes.memset(buffer, 0, len(raw))


def platform_vault() -> Vault:
    return WindowsVault() if os.name == "nt" else MemoryVault()
