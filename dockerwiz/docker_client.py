"""Docker SDK wrapper for health, shell, clean, and other operational commands."""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    import docker as docker_sdk


class DockerNotAvailableError(Exception):
    """Raised when Docker is not installed or the daemon is not running."""


class ContainerNotRunningError(Exception):
    """Raised when a requested container is not running."""


def _get_client() -> docker_sdk.DockerClient:
    try:
        import docker  # noqa: PLC0415
        return docker.from_env()
    except ImportError as exc:
        raise DockerNotAvailableError("docker package is not installed.") from exc
    except Exception as exc:  # noqa: BLE001
        raise DockerNotAvailableError(
            "Could not connect to Docker daemon. Is Docker running?"
        ) from exc


def require_docker() -> docker_sdk.DockerClient:
    """Return a Docker client or raise DockerNotAvailableError."""
    return _get_client()


def check_port_available(port: int) -> bool:
    """Return True if the given host port is not currently in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) != 0


def get_containers(client: docker_sdk.DockerClient, all_containers: bool = False) -> list[Any]:
    """Return a list of containers (running by default, all if all_containers=True)."""
    return client.containers.list(all=all_containers)


def exec_shell(service: str, compose_file: Path | None = None) -> None:
    """Exec into a running container. Tries bash, falls back to sh.

    For database services, launches the appropriate database client instead.
    """
    env_file = Path(".env")
    env_vars: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()

    db_clients: dict[str, list[str]] = {
        "postgres": [
            "docker", "compose", "exec", service,
            "psql", "-U", env_vars.get("DB_USER", "postgres"),
            "-d", env_vars.get("DB_NAME", "postgres"),
        ],
        "mysql": [
            "docker", "compose", "exec", service,
            "mysql", "-u", env_vars.get("DB_USER", "root"), f"-p{env_vars.get('DB_PASSWORD', '')}",
            env_vars.get("DB_NAME", "mysql"),
        ],
        "redis": ["docker", "compose", "exec", service, "redis-cli"],
        "mongo": [
            "docker", "compose", "exec", service,
            "mongosh", "-u", env_vars.get("MONGO_USER", ""),
            "-p", env_vars.get("MONGO_PASSWORD", ""),
        ],
    }

    if service in db_clients:
        cmd = db_clients[service]
    else:
        # Try bash, fall back to sh
        cmd = ["docker", "compose", "exec", service, "bash"]

    proc = subprocess.run(cmd, check=False)  # noqa: S603
    if proc.returncode != 0 and service not in db_clients:
        fallback = ["docker", "compose", "exec", service, "sh"]
        subprocess.run(fallback, check=False)  # noqa: S603


def run_health_check(compose_file: Path | None = None) -> list[dict[str, str]]:
    """Run docker compose config to validate syntax, then check container states.

    Returns a list of result dicts with keys: service, status, message.
    """
    results: list[dict[str, str]] = []

    # Validate compose syntax
    config_cmd = ["docker", "compose", "config", "--quiet"]
    proc = subprocess.run(config_cmd, capture_output=True, text=True, check=False)  # noqa: S603
    if proc.returncode != 0:
        results.append({
            "service": "docker-compose.yml",
            "status":  "FAIL",
            "message": f"Invalid syntax: {proc.stderr.strip()}",
        })
        return results
    results.append({"service": "docker-compose.yml", "status": "OK", "message": "valid syntax"})

    # Check running containers
    try:
        client = _get_client()
        for container in client.containers.list():
            health   = container.attrs.get("State", {}).get("Health", {})
            h_status = str(health.get("Status", "none"))
            c_status = str(container.status or "unknown")
            name     = str(container.name or "")

            if c_status != "running":
                results.append({"service": name, "status": "FAIL", "message": c_status})
            elif h_status == "unhealthy":
                results.append({"service": name, "status": "FAIL", "message": "unhealthy"})
            else:
                results.append({"service": name, "status": "OK",
                                 "message": f"running ({h_status})"})
    except DockerNotAvailableError as exc:
        results.append({"service": "Docker daemon", "status": "FAIL", "message": str(exc)})

    return results


class _UnusedResources(TypedDict):
    stopped_containers: list[Any]
    dangling_images: list[Any]


def list_unused_resources(client: docker_sdk.DockerClient) -> _UnusedResources:
    """Return stopped containers and dangling images."""
    stopped_containers = [c for c in client.containers.list(all=True) if c.status == "exited"]
    dangling_images    = client.images.list(filters={"dangling": True})

    return {
        "stopped_containers": stopped_containers,
        "dangling_images":    dangling_images,
    }


def clean_resources(
    client: docker_sdk.DockerClient,
    remove_containers: bool = True,
    remove_images: bool = True,
    remove_volumes: bool = False,
) -> dict[str, int]:
    """Remove unused Docker resources. Returns counts of removed items."""
    removed: dict[str, int] = {}

    if remove_containers:
        stopped = [c for c in client.containers.list(all=True) if c.status == "exited"]
        for c in stopped:
            c.remove()
        removed["containers"] = len(stopped)

    if remove_images:
        dangling = client.images.list(filters={"dangling": True})
        for img in dangling:
            try:
                client.images.remove(img.id, force=False)
            except Exception:  # noqa: BLE001, S110
                pass
        removed["images"] = len(dangling)

    if remove_volumes:
        pruned = client.volumes.prune()
        removed["volumes"] = len(pruned.get("VolumesDeleted") or [])

    return removed


def start_containers(service: str | None = None) -> None:
    """Start Docker Compose services for the current project.

    Args:
        service: Optional service name to start. Starts all services if None.

    Raises:
        DockerNotAvailableError: If Docker is not installed or daemon is not running.
        FileNotFoundError: If no docker-compose.yml exists in the current directory.
    """
    _get_client()  # validate Docker is available before doing anything

    if not Path("docker-compose.yml").exists():
        raise FileNotFoundError(
            "No docker-compose.yml found in the current directory.\n"
            "Run 'dockerwiz new' to generate one."
        )

    cmd = ["docker", "compose", "up", "-d"]
    if service:
        cmd.append(service)

    subprocess.run(cmd, check=False)  # noqa: S603
