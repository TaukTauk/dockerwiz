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


# ── Dependency file generation ─────────────────────────────────────────────────

def test_python_fastapi_generates_requirements_txt():
    config   = _make_config()
    env      = build_jinja_env("python", "fastapi")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert "requirements.txt" in rendered
    assert "fastapi" in rendered["requirements.txt"]
    assert "uvicorn" in rendered["requirements.txt"]


def test_python_django_generates_requirements_txt():
    config   = _make_config(framework="django")
    env      = build_jinja_env("python", "django")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert "requirements.txt" in rendered
    assert "django" in rendered["requirements.txt"]
    assert "gunicorn" in rendered["requirements.txt"]


def test_node_express_generates_package_json():
    config   = _make_config(language="node", framework="express", base_image="node:22-alpine",
                            app_port=3000)
    env      = build_jinja_env("node", "express")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert "package.json" in rendered
    assert "express" in rendered["package.json"]
    assert "my-api" in rendered["package.json"]  # project name injected


def test_node_nestjs_generates_package_json():
    config   = _make_config(language="node", framework="nestjs", base_image="node:22-alpine",
                            app_port=3000)
    env      = build_jinja_env("node", "nestjs")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert "package.json" in rendered
    assert "@nestjs/core" in rendered["package.json"]


def test_go_gin_generates_go_mod():
    config   = _make_config(language="go", framework="gin", base_image="golang:1.23-alpine",
                            app_port=8080)
    env      = build_jinja_env("go", "gin")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert "go.mod" in rendered
    assert "module my-api" in rendered["go.mod"]
    assert "gin-gonic/gin" in rendered["go.mod"]


def test_go_does_not_generate_go_sum():
    config   = _make_config(language="go", framework="gin", base_image="golang:1.23-alpine",
                            app_port=8080)
    env      = build_jinja_env("go", "gin")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert "go.sum" not in rendered


def test_go_dockerfile_does_not_copy_go_sum():
    config   = _make_config(language="go", framework="gin", base_image="golang:1.23-alpine",
                            app_port=8080)
    env      = build_jinja_env("go", "gin")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert "COPY go.mod go.sum" not in rendered["Dockerfile"]
    assert "COPY go.mod" in rendered["Dockerfile"]


def test_go_dev_generates_air_toml():
    config   = _make_config(language="go", framework="gin", base_image="golang:1.23-alpine",
                            app_port=8080)
    env      = build_jinja_env("go", "gin")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert ".air.toml" in rendered
    assert "tmp/main" in rendered[".air.toml"]


def test_go_prod_does_not_generate_air_toml():
    config   = _make_config(language="go", framework="gin", base_image="golang:1.23-alpine",
                            app_port=8080, environment="prod")
    env      = build_jinja_env("go", "gin")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    assert ".air.toml" not in rendered


# ── Host port rendering ────────────────────────────────────────────────────────

def test_build_context_host_db_port_defaults_to_5432_for_postgres():
    config  = _make_config(services=["postgres"], db_user="u", db_name="d", db_port=5432)
    context = build_context(config)
    assert context["host_db_port"] == 5432


def test_build_context_host_db_port_defaults_to_3306_for_mysql():
    config  = _make_config(services=["mysql"], db_user="u", db_name="d", db_port=3306)
    context = build_context(config)
    assert context["host_db_port"] == 3306


def test_build_context_host_db_port_uses_override():
    config  = _make_config(services=["postgres"], db_user="u", db_name="d", db_port=5432,
                           host_db_port=5433)
    context = build_context(config)
    assert context["host_db_port"] == 5433


def test_build_context_host_redis_port_defaults_to_6379():
    config  = _make_config()
    context = build_context(config)
    assert context["host_redis_port"] == 6379


def test_build_context_host_nginx_port_defaults_to_80():
    config  = _make_config()
    context = build_context(config)
    assert context["host_nginx_port"] == 80


def test_compose_bakes_in_host_db_port(snapshot):
    config  = _make_config(
        services=["postgres"],
        db_user="myuser",
        db_name="mydb",
        db_port=5432,
        host_db_port=5433,
    )
    env     = build_jinja_env("python", "fastapi")
    context = build_context(config)
    rendered = render_templates(env, context, config)
    compose = rendered["docker-compose.yml"]
    assert '"5433:5432"' in compose
    assert '"5432:5432"' not in compose


def test_compose_nginx_uses_host_nginx_port():
    config  = _make_config(services=["nginx"], host_nginx_port=8080)
    env     = build_jinja_env("python", "fastapi")
    context = build_context(config)
    rendered = render_templates(env, context, config)
    assert '"8080:80"' in rendered["docker-compose.yml"]


# ── Makefile init target ───────────────────────────────────────────────────────

def test_makefile_has_init_target():
    config   = _make_config()
    env      = build_jinja_env("python", "fastapi")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    makefile = rendered["Makefile"]
    assert "init" in makefile
    assert ".env.example .env" in makefile or "cp .env.example .env" in makefile


def test_makefile_up_depends_on_env():
    config   = _make_config()
    env      = build_jinja_env("python", "fastapi")
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    lines    = rendered["Makefile"].splitlines()
    up_line  = next((line for line in lines if line.startswith("up:")), None)
    assert up_line is not None
    assert ".env" in up_line
