# dockerwiz — Product

> Generate production-ready Docker setups through an interactive terminal wizard.

---

## 1. Overview

dockerwiz is a Python CLI tool that reduces Docker setup friction for developers. Instead of hand-writing Dockerfiles, docker-compose configurations, and environment files from scratch, developers run a single command and walk through an interactive TUI wizard that produces a complete, production-aware Docker scaffold tailored to their stack.

### Core Philosophy

- Convention over configuration — smart defaults that just work
- Environment-aware — dev configs optimise for speed, prod configs optimise for security and size
- Self-maintaining — Docker Hub API integration keeps base image versions current
- Zero lock-in — output is plain Dockerfile and Compose YAML, no proprietary formats

### Installation

```bash
pipx install dockerwiz          # recommended
brew install TaukTauk/tap/dockerwiz   # macOS
winget install dockerwiz              # Windows
# Binary download from GitHub Releases
```

---

## 2. Name and Branding

| Decision | Value |
|---|---|
| Package name | `dockerwiz` |
| CLI command | `dockerwiz` |
| GitHub repo | `TaukTauk/dockerwiz` |
| PyPI URL | `pypi.org/project/dockerwiz` |
| Tagline | Generate production-ready Docker setups through an interactive terminal wizard. |
| Docs URL (v1.1) | `TaukTauk.github.io/dockerwiz` |
| License | MIT |

**Why `dockerwiz`:** two syllables, immediately implies Docker + wizard, easy to type, command name matches package name.

### Terminal Output Style

| Prefix | Color | Meaning |
|---|---|---|
| `[OK]` | green | Step succeeded |
| `[WARN]` | yellow | Non-fatal issue |
| `[ERROR]` | red | Fatal issue |
| `[INFO]` | default | Neutral information |

Rules: no trailing periods on single-line messages, no exclamation marks, no filler phrases (`Great!`, `Done!`).

Good: `Generated 6 files in ./my-api`
Bad: `Great! Your Docker setup has been generated successfully!`

**Docker trademark note:** dockerwiz is an independent open source project and is not affiliated with or endorsed by Docker Inc.

---

## 3. Minimum Python Version — 3.11

`requires-python = ">=3.11"` in `pyproject.toml`. CI matrix: 3.11, 3.12, 3.13.

**Why 3.11:**
- `tomllib` (stdlib TOML parser) — avoids the `tomli` backport and a conditional import
- `asyncio.TaskGroup` — concurrent Docker Hub API fetches without workarounds
- 10–60% faster than 3.10; still actively maintained until October 2027
- Python 3.9 is EOL; 3.10 reaches EOL October 2026

Binary users (GitHub Releases) are unaffected — the runtime is bundled by PyInstaller.

Next floor bump: when 3.11 reaches EOL (October 2027), bump to 3.12.

---

## 4. Command Surface

### v0.1.0

| Command | Description |
|---|---|
| `dockerwiz new` | TUI wizard — generate full Docker setup |
| `dockerwiz start [service]` | Start Docker Compose services |
| `dockerwiz health` | Diagnose running Docker project |
| `dockerwiz shell <service>` | Quick exec into any container |
| `dockerwiz clean` | Remove unused containers, images, volumes |
| `dockerwiz config` | Manage user preferences |
| `dockerwiz list stacks` | Show supported stacks |
| `dockerwiz list services` | Show supported services |
| `dockerwiz version` | Show installed version |

### v0.2.0 (planned)

| Command | Description |
|---|---|
| `dockerwiz logs <service>` | Smart log viewer with filtering |
| `dockerwiz monitor` | Live container resource dashboard |
| `dockerwiz update` | Check and apply base image updates |
| `dockerwiz convert <path>` | Generate Docker files from existing project |
| `dockerwiz publish` | Build and push image to a registry |
| `dockerwiz template list` | Show template sources |
| `dockerwiz template export` | Copy built-ins to user dir |
| `dockerwiz template validate` | Validate user templates |

---

## 5. `dockerwiz new` — TUI Wizard

The flagship command. 6-screen interactive wizard → complete Docker scaffold.

### Wizard Screens

| Screen | Title | Inputs |
|---|---|---|
| 1 | Project Setup | Project name, output directory, environment (dev / prod) |
| 2 | Language & Framework | Language, framework, base image version |
| 3 | Services | Checkboxes: PostgreSQL, MySQL, Redis, Nginx, MongoDB |
| 4 | Configuration | App port, DB credentials |
| 5 | Review Summary | Read-only view, file list, conflict warning |
| 6 | Generating | Progress bar, per-file status, next steps on success |

### Supported Stacks

| Language | Framework | Default Port | Dev Hot-Reload |
|---|---|---|---|
| Python | FastAPI | 8000 | `uvicorn --reload` |
| Python | Django | 8000 | `manage.py runserver` |
| Go | Gin | 8080 | Air |
| Go | Echo | 8080 | Air |
| Node.js | Express | 3000 | nodemon |
| Node.js | NestJS | 3000 | `nest start --watch` |

### Supported Services

| Service | Image | Port | Mutex Group | Healthcheck |
|---|---|---|---|---|
| PostgreSQL | `postgres:16-alpine` | 5432 | `db` | `pg_isready` |
| MySQL | `mysql:8.0` | 3306 | `db` | `mysqladmin ping` |
| Redis | `redis:7-alpine` | 6379 | — | `redis-cli ping` |
| Nginx | `nginx:alpine` | 80 | — | `wget` check |
| MongoDB | `mongo:7` | 27017 | — | `mongosh ping` |

PostgreSQL and MySQL share mutex group `db` — they cannot both be selected.

### Generated Files

| File | Contents |
|---|---|
| `Dockerfile` | Single-stage (dev) or multi-stage (prod), non-root user in prod |
| `docker-compose.yml` | App + all selected services with healthchecks, volumes, networks |
| `docker-compose.override.yml` | Dev-only: source volume mount + DEBUG env (omitted in prod) |
| `.dockerignore` | Language-tailored exclusions |
| `.env.example` | All env vars, safe placeholder values (`db_password` always `changeme`) |
| `Makefile` | `make up/down/logs/shell/build/restart/db` |
| `nginx.conf` | Reverse proxy — only when Nginx is selected |

### Dev vs Prod Differences

| Aspect | dev | prod |
|---|---|---|
| Dockerfile stages | Single stage | Multi-stage build |
| Hot-reload | Enabled | Disabled |
| Volume mounts | Source code mounted | No mounts |
| User | root | Non-root user created |
| Dev dependencies | Installed | Excluded |

### Docker Hub Version Fetching

Queries `hub.docker.com/v2/repositories/library/<image>/tags` at startup, filters to meaningful variants (e.g. `3.13-slim`), caches at `~/.dockerwiz/cache.json` (TTL 24h, configurable). Falls back to hardcoded versions if offline — shows notice in wizard.

---

## 6. `dockerwiz health`

Scans the current directory's `docker-compose.yml` and produces a diagnostic report:

- Compose file syntax validity
- All services running and healthy
- Resource usage (flags >80% memory)
- `.env` completeness
- Outdated base images vs Docker Hub latest
- Port conflicts

---

## 7. `dockerwiz shell <service>`

Convenience wrapper around `docker compose exec`. Auto-selects shell (`bash` → `sh`). For DB services, launches the appropriate client (`psql`, `mysql`, `redis-cli`, `mongosh`).

---

## 8. `dockerwiz clean`

Identifies stopped containers, dangling images, and unused volumes. Shows disk space to be freed, prompts for confirmation.

Flags: `--all`, `--containers`, `--images`, `--volumes`, `--force`.

---

## 9. `dockerwiz config`

Persists user preferences in `~/.dockerwiz/config.toml`. Keys:

| Key | Default | Example |
|---|---|---|
| `default.language` | — | `python` |
| `default.framework` | — | `fastapi` |
| `default.environment` | `dev` | `prod` |
| `default.db` | — | `postgres` |
| `cache.ttl_hours` | `24` | `48` |
| `output.directory` | `.` | `~/projects` |

Subcommands: `config set`, `config get`, `config list`, `config unset`.

---

## 10. v1.1 Commands (Overview)

**`dockerwiz logs <service>`** — Color-coded log viewer with `--filter`, `--follow`, `--tail`, `--since`. Multi-service support.

**`dockerwiz monitor`** — Real-time TUI dashboard: CPU, memory, network I/O, ports. Keyboard: arrows to select, `L` for logs, `S` for shell, `R` to restart, `Q` to exit.

**`dockerwiz update`** — Parses `docker-compose.yml`, queries Docker Hub for newer tags per image. `--apply` rewrites in place. `--dry-run` shows what would change.

**`dockerwiz convert <path>`** — Detects language/framework from project files (`requirements.txt` → Python, `go.mod` → Go, `package.json` → Node.js), generates Docker scaffold.

**`dockerwiz publish`** — Guided build-and-push to Docker Hub, GHCR, AWS ECR, or custom registry. Delegates credentials to Docker CLI credential helpers.
