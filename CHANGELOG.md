# Changelog

All notable changes to dockerwiz are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/TaukTauk/dockerwiz/releases/tag/v0.1.0
