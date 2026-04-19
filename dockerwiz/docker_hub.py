"""Docker Hub API client with local cache and offline fallback."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

from dockerwiz.fallbacks import FALLBACK_VERSIONS

_CACHE_FILE = Path.home() / ".dockerwiz" / "cache.json"
_HUB_URL    = "https://hub.docker.com/v2/repositories/library/{image}/tags?page_size=100"

# Tags that look like real versioned variants we want to show
_TAG_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\d+\.\d+-slim$"),
    "golang": re.compile(r"^\d+\.\d+-alpine$"),
    "node":   re.compile(r"^\d+-alpine$"),
}


class ImageCache(BaseModel):
    tags:       list[str]
    fetched_at: datetime


class VersionCache(BaseModel):
    python: ImageCache | None = None
    golang: ImageCache | None = None
    node:   ImageCache | None = None


def _load_cache() -> VersionCache:
    if not _CACHE_FILE.exists():
        return VersionCache()
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        return VersionCache.model_validate(data)
    except Exception:  # noqa: BLE001
        return VersionCache()


def _save_cache(cache: VersionCache) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(cache.model_dump_json(indent=2), encoding="utf-8")


def _is_fresh(image_cache: ImageCache, ttl_hours: int) -> bool:
    fetched = image_cache.fetched_at
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=UTC)
    age = datetime.now(UTC) - fetched
    return age.total_seconds() < ttl_hours * 3600


def _filter_tags(image: str, raw_tags: list[str]) -> list[str]:
    """Filter raw Docker Hub tags down to meaningful versioned variants."""
    pattern = _TAG_PATTERNS.get(image)
    if pattern is None:
        return raw_tags[:10]
    matched = [t for t in raw_tags if pattern.match(t)]
    matched.sort(key=lambda t: [int(x) for x in re.findall(r"\d+", t)], reverse=True)
    return matched


async def fetch_image_versions(
    image: str,
    timeout_seconds: int = 5,
) -> tuple[list[str], bool]:
    """Fetch image version tags from Docker Hub.

    Returns (tags, is_live). On any failure, returns (fallback_tags, False).
    Never raises.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.get(_HUB_URL.format(image=image))
            resp.raise_for_status()
            data = resp.json()
            raw  = [r["name"] for r in data.get("results", [])]
            return _filter_tags(image, raw), True
    except Exception:  # noqa: BLE001
        return FALLBACK_VERSIONS.get(image, []), False


async def fetch_all_versions(
    images: list[str],
    ttl_hours: int = 24,
    timeout_seconds: int = 5,
) -> tuple[dict[str, list[str]], bool]:
    """Fetch versions for all requested images, using cache where fresh.

    Returns (versions_dict, is_live). is_live is False if any image fell back.
    """
    import asyncio  # noqa: PLC0415 — local import avoids issues in sync contexts

    cache   = _load_cache()
    results: dict[str, list[str]] = {}
    updated = False
    all_live = True

    stale_images: list[str] = []
    for image in images:
        cached: ImageCache | None = getattr(cache, image, None)
        if cached and _is_fresh(cached, ttl_hours):
            results[image] = cached.tags
        else:
            stale_images.append(image)

    if stale_images:
        tasks = [fetch_image_versions(image, timeout_seconds) for image in stale_images]
        fetched = await asyncio.gather(*tasks)
        for image, (tags, is_live) in zip(stale_images, fetched, strict=False):
            results[image] = tags
            if is_live:
                setattr(cache, image, ImageCache(
                    tags=tags,
                    fetched_at=datetime.now(UTC),
                ))
                updated = True
            else:
                all_live = False

    if updated:
        _save_cache(cache)

    return results, all_live
