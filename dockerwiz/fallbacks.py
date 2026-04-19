"""Hardcoded fallback image version lists used when Docker Hub is unreachable."""

FALLBACK_VERSIONS: dict[str, list[str]] = {
    "python": ["3.13-slim", "3.12-slim", "3.11-slim"],
    "golang": ["1.23-alpine", "1.22-alpine", "1.21-alpine"],
    "node":   ["22-alpine", "20-alpine", "18-alpine"],
}
