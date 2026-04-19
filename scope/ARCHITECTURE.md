# dockerwiz — Architecture

---

## 1. Module Dependency Graph

Arrows mean "imports from". This graph must remain acyclic.

```
cli.py
  ├── models.py
  ├── config.py
  ├── docker_hub.py
  ├── docker_client.py
  ├── generator.py
  ├── stacks.py
  ├── services.py
  └── tui/app.py
        ├── models.py
        ├── stacks.py
        ├── services.py
        └── tui/screens/*.py
              └── models.py

generator.py
  ├── models.py
  ├── stacks.py
  └── services.py

docker_hub.py
  ├── fallbacks.py
  └── config.py

docker_client.py
  └── (docker SDK only)

models.py      → (pydantic only)
fallbacks.py   → (no imports)
stacks.py      → (dataclasses only)
services.py    → (dataclasses only)
config.py      → (tomllib, tomli-w, pathlib only)
```

### Enforced Rules

- `models.py`, `fallbacks.py`, `stacks.py`, `services.py` never import from other dockerwiz modules
- `generator.py` never imports from `tui/` or `cli.py`
- `docker_hub.py`, `docker_client.py` never import from `tui/` or `generator.py`
- `tui/` never imports from `cli.py`
- `cli.py` is the only module that imports from everything else

Violations create circular imports or tightly coupled modules that are hard to test independently.

---

## 2. End-to-End Data Flow (`dockerwiz new`)

```
User runs: dockerwiz new
        │
        ▼
cli.py — loads config, fetches Docker Hub versions (asyncio.run)
        │
        ▼
tui/app.py — launches Textual application with partial state
        │
  ┌─────┴──────────────────────────┐
  │  Screens 1-5: user fills       │
  │  PartialProjectConfig fields   │
  └─────┬──────────────────────────┘
        │
        ▼
Screen 5 calls partial.to_config() → validated ProjectConfig
        │
        ▼
Screen 6 — Textual worker calls generator.generate(config)
        │
        ▼
generator.py renders Jinja2 templates → writes files atomically
        │
        ▼
Screen 6 — progress bar completes, next steps shown
```

---

## 3. Module Responsibilities

### `cli.py`
- Owns the Typer app instance and registers all commands
- Each command validates preconditions then delegates to the appropriate module
- The only place `asyncio.run()` is called (for Docker Hub fetching)
- Never contains business logic

### `models.py`
- Defines `ProjectConfig` (validated final state) and `PartialProjectConfig` (wizard in-progress state)
- Contains no I/O, no rendering, no API calls
- `ProjectConfig` model_validator requires `db_user`/`db_name` when a DB service is selected
- Computed properties: `has_postgres`, `has_mysql`, `has_redis`, `has_nginx`, `has_mongo`, `is_dev`, `is_prod`

### `generator.py`
- Accepts a `ProjectConfig`, returns `dict[str, str]` (filename → content)
- Builds Jinja2 env via `ChoiceLoader` (user templates first, built-ins second)
- Builds template context with all `has_*` and `is_*` helpers
- Writes files atomically: renders to temp dir, copies to final destination
- Public API: `generate(config) -> list[str]`

### `docker_hub.py`
- Owns Docker Hub API client and `~/.dockerwiz/cache.json`
- Never raises — returns `(tags, is_live=False)` on any failure
- `fetch_image_versions(image)` → `tuple[list[str], bool]`
- `fetch_all_versions(images, ttl_hours)` — uses cache where fresh, fetches concurrently where stale

### `docker_client.py`
- Wraps the Docker SDK for `health`, `shell`, `clean`, `monitor`, `logs`, `publish`
- Exposes: `require_docker()`, `exec_shell()`, `run_health_check()`, `list_unused_resources()`, `clean_resources()`
- Raises `DockerNotAvailableError`, `ContainerNotRunningError`

### `fallbacks.py`
- Plain data file, no logic, no imports
- `FALLBACK_VERSIONS: dict[str, list[str]]` — hardcoded image version lists

### `stacks.py` / `services.py`
- Data definitions only (frozen dataclasses)
- `STACKS` list of 6 `StackDefinition` entries; helpers: `get_stack()`, `frameworks_for_language()`
- `SERVICES` list of 5 `ServiceDefinition` entries; `mutex_group` field drives mutual exclusion; helpers: `get_service()`, `get_mutex_conflicts()`

### `config.py`
- Reads/writes `~/.dockerwiz/config.toml` via `tomllib` (read) and `tomli-w` (write)
- Pydantic models: `UserConfig` → `DefaultsConfig`, `OutputConfig`, `CacheConfig`, `DockerHubConfig`
- `CONFIG_KEY_MAP` maps dot-notation CLI keys to `(section_attr, field_attr)`
- Falls back to defaults if config file is missing or corrupt

### `tui/app.py`
- Textual `App` subclass; receives `user_config`, `available_versions`, `is_live` from `cli.py`
- Holds `self.partial = PartialProjectConfig(...)` pre-filled from user config defaults
- Manages screen transitions

### `tui/screens/*.py`
- Each screen is a `Screen` subclass for one wizard step
- Reads/writes `self.app.partial` as the user fills in values
- Does not call `generator.py` directly — Screen 5 triggers Screen 6, which calls the generator

---

## 4. State Management in the TUI

`PartialProjectConfig` has all fields optional. Screens write to it incrementally. Screen 5 calls `partial.to_config()` to produce the final validated `ProjectConfig`. If any required field is missing, `ValidationError` is raised and the user is sent back.

```python
class PartialProjectConfig(BaseModel):
    name:        str | None = None
    language:    str | None = None
    framework:   str | None = None
    services:    list[str]  = []
    environment: str        = "dev"
    app_port:    int | None = None
    base_image:  str | None = None
    db_user:     str | None = None
    db_password: str | None = None
    db_name:     str | None = None
    db_port:     int | None = None

    def to_config(self) -> ProjectConfig:
        return ProjectConfig(**self.model_dump())
```

---

## 5. Async Boundary

`docker_hub.py` uses `httpx` async. Everything else is synchronous. The async boundary is contained and explicit — only `cli.py` calls `asyncio.run()`. Do not call `asyncio.run()` inside TUI screens; use `self.run_worker()` for async operations within Textual.

---

## 6. File Writing Flow

```
generator.py receives ProjectConfig
    │
    ├── build_jinja_env(language, framework)
    │     └── ChoiceLoader: user templates first (~/.dockerwiz/templates/), built-ins second
    │
    ├── build_context(config)
    │     └── returns dict with all template vars + has_* and is_* helpers
    │
    ├── render_templates(env, context)
    │     └── returns dict[str, str]: {filename: rendered_content}
    │
    └── write_files(output_dir, rendered_files)
          ├── check_write_permission(output_dir)
          ├── render all files to tempfile.TemporaryDirectory
          ├── shutil.copytree to final destination
          └── returns list[str] of files written
```

Atomic writes prevent partial file state — if any write fails, the temp dir is cleaned up automatically and the output directory is never left in a partial state.

---

## 7. Error Propagation

```
docker_hub.py     → never raises — returns (fallback, is_live=False) on failure
generator.py      → raises GeneratorError on template or write failure
docker_client.py  → raises DockerNotAvailableError, ContainerNotRunningError
models.py         → raises pydantic.ValidationError on invalid config

cli.py catches at the top level:
  DockerNotAvailableError  → plain message + SystemExit(1)
  GeneratorError           → plain message + SystemExit(1)
  Unexpected Exception     → plain message + write full traceback to ~/.dockerwiz/logs/debug.log
```

Never show a raw Python traceback to the user.

---

## 8. Config Files

### `~/.dockerwiz/config.toml` (user preferences)

```toml
[defaults]
language    = "python"
framework   = "fastapi"
environment = "dev"
db          = "postgres"

[output]
directory = "."

[cache]
ttl_hours = 24        # 1–720, default 24

[docker_hub]
timeout_seconds = 5   # 1–30, default 5
```

Pydantic models: `UserConfig` → `DefaultsConfig`, `OutputConfig`, `CacheConfig`, `DockerHubConfig`. Validation constraints enforced on `config set`; invalid manually-edited values fall back to defaults silently.

Note: `save_config` uses `exclude_none=True` because `tomli_w` cannot serialize `None`.

### `~/.dockerwiz/cache.json` (Docker Hub version cache)

```json
{
  "python": { "tags": ["3.13-slim", "3.12-slim", "3.11-slim"], "fetched_at": "2026-04-18T10:00:00" },
  "golang": { "tags": ["1.23-alpine", "1.22-alpine"], "fetched_at": "2026-04-18T10:00:00" },
  "node":   { "tags": ["22-alpine", "20-alpine"], "fetched_at": "2026-04-18T10:00:00" }
}
```

Pydantic models: `VersionCache` → `ImageCache(tags, fetched_at)`. Fresh check: `age < ttl_hours * 3600`.

### Config Key Map

| CLI key | Section | Field |
|---|---|---|
| `default.language` | `defaults` | `language` |
| `default.framework` | `defaults` | `framework` |
| `default.environment` | `defaults` | `environment` |
| `default.db` | `defaults` | `db` |
| `output.directory` | `output` | `directory` |
| `cache.ttl_hours` | `cache` | `ttl_hours` |
| `docker_hub.timeout_seconds` | `docker_hub` | `timeout_seconds` |

---

## 9. Error Handling Patterns

### Docker not available

```python
def require_docker() -> docker.DockerClient:
    try:
        client = docker.from_env()
        client.ping()
        return client
    except FileNotFoundError:
        raise DockerNotAvailableError("Docker is not installed or not on PATH.")
    except DockerException:
        raise DockerNotAvailableError("Docker daemon is not running.")
```

### Output directory conflict

- Empty directory → proceed silently
- Non-empty directory → prompt: Merge / Overwrite / Cancel (handled on Screen 5)
- Partial conflict (merge) → report per-file: `skipped (already exists)` vs `created`

### Docker Hub failure

All errors caught in `fetch_image_versions`; returns `(FALLBACK_VERSIONS[image], False)`. The `is_live=False` flag causes the wizard to show: *"Showing cached defaults — could not reach Docker Hub"*.

### Input validation (TUI)

- Project name: non-empty, `[a-zA-Z0-9_-]+` only, not in `RESERVED_NAMES`
- App port: 1–65535
- DB user/name: non-empty when DB service selected; password may be empty (warn only)
- Mutex conflict: Next button disabled until resolved

### Error message format

```
[Error]   Short description of what went wrong.
          Context if not obvious.
          Suggested action.
```

Debug tracebacks written to `~/.dockerwiz/logs/debug.log`. Never expose raw exceptions to the terminal.

---

## 10. Template Extensibility

### Resolution Order

```
1. User templates    ~/.dockerwiz/templates/<language>/<framework>/
2. Built-in templates  <package>/templates/<language>/<framework>/
```

`ChoiceLoader` tries user templates first; falls back to built-ins per file. Partial overrides are supported — replace only `Dockerfile.j2` while keeping the rest.

### User Overrides

Copy one file or an entire stack directory to `~/.dockerwiz/templates/<lang>/<fw>/`. dockerwiz picks it up automatically.

### Custom Stacks (v1.1)

Create templates under `~/.dockerwiz/templates/ruby/rails/`, then register in `config.toml`:

```toml
[[custom_stacks]]
language  = "ruby"
framework = "rails"
label     = "Ruby on Rails"
app_port  = 3000
```

The wizard displays it alongside built-in stacks.

### Template Commands (v1.1)

| Command | Description |
|---|---|
| `dockerwiz template list` | Show all stacks and their template source |
| `dockerwiz template export <lang> <fw>` | Copy built-in templates to user directory |
| `dockerwiz template validate <lang> <fw>` | Render templates with sample data, check for errors |

### Security

User templates are Jinja2 executed at runtime — not sandboxed. Only use templates you trust. Never auto-fetch templates from remote URLs.
