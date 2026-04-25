"""CLI entrypoint for dockerwiz. Registers all commands and handles errors."""

from __future__ import annotations

import asyncio
import traceback
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dockerwiz.config import (
    CONFIG_KEY_MAP,
    get_config_value,
    load_config,
    save_config,
    set_config_value,
    unset_config_value,
)
from dockerwiz.docker_client import (
    DockerNotAvailableError,
    clean_resources,
    exec_shell,
    list_unused_resources,
    require_docker,
    run_health_check,
    start_containers,
)
from dockerwiz.docker_hub import fetch_all_versions
from dockerwiz.services import SERVICES
from dockerwiz.stacks import STACKS

console = Console()
err_console = Console(stderr=True, style="bold red")

_LOG_DIR  = Path.home() / ".dockerwiz" / "logs"
_LOG_FILE = _LOG_DIR / "debug.log"

app = typer.Typer(
    name="dockerwiz",
    help="Generate production-ready Docker setups through an interactive terminal wizard.",
    add_completion=False,
    no_args_is_help=True,
)

list_app = typer.Typer(help="List supported stacks and services.", no_args_is_help=True)
app.add_typer(list_app, name="list")


def _log_exception(exc: Exception) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{'=' * 60}\n")
        traceback.print_exc(file=fh)


# ── dockerwiz new ──────────────────────────────────────────────────────────────

@app.command("new")
def new_cmd() -> None:
    """Launch the TUI wizard to generate a Docker setup."""
    from dockerwiz.tui.app import DockerWizApp  # noqa: PLC0415

    user_config = load_config()

    console.print("Fetching Docker Hub image versions...", style="dim")
    try:
        versions, is_live = asyncio.run(
            fetch_all_versions(
                ["python", "golang", "node"],
                ttl_hours=user_config.cache.ttl_hours,
                timeout_seconds=user_config.docker_hub.timeout_seconds,
            )
        )
    except Exception as exc:  # noqa: BLE001
        _log_exception(exc)
        versions = {}
        is_live  = False

    try:
        wizard_app = DockerWizApp(
            user_config=user_config,
            available_versions=versions,
            is_live=is_live,
        )
        wizard_app.run()
    except Exception as exc:  # noqa: BLE001
        _log_exception(exc)
        err_console.print(f"Unexpected error: {exc}")
        err_console.print(f"Details written to {_LOG_FILE}")
        raise typer.Exit(1) from exc


# ── dockerwiz health ───────────────────────────────────────────────────────────

@app.command("health")
def health_cmd() -> None:
    """Diagnose the Docker setup in the current directory."""
    results = run_health_check()
    for r in results:
        icon  = "[green]OK  [/green]" if r["status"] == "OK" else "[red]FAIL[/red]"
        console.print(f"  [{icon}]   {r['service']:<25} {r['message']}")

    fails = sum(1 for r in results if r["status"] == "FAIL")
    if fails:
        console.print(f"\n  {fails} failure(s).")
    else:
        console.print("\n  All checks passed.")


# ── dockerwiz shell ────────────────────────────────────────────────────────────

@app.command("shell")
def shell_cmd(
    service: Annotated[str, typer.Argument(help="Service name from docker-compose.yml")],
) -> None:
    """Exec into a running container."""
    try:
        exec_shell(service)
    except DockerNotAvailableError as exc:
        err_console.print(str(exc))
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        _log_exception(exc)
        err_console.print(f"Unexpected error: {exc}")
        raise typer.Exit(1) from exc


# ── dockerwiz start ────────────────────────────────────────────────────────────

@app.command("start")
def start_cmd(
    service: Annotated[str | None, typer.Argument(help="Service name to start (default: all)")] = None,  # noqa: E501
) -> None:
    """Start Docker Compose services for the current project."""
    try:
        start_containers(service)
    except DockerNotAvailableError as exc:
        err_console.print(str(exc))
        raise typer.Exit(1) from exc
    except FileNotFoundError as exc:
        err_console.print(str(exc))
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        _log_exception(exc)
        err_console.print(f"Unexpected error: {exc}")
        raise typer.Exit(1) from exc


# ── dockerwiz clean ────────────────────────────────────────────────────────────

@app.command("clean")
def clean_cmd(
    all_resources: Annotated[bool, typer.Option("--all", help="Remove all unused resources")] = False,  # noqa: E501
    containers:    Annotated[bool, typer.Option("--containers")] = False,
    images:        Annotated[bool, typer.Option("--images")]     = False,
    volumes:       Annotated[bool, typer.Option("--volumes")]    = False,
    force:         Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Remove unused Docker containers, images, and volumes."""
    try:
        client = require_docker()
    except DockerNotAvailableError as exc:
        err_console.print(str(exc))
        raise typer.Exit(1) from exc

    resources = list_unused_resources(client)
    stopped   = resources["stopped_containers"]
    dangling  = resources["dangling_images"]

    if not stopped and not dangling:
        console.print("  Nothing to clean.")
        return

    console.print(f"  Stopped containers  ({len(stopped)})")
    console.print(f"  Dangling images     ({len(dangling)})")

    rm_containers = all_resources or containers
    rm_images     = all_resources or images
    rm_volumes    = all_resources or volumes

    if not (rm_containers or rm_images or rm_volumes):
        rm_containers = True
        rm_images     = True

    if not force:
        confirm = typer.confirm("  Proceed?", default=False)
        if not confirm:
            raise typer.Abort()

    removed = clean_resources(client, rm_containers, rm_images, rm_volumes)
    console.print(f"  Removed: {removed}")


# ── dockerwiz config ───────────────────────────────────────────────────────────

config_app = typer.Typer(help="Manage user preferences.", no_args_is_help=True)
app.add_typer(config_app, name="config")


@config_app.command("set")
def config_set_cmd(
    key:   Annotated[str, typer.Argument(help="Config key (e.g. default.language)")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a config value."""
    if key not in CONFIG_KEY_MAP:
        err_console.print(f"Unknown config key: {key}")
        err_console.print(f"Valid keys: {', '.join(CONFIG_KEY_MAP)}")
        raise typer.Exit(1)
    config = load_config()
    try:
        config = set_config_value(config, key, value)
    except ValueError as exc:
        err_console.print(str(exc))
        raise typer.Exit(1) from exc
    save_config(config)
    console.print(f"  Set {key} = {value}")


@config_app.command("get")
def config_get_cmd(
    key: Annotated[str, typer.Argument(help="Config key to read")],
) -> None:
    """Get a config value."""
    config = load_config()
    result = get_config_value(config, key)
    console.print(result if result is not None else "(not set)")


@config_app.command("list")
def config_list_cmd() -> None:
    """Show all config values."""
    config = load_config()

    def _show(section: str, obj: object) -> None:
        console.print(f"\n  \\[{section}]")
        for field in obj.model_fields:  # type: ignore[attr-defined]
            val = getattr(obj, field)
            console.print(f"  {field:<20} = {val if val is not None else '(not set)'}")

    _show("defaults",   config.defaults)
    _show("output",     config.output)
    _show("cache",      config.cache)
    _show("docker_hub", config.docker_hub)


@config_app.command("unset")
def config_unset_cmd(
    key: Annotated[str, typer.Argument(help="Config key to unset")],
) -> None:
    """Unset (clear) a config value."""
    config = load_config()
    config = unset_config_value(config, key)
    save_config(config)
    console.print(f"  Unset {key}")


# ── dockerwiz list ─────────────────────────────────────────────────────────────

@list_app.command("stacks")
def list_stacks_cmd() -> None:
    """Show all supported language/framework stacks."""
    table = Table(title="Supported Stacks")
    table.add_column("Language",  style="cyan")
    table.add_column("Framework", style="green")
    table.add_column("Default Port")
    table.add_column("Base Image Key")
    for s in STACKS:
        table.add_row(s.language, s.label, str(s.default_port), s.image_key)
    console.print(table)


@list_app.command("services")
def list_services_cmd() -> None:
    """Show all supported services."""
    table = Table(title="Supported Services")
    table.add_column("Name",  style="cyan")
    table.add_column("Label", style="green")
    table.add_column("Image")
    table.add_column("Port")
    table.add_column("Mutex Group")
    for s in SERVICES:
        table.add_row(s.name, s.label, s.image, str(s.default_port), s.mutex_group or "—")
    console.print(table)


# ── dockerwiz version ──────────────────────────────────────────────────────────

@app.command("version")
def version_cmd() -> None:
    """Show the installed version."""
    try:
        v = pkg_version("dockerwiz")
    except PackageNotFoundError:
        v = "dev"
    console.print(f"dockerwiz {v}")


# ── Entrypoint ─────────────────────────────────────────────────────────────────

def main() -> None:
    app()


if __name__ == "__main__":
    main()
