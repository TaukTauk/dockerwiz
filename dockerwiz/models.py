"""Core data models for dockerwiz."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ProjectConfig(BaseModel):
    """Fully validated configuration for a project. All fields required."""

    name: str
    output_directory: str = "."
    language: str
    framework: str
    base_image: str
    environment: str = "dev"
    app_port: int = Field(ge=1, le=65535)
    services: list[str] = Field(default_factory=list)
    db_user: str | None = None
    db_password: str | None = None
    db_name: str | None = None
    db_port: int | None = None
    host_db_port: int | None = None
    host_redis_port: int | None = None
    host_nginx_port: int | None = None
    host_mongo_port: int | None = None

    @model_validator(mode="after")
    def validate_db_fields(self) -> ProjectConfig:
        has_db = "postgres" in self.services or "mysql" in self.services
        if has_db:
            if not self.db_user:
                raise ValueError("db_user is required when a database service is selected")
            if not self.db_name:
                raise ValueError("db_name is required when a database service is selected")
        return self

    # ── Computed helpers ───────────────────────────────────────────────────────

    @property
    def has_postgres(self) -> bool:
        return "postgres" in self.services

    @property
    def has_mysql(self) -> bool:
        return "mysql" in self.services

    @property
    def has_redis(self) -> bool:
        return "redis" in self.services

    @property
    def has_nginx(self) -> bool:
        return "nginx" in self.services

    @property
    def has_mongo(self) -> bool:
        return "mongo" in self.services

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


class PartialProjectConfig(BaseModel):
    """In-progress wizard config. All fields optional; populated screen by screen."""

    name: str | None = None
    output_directory: str = "."
    language: str | None = None
    framework: str | None = None
    base_image: str | None = None
    environment: str = "dev"
    app_port: int | None = None
    services: list[str] = Field(default_factory=list)
    db_user: str | None = None
    db_password: str | None = None
    db_name: str | None = None
    db_port: int | None = None
    host_db_port: int | None = None
    host_redis_port: int | None = None
    host_nginx_port: int | None = None
    host_mongo_port: int | None = None

    def to_config(self) -> ProjectConfig:
        """Convert to final validated ProjectConfig. Raises ValidationError if incomplete."""
        return ProjectConfig(**self.model_dump())
