"""Supported service definitions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceDefinition:
    """Describes a supported Docker service."""

    name: str
    label: str
    image: str
    default_port: int
    mutex_group: str | None  # services sharing the same group cannot both be selected
    category: str            # for UI grouping


SERVICES: list[ServiceDefinition] = [
    ServiceDefinition("postgres", "PostgreSQL", "postgres:16-alpine", 5432,  "db",  "Database"),
    ServiceDefinition("mysql",    "MySQL",      "mysql:8.0",          3306,  "db",  "Database"),
    ServiceDefinition("redis",    "Redis",      "redis:7-alpine",     6379,  None,  "Cache"),
    ServiceDefinition("nginx",    "Nginx",      "nginx:alpine",       80,    None,  "Web Server"),
    ServiceDefinition("mongo",    "MongoDB",    "mongo:7",            27017, None,  "Document Store"),  # noqa: E501
]


def get_service(name: str) -> ServiceDefinition | None:
    """Return the matching service definition, or None if not found."""
    for svc in SERVICES:
        if svc.name == name:
            return svc
    return None


def get_mutex_conflicts(selected: list[str]) -> list[tuple[str, str]]:
    """Return pairs of selected services that conflict via mutex_group."""
    conflicts: list[tuple[str, str]] = []
    groups: dict[str, list[str]] = {}
    for name in selected:
        svc = get_service(name)
        if svc and svc.mutex_group:
            groups.setdefault(svc.mutex_group, []).append(name)
    for members in groups.values():
        if len(members) > 1:
            conflicts.append((members[0], members[1]))
    return conflicts
