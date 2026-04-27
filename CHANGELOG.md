# Changelog

All notable changes to dockerwiz are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.2] — 2026-04-27

### Fixed

- **`hatch test` missing dependencies**: `respx`, `pytest-asyncio`, and `pytest-snapshot` were only
  declared in the `default` hatch environment. The built-in `hatch-test` environment (used by
  `hatch test`) never received them, causing an `ImportError` on collection. Added a
  `[tool.hatch.envs.hatch-test]` section with `extra-dependencies` so `hatch test` works out of
  the box.
- **Test matrix ignored by `hatch test`**: the Python version matrix was declared under
  `[[tool.hatch.envs.test.matrix]]` instead of `[[tool.hatch.envs.hatch-test.matrix]]`, so
  `hatch test` fell back to the system Python (3.14) rather than the declared 3.11–3.13 range.
- **`test_fetch_all_versions_offline` flaky on warm cache**: the test mocked Docker Hub HTTP calls
  with `respx` but did not patch the disk cache. If `~/.dockerwiz/cache.json` held fresh entries,
  `fetch_all_versions` returned cached data without making any HTTP requests and `is_live` stayed
  `True`, flipping the assertion. Fixed by patching `_load_cache` to return an empty
  `VersionCache()` for the duration of the test.
- **Pydantic v2.11 deprecation warnings**: `model_fields` was accessed on model *instances* in
  `config.py` and `cli.py`. Pydantic v2.11 deprecates instance-level access in favour of
  `type(obj).model_fields`. Both call-sites updated to avoid the deprecation warning.

---

## [0.1.1] — 2026-04-25

### Fixed

- **TUI — short terminal overlap**: all 6 wizard screens now use `VerticalScroll` as the outer
  container instead of plain `Container`. Textual's `Container` has scrolling disabled at the widget
  level, so `overflow-y: auto` in CSS was silently ignored and content spilled out below the
  terminal, overlapping the footer. `VerticalScroll` has scrolling enabled natively; content now
  scrolls cleanly on any terminal height.
- **TUI — language screen crash on rapid selection**: switching language radio buttons quickly
  caused a `ValueError` crash (`RadioButton is not in list`). Root cause: Textual's `RadioSet`
  keeps an internal `_pressed_button` reference that is not cleared when children are removed;
  mutating children while that reference is stale corrupts internal state. Fixed by pre-composing
  one `RadioSet` per language at screen startup and toggling `.display` on language change — no
  DOM mutation at runtime.
- **TUI — framework multi-select glitch**: same `_pressed_button` corruption caused both the old
  and new framework buttons to appear selected simultaneously when switching languages.
- **Dockerfile missing image name prefix**: the base-image dropdown populated from Docker Hub tags
  returned bare tags (`3.14-slim`) without the image name. The `FROM` line rendered as
  `FROM 3.14-slim` instead of `FROM python:3.14-slim`. Tags are now prefixed with the image key
  (`python:`, `golang:`, `node:`) before being stored in `base_image`.
- **`.env` not created after generation**: `make up` failed silently because `docker-compose.yml`
  references `env_file: .env` but only `.env.example` was written. The generator now auto-copies
  `.env.example` → `.env` immediately after writing all files, so `make up` works out of the box.
- **`DB_PASSWORD`, `DB_ROOT_PASSWORD`, `MONGO_PASSWORD` hardcoded as `changeme`**: all six
  `.env.example.j2` templates used the literal string `changeme` instead of the `{{ db_password }}`
  template variable. The password entered in wizard step 4 was discarded.
- **`health` command spurious "0 warning(s)" output**: `run_health_check()` never returns a `WARN`
  status, so the warning count was always zero. Removed the dead branch; summary now shows only
  failure count or "All checks passed."

### Added

- Tests for previously untested v0.1.0 commands: `start`, `health`, `shell`, `clean`,
  `config unset` — 11 new test cases covering happy paths and error paths.

---

## [0.1.0] — 2026-04-19

Initial release.

### Added

- `dockerwiz new` — 6-screen interactive TUI wizard (Textual) that generates a complete Docker scaffold
- `dockerwiz start [service]` — start Docker Compose services with Docker availability check
- `dockerwiz health` — validate `docker-compose.yml` syntax and report container states
- `dockerwiz shell <service>` — exec into a running container; auto-selects `bash`/`sh`; launches DB clients for `postgres`, `mysql`, `redis`, `mongo`
- `dockerwiz clean` — identify and remove stopped containers, dangling images, and unused volumes
- `dockerwiz config set/get/list/unset` — persist user preferences in `~/.dockerwiz/config.toml`
- `dockerwiz list stacks` — show all supported language/framework stacks
- `dockerwiz list services` — show all supported services
- `dockerwiz version` — show installed version
- Supported stacks: Python/FastAPI, Python/Django, Go/Gin, Go/Echo, Node.js/Express, Node.js/NestJS
- Supported services: PostgreSQL, MySQL, Redis, Nginx, MongoDB
- Generated files: `Dockerfile`, `docker-compose.yml`, `docker-compose.override.yml`, `.dockerignore`, `.env.example`, `Makefile`, `nginx.conf` (when Nginx selected)
- Dev vs prod modes: single-stage vs multi-stage Dockerfile, non-root user in prod
- Docker Hub API integration with local cache (`~/.dockerwiz/cache.json`, TTL 24h) and offline fallback
- User template overrides via `~/.dockerwiz/templates/`
- Unexpected errors logged to `~/.dockerwiz/logs/debug.log`

[0.1.2]: https://github.com/TaukTauk/dockerwiz/releases/tag/v0.1.2
[0.1.1]: https://github.com/TaukTauk/dockerwiz/releases/tag/v0.1.1
[0.1.0]: https://github.com/TaukTauk/dockerwiz/releases/tag/v0.1.0
