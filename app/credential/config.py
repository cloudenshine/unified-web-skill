"""CredentialStore — structured YAML/JSON config layer for platform credentials.

Loads credentials in priority order:
  1. ~/.unified-web-skill/credentials.yaml  (primary, YAML)
  2. ~/.unified-web-skill/credentials.json  (fallback if YAML missing)
  3. Existing .env values (fallback for backward compatibility)

Supports optional AES-256-GCM encryption when UWS_MASTER_KEY is set.
"""

from __future__ import annotations

import json
import logging
import os
import platform as os_platform
import stat
import subprocess
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# -- Known platforms -------------------------------------------------------
PLATFORMS = frozenset({"twitter", "xiaohongshu", "xueqiu", "bilibili"})


def _cred_dir() -> Path:
    """Return ~/.unified-web-skill/, creating it if needed."""
    p = Path.home() / ".unified-web-skill"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _yaml_path() -> Path:
    return _cred_dir() / "credentials.yaml"


def _json_path() -> Path:
    return _cred_dir() / "credentials.json"


# -- Security helpers ------------------------------------------------------

def _restrict_permissions(path: Path) -> None:
    """Set restrictive permissions on *path*.

    - POSIX: chmod 0o600 (owner read/write only).
    - Windows: icacls to remove inheritance and grant only current user R/W.
    """
    try:
        if os_platform.system() != "Windows":
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        else:
            user = os.environ.get("USERNAME", "")
            if user:
                cmd = [
                    "icacls", str(path),
                    "/inheritance:r",
                    "/grant:r", f"{user}:(R,W)",
                ]
                subprocess.run(cmd, check=False, capture_output=True, timeout=10)
    except Exception as exc:
        _logger.warning("Failed to restrict permissions on %s: %s", path, exc)


def mask_value(val: str | None, show_first: int = 3, show_last: int = 3) -> str:
    """Mask a sensitive string for safe display.

    - None or empty -> empty string.
    - Length <= 6 -> "***".
    - Otherwise -> "abc...xyz" showing first/last 3 chars.
    """
    if not val:
        return ""
    val = str(val)
    if len(val) <= 6:
        return "***"
    return f"{val[:show_first]}...{val[-show_last:]}"


# -- Optional AES-GCM encryption -------------------------------------------

def _master_key() -> bytes | None:
    """Return 32-byte AES key from UWS_MASTER_KEY env var (64 hex chars)."""
    raw = os.environ.get("UWS_MASTER_KEY", "")
    if not raw:
        return None
    try:
        key = bytes.fromhex(raw)
    except (ValueError, TypeError):
        _logger.warning("UWS_MASTER_KEY not valid hex -- falling back to plaintext")
        return None
    if len(key) != 32:
        _logger.warning("UWS_MASTER_KEY must be 32 bytes (64 hex chars) -- fallback to plaintext")
        return None
    return key


def _encrypt(plaintext: str, key: bytes) -> str | None:
    """AES-256-GCM encrypt. Returns hex ciphertext or None if cryptography missing."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return None
    nonce = os.urandom(12)
    aad = b"unified-web-skill-credential-v1"
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), aad)
    actual_ct = ct[:-16]
    tag = ct[-16:]
    return f"{nonce.hex()}|{actual_ct.hex()}|{tag.hex()}"


def _decrypt(ciphertext: str, key: bytes) -> str | None:
    """Reverse _encrypt."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return None
    try:
        parts = ciphertext.split("|")
        if len(parts) != 3:
            return None
        nonce = bytes.fromhex(parts[0])
        actual_ct = bytes.fromhex(parts[1])
        tag = bytes.fromhex(parts[2])
        aad = b"unified-web-skill-credential-v1"
        plain = AESGCM(key).decrypt(nonce, actual_ct + tag, aad)
        return plain.decode("utf-8")
    except Exception as exc:
        _logger.warning("Decryption failed: %s", exc)
        return None


# -- CredentialStore -------------------------------------------------------

class CredentialStore:
    """Singleton credential manager.

    Usage::

        store = CredentialStore.get_instance()
        token = store.get("twitter", "auth_token")
        store.set("twitter", "auth_token", "new_value")
        status = store.doctor()
    """

    _instance: CredentialStore | None = None

    def __init__(self) -> None:
        if CredentialStore._instance is not None:
            raise RuntimeError("Use CredentialStore.get_instance() instead")
        self._data: dict[str, dict[str, str]] = {}
        self._dirty = False
        self._master_key = _master_key()
        self._load()

    # -- Singleton ---------------------------------------------------------

    @classmethod
    def get_instance(cls) -> CredentialStore:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # -- Load / Save -------------------------------------------------------

    def _load(self) -> None:
        """Load credentials from disk, falling back to .env values."""
        yp = _yaml_path()
        jp = _json_path()
        loaded = False

        if yp.exists():
            try:
                import yaml
                with open(yp, "r", encoding="utf-8") as fh:
                    raw = yaml.safe_load(fh)
                if isinstance(raw, dict):
                    self._data = self._decrypt_all(raw)
                    _logger.info("Loaded credentials from %s", yp)
                    loaded = True
            except Exception as exc:
                _logger.warning("Failed to load YAML credentials: %s", exc)

        if not loaded and jp.exists():
            try:
                with open(jp, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                self._data = self._decrypt_all(raw)
                _logger.info("Loaded credentials from %s", jp)
                loaded = True
            except Exception as exc:
                _logger.warning("Failed to load JSON credentials: %s", exc)

        # Fallback to .env for missing platforms
        if not loaded or not self._data:
            self._load_env_fallback()

    def _load_env_fallback(self) -> None:
        env_map: dict[str, dict[str, str]] = {}

        for platform, keys in env_map.items():
            if platform not in self._data:
                self._data[platform] = {}
            for k, v in keys.items():
                if k not in self._data[platform]:
                    self._data[platform][k] = v

    def save(self) -> None:
        """Write credentials to disk (YAML preferred, JSON fallback)."""
        if not self._dirty:
            return
        raw = self._encrypt_all(self._data)
        yp = _yaml_path()
        try:
            import yaml
            with open(yp, "w", encoding="utf-8") as fh:
                yaml.dump(raw, fh, default_flow_style=False, allow_unicode=True)
            _restrict_permissions(yp)
            _logger.info("Saved credentials to %s", yp)
        except ImportError:
            jp = _json_path()
            with open(jp, "w", encoding="utf-8") as fh:
                json.dump(raw, fh, ensure_ascii=False, indent=2)
            _restrict_permissions(jp)
            _logger.info("Saved credentials to %s (JSON fallback)", jp)
        self._dirty = False

    # -- Encryption wrappers -----------------------------------------------

    def _encrypt_val(self, plaintext: str) -> str:
        if self._master_key:
            encrypted = _encrypt(plaintext, self._master_key)
            if encrypted is not None:
                return f"!enc:{encrypted}"
        return plaintext

    def _decrypt_val(self, stored: str) -> str:
        if stored.startswith("!enc:") and self._master_key:
            plain = _decrypt(stored[5:], self._master_key)
            if plain is not None:
                return plain
            _logger.warning("Failed to decrypt a credential value")
        return stored

    def _encrypt_all(self, data: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        if not self._master_key:
            return data
        out: dict[str, dict[str, str]] = {}
        for platform, kv in data.items():
            out[platform] = {k: self._encrypt_val(v) for k, v in kv.items()}
        return out

    def _decrypt_all(self, raw: dict[str, Any]) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for platform, kv in raw.items():
            if not isinstance(kv, dict):
                continue
            out[str(platform)] = {
                str(k): self._decrypt_val(str(v)) for k, v in kv.items()
            }
        return out

    # -- Public API --------------------------------------------------------

    def get(self, platform: str, key: str, default: str = "") -> str:
        return self._data.get(platform, {}).get(key, default)

    def get_all(self, platform: str) -> dict[str, str]:
        return dict(self._data.get(platform, {}))

    def set(self, platform: str, key: str, value: str) -> None:
        self._data.setdefault(platform, {})[key] = value
        self._dirty = True

    def set_platform(self, platform: str, kv: dict[str, str]) -> None:
        self._data[platform] = dict(kv)
        self._dirty = True

    def remove(self, platform: str, key: str) -> bool:
        exists = platform in self._data and key in self._data[platform]
        if exists:
            del self._data[platform][key]
            self._dirty = True
        return exists

    def list_platforms(self) -> list[str]:
        return sorted(self._data.keys())

    def doctor(self) -> dict[str, Any]:
        platforms: list[dict[str, Any]] = []
        for name in sorted(self._data.keys()):
            kv = self._data[name]
            entries = {k: mask_value(v) for k, v in kv.items()}
            platforms.append({
                "name": name,
                "keys": sorted(kv.keys()),
                "masked": entries,
                "count": len(kv),
            })

        yp = _yaml_path()
        jp = _json_path()
        source = ""
        if yp.exists():
            source = str(yp)
        elif jp.exists():
            source = str(jp)

        return {
            "ok": True,
            "platforms": platforms,
            "total_platforms": len(platforms),
            "encryption": self._master_key is not None,
            "file": source,
            "dir": str(_cred_dir()),
        }

