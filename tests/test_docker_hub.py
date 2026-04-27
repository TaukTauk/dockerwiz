"""Tests for docker_hub.py — mocks httpx with respx."""

import pytest
import respx
from httpx import Response

from dockerwiz.docker_hub import VersionCache, fetch_all_versions, fetch_image_versions
from dockerwiz.fallbacks import FALLBACK_VERSIONS


@pytest.mark.asyncio
@respx.mock
async def test_fetch_live_python_tags():
    respx.get(
        "https://hub.docker.com/v2/repositories/library/python/tags?page_size=100"
    ).mock(return_value=Response(200, json={
        "results": [
            {"name": "3.13-slim"},
            {"name": "3.12-slim"},
            {"name": "3.11-slim"},
            {"name": "latest"},
            {"name": "3.13"},
        ]
    }))

    tags, is_live = await fetch_image_versions("python", timeout_seconds=5)
    assert is_live is True
    assert "3.13-slim" in tags
    # "latest" and "3.13" should be filtered out
    assert "latest" not in tags
    assert "3.13" not in tags


@pytest.mark.asyncio
@respx.mock
async def test_fetch_offline_fallback():
    respx.get(
        "https://hub.docker.com/v2/repositories/library/python/tags?page_size=100"
    ).mock(side_effect=Exception("network error"))

    tags, is_live = await fetch_image_versions("python", timeout_seconds=1)
    assert is_live is False
    assert tags == FALLBACK_VERSIONS["python"]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_non_200_falls_back():
    respx.get(
        "https://hub.docker.com/v2/repositories/library/python/tags?page_size=100"
    ).mock(return_value=Response(503))

    tags, is_live = await fetch_image_versions("python", timeout_seconds=5)
    assert is_live is False
    assert tags == FALLBACK_VERSIONS["python"]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_all_versions_offline(mocker):
    mocker.patch("dockerwiz.docker_hub._load_cache", return_value=VersionCache())

    for image in ["python", "golang", "node"]:
        respx.get(
            f"https://hub.docker.com/v2/repositories/library/{image}/tags?page_size=100"
        ).mock(side_effect=Exception("offline"))

    versions, is_live = await fetch_all_versions(
        ["python", "golang", "node"], ttl_hours=24
    )
    assert is_live is False
    assert versions["python"] == FALLBACK_VERSIONS["python"]
    assert versions["golang"] == FALLBACK_VERSIONS["golang"]
    assert versions["node"]   == FALLBACK_VERSIONS["node"]
