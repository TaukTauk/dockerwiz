"""Renders Jinja2 templates and writes Docker scaffold files to disk."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined

from dockerwiz.models import ProjectConfig

_BUILTIN_TEMPLATES = Path(__file__).parent / "templates"
_USER_TEMPLATES    = Path.home() / ".dockerwiz" / "templates"


class GeneratorError(Exception):
    """Raised when template rendering or file writing fails."""


def build_jinja_env(language: str, framework: str) -> Environment:
    """Build a Jinja2 environment with user-override templates taking precedence."""
    user_path    = _USER_TEMPLATES / language / framework
    builtin_path = _BUILTIN_TEMPLATES / language / framework

    loaders: list[FileSystemLoader] = []
    if user_path.is_dir():
        loaders.append(FileSystemLoader(str(user_path)))
    loaders.append(FileSystemLoader(str(builtin_path)))

    return Environment(  # noqa: S701  — templates are Dockerfile/YAML, not HTML
        loader=ChoiceLoader(loaders),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def build_context(config: ProjectConfig) -> dict[str, Any]:
    """Build the full template context dict from a ProjectConfig."""
    has_db = config.has_postgres or config.has_mysql

    return {
        "name":         config.name,
        "language":     config.language,
        "framework":    config.framework,
        "environment":  config.environment,
        "base_image":   config.base_image,
        "app_port":     config.app_port,
        "services":     config.services,

        "has_postgres": config.has_postgres,
        "has_mysql":    config.has_mysql,
        "has_redis":    config.has_redis,
        "has_nginx":    config.has_nginx,
        "has_mongo":    config.has_mongo,
        "has_db":       has_db,

        "is_dev":       config.is_dev,
        "is_prod":      config.is_prod,

        "db_user":      config.db_user,
        "db_password":  config.db_password,
        "db_name":      config.db_name,
        "db_port":      config.db_port,
    }


def _template_names(config: ProjectConfig) -> list[str]:
    """Return the list of template filenames to render for this config."""
    names = [
        "Dockerfile.j2",
        "docker-compose.yml.j2",
        ".dockerignore.j2",
        ".env.example.j2",
        "Makefile.j2",
    ]
    if config.is_dev:
        names.append("docker-compose.override.yml.j2")
    if config.has_nginx:
        names.append("nginx.conf.j2")
    return names


def render_templates(
    env: Environment,
    context: dict[str, Any],
    config: ProjectConfig,
) -> dict[str, str]:
    """Render all templates and return {output_filename: content}."""
    rendered: dict[str, str] = {}
    for template_name in _template_names(config):
        try:
            tmpl = env.get_template(template_name)
            output_name = template_name.removesuffix(".j2")
            rendered[output_name] = tmpl.render(**context)
        except Exception as exc:
            raise GeneratorError(f"Failed to render {template_name}: {exc}") from exc
    return rendered


def write_files(output_dir: Path, rendered: dict[str, str]) -> list[str]:
    """Write rendered files to output_dir atomically. Returns list of written paths."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GeneratorError(f"Cannot create output directory {output_dir}: {exc}") from exc

    written: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for filename, content in rendered.items():
            tmp_file = tmp_dir / filename
            tmp_file.write_text(content, encoding="utf-8")

        for filename in rendered:
            src  = tmp_dir / filename
            dest = output_dir / filename
            try:
                shutil.copy2(src, dest)
                written.append(str(dest))
            except OSError as exc:
                raise GeneratorError(f"Failed to write {dest}: {exc}") from exc

    return written


def generate(config: ProjectConfig) -> list[str]:
    """Generate Docker scaffold files for the given config.

    Returns the list of absolute file paths written.
    Raises GeneratorError on any failure.
    """
    env      = build_jinja_env(config.language, config.framework)
    context  = build_context(config)
    rendered = render_templates(env, context, config)
    output   = Path(config.output_directory) / config.name
    return write_files(output, rendered)
