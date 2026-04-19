"""User config read/write for ~/.dockerwiz/config.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w
from pydantic import BaseModel, Field, ValidationError

CONFIG_DIR  = Path.home() / ".dockerwiz"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_CONFIG_HEADER = (
    "# ~/.dockerwiz/config.toml\n"
    "# This file is managed by dockerwiz.\n"
    "# Edit manually or use: dockerwiz config set <key> <value>\n\n"
)


class DefaultsConfig(BaseModel):
    language:    str | None = None
    framework:   str | None = None
    environment: str        = "dev"
    db:          str | None = None


class OutputConfig(BaseModel):
    directory: str = "."


class CacheConfig(BaseModel):
    ttl_hours: int = Field(default=24, ge=1, le=720)


class DockerHubConfig(BaseModel):
    timeout_seconds: int = Field(default=5, ge=1, le=30)


class UserConfig(BaseModel):
    defaults:   DefaultsConfig  = Field(default_factory=DefaultsConfig)
    output:     OutputConfig    = Field(default_factory=OutputConfig)
    cache:      CacheConfig     = Field(default_factory=CacheConfig)
    docker_hub: DockerHubConfig = Field(default_factory=DockerHubConfig)


# Maps dot-notation CLI keys to (section_attr, field_attr)
CONFIG_KEY_MAP: dict[str, tuple[str, str]] = {
    "default.language":           ("defaults",   "language"),
    "default.framework":          ("defaults",   "framework"),
    "default.environment":        ("defaults",   "environment"),
    "default.db":                 ("defaults",   "db"),
    "output.directory":           ("output",     "directory"),
    "cache.ttl_hours":            ("cache",      "ttl_hours"),
    "docker_hub.timeout_seconds": ("docker_hub", "timeout_seconds"),
}


def load_config() -> UserConfig:
    """Load user config from ~/.dockerwiz/config.toml, creating it if absent."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        config = UserConfig()
        save_config(config)
        return config

    with CONFIG_FILE.open("rb") as fh:
        raw = tomllib.load(fh)

    try:
        return UserConfig.model_validate(raw)
    except ValidationError:
        # Bad manually-edited file — fall back to defaults (a warning is shown by callers)
        return UserConfig()


def save_config(config: UserConfig) -> None:
    """Write UserConfig to ~/.dockerwiz/config.toml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    content = _CONFIG_HEADER + tomli_w.dumps(config.model_dump(exclude_none=True))
    CONFIG_FILE.write_text(content, encoding="utf-8")


def get_config_value(config: UserConfig, key: str) -> str | None:
    """Return the string value for a dot-notation config key."""
    if key not in CONFIG_KEY_MAP:
        return None
    section_attr, field_attr = CONFIG_KEY_MAP[key]
    return str(getattr(getattr(config, section_attr), field_attr))


def set_config_value(config: UserConfig, key: str, value: str | None) -> UserConfig:
    """Return a new UserConfig with the given dot-notation key set to value."""
    if key not in CONFIG_KEY_MAP:
        raise ValueError(f"Unknown config key: {key}")

    section_attr, field_attr = CONFIG_KEY_MAP[key]
    section_obj = getattr(config, section_attr)
    field_info  = section_obj.model_fields[field_attr]

    # Cast to the correct type
    annotation = field_info.annotation
    typed_value: object
    if value is None:
        typed_value = None
    elif annotation in (int, "int | None") or str(annotation) in ("int", "int | None"):
        typed_value = int(value)
    else:
        typed_value = value

    updated_section = section_obj.model_copy(update={field_attr: typed_value})
    return config.model_copy(update={section_attr: updated_section})


def unset_config_value(config: UserConfig, key: str) -> UserConfig:
    """Clear a dot-notation config key (set to None or its default)."""
    return set_config_value(config, key, None)
