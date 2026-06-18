"""Dynamic provider loading from declarative JSON manifest.

Supports:
  - Merging JSON profiles with built-in Python profiles
  - Dynamic import of engine classes by module_path
  - Runtime registration into EngineManager
"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .provider_config import ProviderProfile

if TYPE_CHECKING:
    from .manager import EngineManager
    from .base import Engine

logger = logging.getLogger(__name__)


def load_provider_profiles(path: str | Path) -> list[ProviderProfile]:
    """Load provider profiles from a JSON manifest file.

    The JSON is a list of dicts, each matching ProviderProfile fields.
    Unknown dict keys are silently ignored.
    """
    path = Path(path)
    if not path.exists():
        logger.warning("Provider manifest not found: %s", path)
        return []

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        logger.error("Provider manifest must be a list, got %s", type(raw).__name__)
        return []

    profiles: list[ProviderProfile] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            # Build capabilities set from string list
            caps = entry.pop("capabilities", [])
            profile = ProviderProfile(
                name=entry.pop("name"),
                category=entry.pop("category"),
                capabilities=set(caps),
                **{k: v for k, v in entry.items() if k in ProviderProfile.__dataclass_fields__},
            )
            profiles.append(profile)
        except Exception as exc:
            logger.warning("Skipping invalid provider entry %r: %s", entry.get("name", "?"), exc)

    logger.info("Loaded %d provider profiles from %s", len(profiles), path)
    return profiles


def _import_engine_class(module_path: str) -> type[Engine] | None:
    """Dynamically import an engine class from 'module:ClassName' path.

    Example: ``"app.engines.providers.jina_reader:JinaReaderEngine"``
    """
    try:
        mod_path, cls_name = module_path.split(":", 1)
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        return cls
    except (ImportError, AttributeError, ValueError) as exc:
        logger.warning("Failed to import engine %r: %s", module_path, exc)
        return None


def register_from_profiles(
    manager: "EngineManager",
    profiles: list[ProviderProfile],
) -> int:
    """Register engines from enabled provider profiles.

    For each enabled profile with a ``module_path``, dynamically import
    the engine class and register it with the manager.

    Returns the number of successfully registered engines.
    """
    count = 0
    for profile in profiles:
        if not profile.enabled:
            continue
        if not profile.module_path:
            continue
        engine_cls = _import_engine_class(profile.module_path)
        if engine_cls is None:
            continue
        try:
            engine = engine_cls()
            manager.register(engine)
            logger.info("Registered provider: %s (%s)", profile.name, profile.module_path)
            count += 1
        except Exception as exc:
            logger.warning("Failed to instantiate engine %s: %s", profile.name, exc)

    return count
