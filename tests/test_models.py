"""Tests for models.py."""

import pytest
from pydantic import ValidationError

from dockerwiz.models import PartialProjectConfig, ProjectConfig


def _config(**overrides):
    defaults = {
        "name": "my-api",
        "language": "python",
        "framework": "fastapi",
        "base_image": "python:3.13-slim",
        "environment": "dev",
        "app_port": 8000,
        "services": [],
    }
    return ProjectConfig(**{**defaults, **overrides})


def test_basic_config():
    config = _config()
    assert config.name == "my-api"
    assert config.is_dev
    assert not config.is_prod


def test_prod_flags():
    config = _config(environment="prod")
    assert config.is_prod
    assert not config.is_dev


def test_service_helpers():
    config = _config(services=["postgres", "redis"], db_user="u", db_name="d", db_port=5432)
    assert config.has_postgres
    assert config.has_redis
    assert not config.has_mysql
    assert not config.has_nginx
    assert not config.has_mongo


def test_db_requires_user_and_name():
    with pytest.raises(ValidationError):
        _config(services=["postgres"])  # missing db_user and db_name


def test_db_with_credentials():
    config = _config(services=["postgres"], db_user="user", db_name="db", db_port=5432)
    assert config.db_user == "user"
    assert config.db_name == "db"


def test_partial_to_config():
    partial = PartialProjectConfig(
        name="test",
        language="python",
        framework="fastapi",
        base_image="python:3.13-slim",
        environment="dev",
        app_port=8000,
    )
    config = partial.to_config()
    assert config.name == "test"


def test_partial_to_config_missing_required():
    partial = PartialProjectConfig(name="test")  # missing many required fields
    with pytest.raises(ValidationError):
        partial.to_config()
