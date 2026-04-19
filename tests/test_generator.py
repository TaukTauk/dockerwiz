"""Tests for generator.py — uses snapshot testing."""

from dockerwiz.generator import build_context, build_jinja_env, render_templates
from dockerwiz.models import ProjectConfig


def _make_config(**overrides):
    defaults = {
        "name": "my-api",
        "output_directory": ".",
        "language": "python",
        "framework": "fastapi",
        "base_image": "python:3.13-slim",
        "environment": "dev",
        "app_port": 8000,
        "services": [],
    }
    return ProjectConfig(**{**defaults, **overrides})


def test_build_context_service_helpers():
    config  = _make_config(services=["postgres", "redis"], db_user="u", db_name="d", db_port=5432)
    context = build_context(config)
    assert context["has_postgres"] is True
    assert context["has_redis"]    is True
    assert context["has_mysql"]    is False
    assert context["is_dev"]       is True
    assert context["is_prod"]      is False


def test_render_fastapi_dev(snapshot):
    config   = _make_config()
    env      = build_jinja_env("python", "fastapi")
    context  = build_context(config)
    rendered = render_templates(env, context, config)

    assert "Dockerfile" in rendered
    assert "docker-compose.yml" in rendered
    assert "docker-compose.override.yml" in rendered  # dev only
    assert ".dockerignore" in rendered
    assert ".env.example" in rendered
    assert "Makefile" in rendered

    snapshot.assert_match(rendered["Dockerfile"], "fastapi_dev_Dockerfile")
    snapshot.assert_match(rendered["docker-compose.yml"], "fastapi_dev_docker-compose.yml")


def test_render_fastapi_prod_no_override(snapshot):
    config   = _make_config(environment="prod")
    env      = build_jinja_env("python", "fastapi")
    context  = build_context(config)
    rendered = render_templates(env, context, config)

    assert "docker-compose.override.yml" not in rendered
    snapshot.assert_match(rendered["Dockerfile"], "fastapi_prod_Dockerfile")


def test_render_with_postgres(snapshot):
    config  = _make_config(
        services=["postgres"],
        db_user="myuser",
        db_name="mydb",
        db_port=5432,
    )
    env     = build_jinja_env("python", "fastapi")
    context = build_context(config)
    rendered = render_templates(env, context, config)

    assert "DB_USER" in rendered[".env.example"]
    assert "psql" in rendered["Makefile"]
    snapshot.assert_match(rendered["docker-compose.yml"], "fastapi_dev_postgres_docker-compose.yml")


def test_render_with_nginx():
    config  = _make_config(services=["nginx"])
    env     = build_jinja_env("python", "fastapi")
    context = build_context(config)
    rendered = render_templates(env, context, config)
    assert "nginx.conf" in rendered
    assert "upstream app" in rendered["nginx.conf"]


def test_render_go_gin():
    config  = _make_config(language="go", framework="gin", base_image="golang:1.23-alpine",
                           app_port=8080)
    env     = build_jinja_env("go", "gin")
    context = build_context(config)
    rendered = render_templates(env, context, config)
    assert "air" in rendered["Dockerfile"].lower()


def test_render_node_express():
    config  = _make_config(language="node", framework="express", base_image="node:22-alpine",
                           app_port=3000)
    env     = build_jinja_env("node", "express")
    context = build_context(config)
    rendered = render_templates(env, context, config)
    assert "nodemon" in rendered["Dockerfile"]
