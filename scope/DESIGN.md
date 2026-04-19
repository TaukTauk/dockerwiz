# dockerwiz — TUI and Template Design

---

## Part 1: TUI Screen Wireframes

Six screens make up the wizard. Each is a Textual `Screen` subclass. Dimensions assume an 80-column terminal. All screens share a common header and footer.

### Common Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ dockerwiz                                          Step N of 6               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   [screen content]                                                           │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tab: next field   Shift+Tab: prev field   Ctrl+C: cancel                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

Header: tool name left, step indicator right. Footer: keyboard shortcuts, always visible.

---

### Screen 1 — Project Setup

**File:** `tui/screens/project.py` | **Writes:** `partial.name`, `partial.output_directory`, `partial.environment`

```
│   Project Setup                                                              │
│   ─────────────────────────────────────────────                              │
│                                                                              │
│   Project name                                                               │
│   ┌──────────────────────────────────────────┐                               │
│   │ my-api                                   │                               │
│   └──────────────────────────────────────────┘                               │
│                                                                              │
│   Output directory                                                           │
│   ┌──────────────────────────────────────────┐                               │
│   │ .                                        │                               │
│   └──────────────────────────────────────────┘                               │
│   Files will be written to: ./my-api                                         │
│                                                                              │
│   Environment                                                                │
│   (o) dev      ( ) prod                                                      │
│                                                                              │
│                                                       [ Next > ]             │
```

**Widgets:** Project name `Input` (required, validated on Next), Output directory `Input` (default `.`), Resolved path `Label` (updates live), Environment `RadioSet` (pre-filled from config), Next `Button` (disabled until name non-empty).

**Validation:** empty name → inline error; invalid characters → inline error; non-existent output dir → offer to create; non-empty resolved path → handled on Screen 5.

---

### Screen 2 — Language and Framework

**File:** `tui/screens/language.py` | **Writes:** `partial.language`, `partial.framework`, `partial.base_image`

```
│   Language and Framework                                                     │
│   ─────────────────────────────────────────────                              │
│                                                                              │
│   Language                  Framework                                        │
│   ┌───────────────────┐     ┌───────────────────┐                            │
│   │ (o) Python        │     │ (o) FastAPI       │                            │
│   │ ( ) Go            │     │ ( ) Django        │                            │
│   │ ( ) Node.js       │     └───────────────────┘                            │
│   └───────────────────┘                                                      │
│                                                                              │
│   Base image                                                                 │
│   ┌──────────────────────────────────────────┐                               │
│   │ python:3.13-slim (latest)             [v]│                               │
│   └──────────────────────────────────────────┘                               │
│   Fetched from Docker Hub                                                    │
│                                                                              │
│   [ < Back ]                                          [ Next > ]             │
```

**Widgets:** Language `RadioSet` (selecting language refreshes framework list), Framework `RadioSet` (options change per language), Base image `Select` (from `available_versions`), Source `Label` (changes based on `is_live`).

**Framework options by language:**

| Language | Frameworks |
|---|---|
| Python | FastAPI, Django |
| Go | Gin, Echo |
| Node.js | Express, NestJS |

**Offline notice:** when `is_live=False` → `"Showing cached defaults — could not reach Docker Hub"`.

---

### Screen 3 — Services

**File:** `tui/screens/services.py` | **Writes:** `partial.services`

```
│   Services                                                                   │
│   Select the services your project needs.                                    │
│                                                                              │
│   Database                                                                   │
│   [x] PostgreSQL      postgres:16-alpine     port 5432                       │
│   [ ] MySQL           mysql:8.0              port 3306                       │
│                                                                              │
│   Cache                                                                      │
│   [x] Redis           redis:7-alpine         port 6379                       │
│                                                                              │
│   Web Server                                                                 │
│   [ ] Nginx           nginx:alpine           port 80                         │
│                                                                              │
│   Document Store                                                             │
│   [ ] MongoDB         mongo:7                port 27017                      │
│                                                                              │
│   [ < Back ]                                          [ Next > ]             │
```

**Mutex conflict (PostgreSQL + MySQL selected):**

```
│   [x] PostgreSQL      postgres:16-alpine     port 5432                      │
│   [x] MySQL           mysql:8.0              port 3306                      │
│   ! Select either PostgreSQL or MySQL, not both.                            │
```

Next button disabled until conflict resolved. Zero services is valid.

---

### Screen 4 — Configuration

**File:** `tui/screens/configure.py` | **Writes:** `partial.app_port`, `partial.db_user`, `partial.db_password`, `partial.db_name`, `partial.db_port`

Fields shown depend on services selected on Screen 3.

**Variant A — no database:**

```
│   Application                                                                │
│   App port                                                                   │
│   ┌──────────────┐                                                           │
│   │ 8000         │                                                           │
│   └──────────────┘                                                           │
```

**Variant B — PostgreSQL or MySQL:**

```
│   Application                    App port                                   │
│   ┌──────────────────┐                                                      │
│   │ 8000             │                                                      │
│   └──────────────────┘                                                      │
│                                                                             │
│   PostgreSQL                                                                │
│   DB user              DB password             DB name                      │
│   ┌──────────────┐     ┌──────────────┐        ┌──────────────┐             │
│   │ myuser       │     │ ••••••       │  [show]│ mydb         │             │
│   └──────────────┘     └──────────────┘        └──────────────┘             │
```

**Default ports by language:** Python → 8000, Go → 8080, Node.js → 3000 (pre-filled from `stacks.py`).

**Validation:** port 1–65535; DB user/name non-empty if DB selected; password may be empty (warn only).

---

### Screen 5 — Review Summary

**File:** `tui/screens/review.py` | **Reads:** `partial` (full, read-only)

```
│   Review                                                                     │
│   ─────────────────────────────────────────────                              │
│                                                                              │
│   Project        my-api                                                      │
│   Output         ./my-api                                                    │
│   Environment    dev                                                         │
│   Language       Python / FastAPI                                            │
│   Base image     python:3.13-slim                                            │
│   Services       PostgreSQL, Redis                                           │
│   App port       8000                                                        │
│   DB user        myuser                                                      │
│   DB name        mydb                                                        │
│                                                                              │
│   Files to be generated                                                      │
│   ─────────────────────                                                      │
│   Dockerfile                                                                 │
│   docker-compose.yml                                                         │
│   docker-compose.override.yml                                                │
│   .dockerignore                                                              │
│   .env.example                                                               │
│   Makefile                                                                   │
│                                                                              │
│   [ < Back ]                                        [ Generate ]             │
```

**Output directory conflict warning (if non-empty):**

```
│   ! ./my-api already exists and is not empty.                               │
│     [ Merge ]   [ Overwrite ]   [ Cancel ]                                  │
```

Generate button hidden until conflict resolved. Clicking Generate calls `partial.to_config()`.

---

### Screen 6 — Generating

**File:** `tui/screens/generate.py` | **Reads:** validated `ProjectConfig`

```
│   Writing files to ./my-api                                                  │
│                                                                              │
│   Dockerfile                          done                                   │
│   docker-compose.yml                  done                                   │
│   .dockerignore                       done                                   │
│   .env.example                        done                                   │
│   Makefile                            writing...                             │
│                                                                              │
│   ████████████████████████░░░░░░░░░░░░  4 / 5                                │
```

**On success:** progress fills to 100%, then shows next steps:

```
│   Generated 6 files in ./my-api                                             │
│                                                                             │
│   Next steps:                                                               │
│     cd my-api                                                               │
│     cp .env.example .env                                                    │
│     make up                                                                 │
│                                                       [ Exit ]              │
```

**On failure:** progress stops, error shown, Back and Exit buttons appear.

**Worker pattern:** generation runs in a Textual worker (`run_worker`) to avoid blocking the UI. Each file writes individually so the progress bar advances per-file.

---

### Navigation Summary

```
Screen 1  →(Next)→  Screen 2  →(Next)→  Screen 3
Screen 3  →(Next)→  Screen 4  →(Next)→  Screen 5
Screen 5  →(Generate)→  Screen 6  →(Exit)→  app.exit()

Back always preserves entered values. Input is never lost.
```

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Tab` | Next widget |
| `Shift+Tab` | Previous widget |
| `Enter` | Activate focused button or toggle |
| `Space` | Toggle checkbox or radio |
| `Ctrl+C` / `Escape` | Cancel wizard — exits without writing files |

---

## Part 2: Template Design

All templates live in `dockerwiz/templates/<language>/<framework>/` as `.j2` files.

### Template Context

Every template receives these variables:

| Variable | Type | Example |
|---|---|---|
| `name` | `str` | `my-api` |
| `language` | `str` | `python` |
| `framework` | `str` | `fastapi` |
| `environment` | `str` | `dev` |
| `base_image` | `str` | `python:3.13-slim` |
| `app_port` | `int` | `8000` |
| `services` | `list[str]` | `["postgres", "redis"]` |
| `has_postgres` | `bool` | `True` |
| `has_mysql` | `bool` | `False` |
| `has_redis` | `bool` | `True` |
| `has_nginx` | `bool` | `False` |
| `has_mongo` | `bool` | `False` |
| `is_dev` | `bool` | `True` |
| `is_prod` | `bool` | `False` |
| `db_user` | `str` | `myuser` |
| `db_password` | `str` | `secret` |
| `db_name` | `str` | `mydb` |
| `db_port` | `int` | `5432` |

These are computed by `build_context()` in `generator.py` — keep logic out of templates.

---

### `Dockerfile.j2` — Python/FastAPI

```jinja
{% if is_prod %}
# ── Build stage ────────────────────────────────────────────────────────────────
FROM {{ base_image }} AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM {{ base_image }}
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
RUN useradd --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE {{ app_port }}
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{{ app_port }}", "--workers", "2"]

{% else %}
FROM {{ base_image }}
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {{ app_port }}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{{ app_port }}", "--reload"]
{% endif %}
```

**Go (Gin/Echo) dev:** uses `air` hot-reload (`RUN go install github.com/air-verse/air@latest`, `CMD ["air"]`). Prod: multi-stage with `FROM scratch`, binary compiled via `CGO_ENABLED=0 GOOS=linux go build`.

**Node.js (Express) dev:** `CMD ["npx", "nodemon", "index.js"]`. Prod: multi-stage, `npm ci --only=production`, non-root user via `adduser`.

**Node.js (NestJS) dev:** `CMD ["npx", "nest", "start", "--watch"]`.

---

### `docker-compose.yml.j2`

Shared across all stacks. Conditional service blocks with healthchecks:

```jinja
services:
  app:
    build: .
    ports:
      - "${APP_PORT:-{{ app_port }}}:{{ app_port }}"
    env_file: .env
    {% set has_deps = has_postgres or has_mysql or has_redis or has_mongo %}
    {% if has_deps %}
    depends_on:
      {% if has_postgres %}postgres:
        condition: service_healthy{% endif %}
      {% if has_redis %}redis:
        condition: service_healthy{% endif %}
    {% endif %}
    networks:
      - app-network

  {% if has_postgres %}
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
  {% endif %}

  {# redis, mysql, nginx, mongo blocks follow the same pattern #}

volumes:
  {% if has_postgres %}pgdata:{% endif %}
  {% if has_redis %}redisdata:{% endif %}
  {% if has_mongo %}mongodata:{% endif %}

networks:
  app-network:
    driver: bridge
```

---

### `docker-compose.override.yml.j2`

Dev-only — only written when `environment == "dev"`.

```jinja
# Development overrides — applied automatically by docker compose
services:
  app:
    volumes:
      - .:/app
    environment:
      DEBUG: "true"
```

---

### `.dockerignore.j2`

**Python:** `__pycache__/`, `*.py[cod]`, `.venv/`, `.env`, `.pytest_cache/`, `.mypy_cache/`

**Go:** `bin/`, `vendor/`, `tmp/` (Air hot-reload dir), `.env`

**Node.js:** `node_modules/`, `dist/`, `.env`

All stacks also exclude: `.git/`, `Dockerfile`, `docker-compose*.yml`, `.dockerignore`, `.vscode/`, `.idea/`

---

### `.env.example.j2`

```jinja
# Application
APP_PORT={{ app_port }}

{% if has_postgres %}
# PostgreSQL
DB_HOST=postgres
DB_PORT={{ db_port }}
DB_USER={{ db_user }}
DB_PASSWORD=changeme
DB_NAME={{ db_name }}
{% endif %}

{% if has_mysql %}
# MySQL
DB_HOST=mysql
DB_PORT=3306
DB_USER={{ db_user }}
DB_PASSWORD=changeme
DB_ROOT_PASSWORD=changeme
DB_NAME={{ db_name }}
{% endif %}

{% if has_redis %}
# Redis
REDIS_HOST=redis
REDIS_PORT=6379
{% endif %}

{% if has_nginx %}
# Nginx
NGINX_PORT=80
{% endif %}

{% if has_mongo %}
# MongoDB
MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_USER={{ db_user }}
MONGO_PASSWORD=changeme
{% endif %}
```

**Important:** `db_user` and `db_name` from Screen 4 are used as defaults, but `db_password` is always replaced with `changeme` — never write the real password into a file that could be committed.

---

### `Makefile.j2`

```jinja
.PHONY: up down logs shell build restart{% if has_postgres or has_mysql or has_mongo %} db{% endif %}

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec app bash || docker compose exec app sh

build:
	docker compose build --no-cache

restart:
	docker compose restart app

{% if has_postgres %}
db:
	docker compose exec postgres psql -U $${DB_USER} -d $${DB_NAME}
{% elif has_mysql %}
db:
	docker compose exec mysql mysql -u $${DB_USER} -p$${DB_PASSWORD} $${DB_NAME}
{% elif has_mongo %}
db:
	docker compose exec mongo mongosh -u $${MONGO_USER} -p $${MONGO_PASSWORD}
{% endif %}
```

**Critical:** Makefile recipe lines must use real tab characters, not spaces. Verify with `cat -A` — recipe lines must show `^I`.

**`$$` in Jinja2** renders as `$` in the output — required for Makefile shell variable syntax.

---

### `nginx.conf.j2`

Only generated when `has_nginx` is true.

```jinja
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:{{ app_port }};
    }

    server {
        listen 80;

        location / {
            proxy_pass         http://app;
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
        }
    }
}
```

`$host`, `$remote_addr` etc. are Nginx variables, not Jinja2. Jinja2 only treats `{{ }}`, `{% %}`, `{# #}` as special — `$` passes through unchanged.

---

### Template Conventions

| Convention | Rule |
|---|---|
| Whitespace control | Use `{%- -%}` trim blocks on conditional sections to avoid blank lines |
| Comments | Use `{# ... #}` Jinja2 comments |
| Variable naming | Match `ProjectConfig` field names exactly |
| Logic | Keep conditionals simple — complex logic belongs in `build_context()` |
| Makefile tabs | Template files must use real tab characters on recipe lines |
| Nginx `$vars` | Pass through unchanged — no escaping needed |
| Makefile `$vars` | Use `$$` in template → renders as `$` in output |
