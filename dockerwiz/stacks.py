"""Supported language/framework stack definitions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StackDefinition:
    """Describes a supported language/framework combination."""

    language: str
    framework: str
    label: str
    default_port: int
    image_key: str  # key used in FALLBACK_VERSIONS / cache (python, golang, node)


STACKS: list[StackDefinition] = [
    StackDefinition("python", "fastapi", "FastAPI",  8000, "python"),
    StackDefinition("python", "django",  "Django",   8000, "python"),
    StackDefinition("go",     "gin",     "Gin",      8080, "golang"),
    StackDefinition("go",     "echo",    "Echo",     8080, "golang"),
    StackDefinition("node",   "express", "Express",  3000, "node"),
    StackDefinition("node",   "nestjs",  "NestJS",   3000, "node"),
]

LANGUAGES: list[str] = sorted({s.language for s in STACKS})


def get_stack(language: str, framework: str) -> StackDefinition | None:
    """Return the matching stack definition, or None if not found."""
    for stack in STACKS:
        if stack.language == language and stack.framework == framework:
            return stack
    return None


def frameworks_for_language(language: str) -> list[StackDefinition]:
    """Return all stacks for the given language."""
    return [s for s in STACKS if s.language == language]
