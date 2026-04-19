# CLAUDE.md

This file provides context for AI-assisted development on dockerwiz.
Detailed documentation lives in the `scope/` directory.

---

## What is dockerwiz

A Python CLI tool that generates production-ready Docker setups through an
interactive TUI wizard. Developers run `dockerwiz new`, walk through 6 screens,
and get a complete Dockerfile, docker-compose.yml, .env.example, Makefile, and
more — tailored to their stack.

---

## Scope Documents

| File | Contents |
|---|---|
| `scope/PRODUCT.md` | Feature spec (v1.0 & v1.1), commands, stacks, services, naming, Python version |
| `scope/ARCHITECTURE.md` | Module responsibilities, dependency graph, data flow, config schema, error handling, template extensibility |
| `scope/DESIGN.md` | TUI wireframes for all 6 screens, Jinja2 template design for all output files |
| `scope/DEVELOPMENT.md` | pyproject.toml, testing strategy, versioning, CI/CD pipeline, licensing, documentation |

---

## Tech Stack

| Concern | Tool |
|---|---|
| Language | Python 3.11+ |
| TUI framework | Textual |
| CLI framework | Typer |
| Templating | Jinja2 |
| HTTP client | httpx (async) |
| Docker SDK | docker |
| Data validation | Pydantic v2 |
| Terminal output | Rich |
| Config files | tomllib (read) + tomli-w (write) |
| Project manager | Hatch |
| Linter | Ruff |
| Type checker | Mypy (strict) |
| Test runner | Pytest |

---

## Project Structure

```
dockerwiz/
├── dockerwiz/
│   ├── __init__.py
│   ├── cli.py               # Typer entrypoint — all commands registered here
│   ├── models.py            # ProjectConfig, PartialProjectConfig, enums
│   ├── generator.py         # Renders Jinja2 templates, writes files
│   ├── docker_hub.py        # Docker Hub API client, version cache
│   ├── docker_client.py     # Docker SDK wrapper
│   ├── fallbacks.py         # Hardcoded image version fallbacks
│   ├── config.py            # ~/.dockerwiz/config.toml read/write
│   ├── stacks.py            # Supported language/framework definitions
│   ├── services.py          # Supported service definitions
│   ├── tui/
│   │   ├── app.py           # Textual App, screen transitions, partial state
│   │   └── screens/
│   │       ├── project.py   # Screen 1 — Project Setup
│   │       ├── language.py  # Screen 2 — Language and Framework
│   │       ├── services.py  # Screen 3 — Services
│   │       ├── configure.py # Screen 4 — Configuration
│   │       ├── review.py    # Screen 5 — Review Summary
│   │       └── generate.py  # Screen 6 — Generating
│   └── templates/
│       ├── python/fastapi/
│       ├── python/django/
│       ├── go/gin/
│       ├── go/echo/
│       ├── node/express/
│       └── node/nestjs/
├── tests/
│   ├── snapshots/           # Golden files for generator snapshot tests
│   ├── integration/         # Tests that require a live Docker daemon
│   ├── test_generator.py
│   ├── test_docker_hub.py
│   └── test_cli.py
├── scope/                   # All planning and design documents
├── docs/                    # MkDocs source (v1.1)
├── pyproject.toml
├── CLAUDE.md
└── CHANGELOG.md
```

---

## Module Dependency Rules

These rules must not be violated. They prevent circular imports and keep
modules independently testable.

- `models.py`, `fallbacks.py`, `stacks.py`, `services.py` — import nothing from other dockerwiz modules
- `generator.py` — never imports from `tui/` or `cli.py`
- `docker_hub.py`, `docker_client.py` — never import from `tui/` or `generator.py`
- `tui/` — never imports from `cli.py`
- `cli.py` — the only module that imports from everything else

---

## Key Conventions

### Code Style

- Line length: 100 characters
- Type hints: required on all public functions (mypy strict)
- Docstrings: Google style on all public functions and classes
- No `os.path` — use `pathlib.Path` throughout
- No `print()` — use `rich.console.Console` for all terminal output

### Error Handling

- Never show a raw Python traceback to the user
- Every error must include a plain-language message and a suggested action
- Unexpected exceptions are caught at the CLI boundary and written to `~/.dockerwiz/logs/debug.log`
- `docker_hub.py` never raises — returns `(fallback_tags, is_live=False)` on failure

### Naming

- CLI command functions in `cli.py`: suffix with `_cmd` to avoid shadowing (e.g. `version_cmd`, `config_cmd`)
- Template context helpers: `has_<service>` for booleans (e.g. `has_postgres`), `is_<env>` for environment (e.g. `is_prod`)
- Config keys use dot notation in CLI: `default.language`, `cache.ttl_hours`

### Templates

- All template files use `.j2` extension
- Templates receive the full context from `build_context()` in `generator.py`
- Keep logic minimal in templates — complex conditionals belong in `build_context()`
- Makefile templates must use real tab characters on recipe lines, not spaces
- `$$` in Makefile templates renders as `$` in the output

### Tests

- Snapshot tests for all generator output — update with `pytest --snapshot-update`
- Mock all Docker Hub API calls with `respx` — never make real network calls in tests
- Use `typer.testing.CliRunner` for CLI tests
- Integration tests (require Docker daemon) live in `tests/integration/` and run separately

### Commits

Follow Conventional Commits:
```
feat(new): add PHP Laravel stack support
fix(health): handle missing .env file gracefully
docs(readme): update installation instructions
```

Valid scopes: `new`, `health`, `shell`, `clean`, `config`, `logs`, `monitor`,
`update`, `convert`, `publish`, `generator`, `docker-hub`, `tui`, `cli`, `deps`, `release`

---

## Common Commands

```bash
# Run the CLI in development
pip install -e .
dockerwiz --help

# Run tests
hatch run test

# Run tests with coverage
hatch run test-cov

# Lint
hatch run lint

# Auto-fix lint
hatch run lint-fix

# Type check
hatch run types

# Run all checks (mirrors CI)
hatch run check

# Update snapshots after intentional template changes
pytest --snapshot-update

# Build docs locally (v1.1)
mkdocs serve
```

---

## v0.1.0 Command Surface

| Command | Status |
|---|---|
| `dockerwiz new` | Core — TUI wizard |
| `dockerwiz start [service]` | Start Docker Compose services |
| `dockerwiz health` | Diagnose running project |
| `dockerwiz shell <service>` | Exec into container |
| `dockerwiz clean` | Remove unused resources |
| `dockerwiz config` | Manage preferences |
| `dockerwiz list stacks` | Show supported stacks |
| `dockerwiz list services` | Show supported services |
| `dockerwiz version` | Show installed version |

## v0.2.0 Command Surface (planned)

| Command | Status |
|---|---|
| `dockerwiz logs <service>` | Smart log viewer |
| `dockerwiz monitor` | Live container dashboard |
| `dockerwiz update` | Check and apply image updates |
| `dockerwiz convert <path>` | Import existing project |
| `dockerwiz publish` | Build and push to registry |
| `dockerwiz template list` | Show template sources |
| `dockerwiz template export` | Copy built-ins to user dir |
| `dockerwiz template validate` | Validate user templates |

---

## Supported Stacks (v1.0)

| Language | Framework | Default Port | Dev Hot-Reload |
|---|---|---|---|
| Python | FastAPI | 8000 | `uvicorn --reload` |
| Python | Django | 8000 | `manage.py runserver` |
| Go | Gin | 8080 | Air |
| Go | Echo | 8080 | Air |
| Node.js | Express | 3000 | nodemon |
| Node.js | NestJS | 3000 | `nest start --watch` |

## Supported Services (v1.0)

| Service | Image | Port | Mutex Group |
|---|---|---|---|
| PostgreSQL | `postgres:16-alpine` | 5432 | `db` |
| MySQL | `mysql:8.0` | 3306 | `db` |
| Redis | `redis:7-alpine` | 6379 | — |
| Nginx | `nginx:alpine` | 80 | — |
| MongoDB | `mongo:7` | 27017 | — |

Services in the same mutex group cannot both be selected.

---

## User-Facing Files

```
~/.dockerwiz/
├── config.toml      # user preferences (TOML)
├── cache.json       # Docker Hub version cache (JSON, TTL 24h default)
├── templates/       # user template overrides (optional)
└── logs/
    └── debug.log    # full tracebacks on unexpected errors
```

---

## Distribution (v1.0)

- Primary: `pipx install dockerwiz`
- Binaries: GitHub Releases (`linux-x64`, `darwin-arm64`, `windows-x64.exe`)
- Minimum Python: 3.11 (binary users are unaffected — runtime is bundled)
