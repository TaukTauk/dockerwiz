# dockerwiz — Development

---

## 1. Project Setup

### Prerequisites

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install hatch
```

### Install in editable mode

```bash
pip install -e .
dockerwiz --help
dockerwiz version
```

### Common Commands

```bash
hatch run test          # run tests
hatch run test-cov      # tests with coverage
hatch run lint          # ruff check
hatch run lint-fix      # ruff check --fix
hatch run format        # ruff format
hatch run types         # mypy
hatch run check         # lint + types + test (mirrors CI)

pytest --snapshot-update   # update golden files after intentional template changes
```

---

## 2. Tech Stack

| Concern | Tool |
|---|---|
| Language | Python 3.11+ |
| TUI framework | Textual ≥0.60.0 |
| CLI framework | Typer ≥0.12.0 |
| Templating | Jinja2 ≥3.1.0 |
| HTTP client | httpx ≥0.27.0 (async) |
| Docker SDK | docker ≥7.0.0 |
| Data validation | Pydantic v2 ≥2.0.0 |
| Terminal output | Rich ≥13.0.0 |
| Config files | tomllib (stdlib read) + tomli-w ≥1.0.0 (write) |
| Build | hatchling |
| Lint / format | Ruff ≥0.4.0 |
| Type checker | Mypy ≥1.10.0 (strict) |
| Test runner | Pytest ≥8.0.0 |

### Dependency rationale

| Package | Floor | Reason |
|---|---|---|
| `textual` | 0.60.0 | Stable screen/widget API |
| `typer` | 0.12.0 | `Annotated` type hint support |
| `httpx` | 0.27.0 | Stable async client interface |
| `docker` | 7.0.0 | Dropped Python 3.7; stable API |
| `pydantic` | 2.0.0 | v2 significantly faster than v1 |
| `tomli-w` | 1.0.0 | Writing TOML; stdlib handles reading |

---

## 3. `pyproject.toml`

```toml
[build-system]
requires      = ["hatchling"]
build-backend = "hatchling.build"

[project]
name            = "dockerwiz"
version         = "0.1.0"
description     = "Generate production-ready Docker setups through an interactive terminal wizard."
readme          = "README.md"
license         = { text = "MIT" }
requires-python = ">=3.11"
authors         = [{ name = "Tauk Tauk", email = "tauktauk51833@gmail.com" }]
keywords        = ["docker", "cli", "devtools", "tui", "dockerfile", "docker-compose", "scaffold"]
classifiers     = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Build Tools",
    "Topic :: Utilities",
]
dependencies = [
    "textual>=0.60.0",
    "typer>=0.12.0",
    "jinja2>=3.1.0",
    "httpx>=0.27.0",
    "docker>=7.0.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
    "tomli-w>=1.0.0",
]

[project.scripts]
dockerwiz = "dockerwiz.cli:main"

[project.urls]
Homepage  = "https://github.com/TaukTauk/dockerwiz"
Repository = "https://github.com/TaukTauk/dockerwiz"
Issues    = "https://github.com/TaukTauk/dockerwiz/issues"
Changelog = "https://github.com/TaukTauk/dockerwiz/blob/main/CHANGELOG.md"

[tool.hatchling.build.targets.wheel]
packages = ["dockerwiz"]

[tool.hatch.envs.default]
dependencies = [
    "pytest>=8.0.0",
    "pytest-snapshot>=0.9.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "types-docker",
]

[tool.hatch.envs.default.scripts]
test     = "pytest tests/ -v"
test-cov = "pytest tests/ --cov=dockerwiz --cov-report=term-missing --cov-report=xml"
lint     = "ruff check ."
lint-fix = "ruff check . --fix"
format   = "ruff format ."
types    = "mypy dockerwiz/"
check    = ["lint", "types", "test"]

[[tool.hatch.envs.test.matrix]]
python = ["3.11", "3.12", "3.13"]

[tool.pytest.ini_options]
asyncio_mode  = "auto"
snapshot_path = "tests/snapshots"
testpaths     = ["tests"]
addopts       = "-v --tb=short"

[tool.ruff]
target-version = "py311"
line-length    = 100
src            = ["dockerwiz", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "N", "ANN", "S", "PTH"]
ignore = ["ANN101", "ANN102", "S101"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ANN", "S"]

[tool.ruff.lint.isort]
known-first-party = ["dockerwiz"]

[tool.mypy]
python_version         = "3.11"
strict                 = true
warn_return_any        = true
warn_unused_configs    = true
warn_unused_ignores    = true
disallow_untyped_defs  = true
ignore_missing_imports = true

[tool.coverage.run]
source = ["dockerwiz"]
omit   = ["tests/*", "dockerwiz/__main__.py"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError"]
```

**Note:** dependencies must be a TOML array under `[project]`, not a `[project.dependencies]` table — hatchling rejects the table form.

---

## 4. Testing Strategy

### Test Layers

| Layer | Tool | Coverage target |
|---|---|---|
| Generator (snapshot) | `pytest-snapshot` | 95%+ |
| Docker Hub API | `respx` | 90%+ |
| TUI screens | Textual test client | 60%+ critical paths |
| CLI entrypoint | `typer.testing.CliRunner` | 80%+ |
| Docker SDK commands | Integration tests only | — |

### Generator — Snapshot Tests

```python
# tests/test_generator.py
@pytest.fixture
def fastapi_dev_config():
    return ProjectConfig(
        name="my-api", language="python", framework="fastapi",
        services=["postgres", "redis"], environment="dev", app_port=8000,
        db_port=5432, db_user="myuser", db_password="secret",
        db_name="mydb", base_image="python:3.13-slim",
    )

def test_dockerfile_snapshot(fastapi_dev_config, snapshot):
    result = generate(fastapi_dev_config)
    snapshot.assert_match(result["Dockerfile"], "Dockerfile")
```

Snapshot directory structure mirrors test configs:
```
tests/snapshots/
├── python_fastapi_dev/
├── python_fastapi_prod/
├── go_gin_dev/
├── node_express_dev/
└── python_fastapi_dev_postgres_redis_nginx/
```

Update snapshots after intentional template changes: `pytest --snapshot-update`. Review the diff in git to confirm changes are intentional.

### Docker Hub API — respx Mocks

```python
# tests/test_docker_hub.py
@pytest.mark.asyncio
@respx.mock
async def test_fetch_filters_tags():
    respx.get("https://hub.docker.com/v2/repositories/library/python/tags").mock(
        return_value=httpx.Response(200, json={
            "results": [{"name": "3.13-slim"}, {"name": "3.13-bullseye"}, {"name": "latest"}]
        })
    )
    tags, is_live = await fetch_image_versions("python")
    assert tags == ["3.13-slim"]
    assert is_live is True

@pytest.mark.asyncio
@respx.mock
async def test_offline_fallback():
    respx.get(...).mock(side_effect=httpx.ConnectError("no network"))
    tags, is_live = await fetch_image_versions("python")
    assert tags == FALLBACK_VERSIONS["python"]
    assert is_live is False
```

Never make real network calls in tests.

### CLI — CliRunner

```python
# tests/test_cli.py
from typer.testing import CliRunner
from dockerwiz.cli import app

runner = CliRunner()

def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0

def test_list_stacks():
    result = runner.invoke(app, ["list", "stacks"])
    assert result.exit_code == 0
    assert "python" in result.output
```

### What Not to Unit Test

`dockerwiz shell` and `dockerwiz clean` wrap Docker SDK calls requiring a live daemon. Test these in `tests/integration/` only, running against a real Docker daemon in CI.

---

## 5. Versioning

### Scheme: SemVer

| Segment | When |
|---|---|
| MAJOR | Breaking CLI change or generated file format change |
| MINOR | New command, new stack, new service |
| PATCH | Bug fix, template correction, dependency update |

Single source of truth: `version` field in `pyproject.toml`. CLI reads it via `importlib.metadata.version("dockerwiz")`.

### Conventional Commits

Format: `<type>(<scope>): <short description>`

Valid types: `feat`, `fix`, `docs`, `chore`, `refactor`, `perf`, `test`, `ci`

Valid scopes: `new`, `health`, `shell`, `clean`, `config`, `logs`, `monitor`, `update`, `convert`, `publish`, `generator`, `docker-hub`, `tui`, `cli`, `deps`, `release`

Examples:
```
feat(new): add MongoDB service support
fix(health): handle missing .env file gracefully
feat(new)!: rename --env flag to --environment

BREAKING CHANGE: the --env flag has been renamed to --environment
```

### Changelog with git-cliff

```bash
pip install git-cliff

git-cliff --output CHANGELOG.md         # full history
git-cliff v1.0.0..v1.1.0 --output CHANGELOG.md  # range
git-cliff --unreleased                   # preview unreleased
```

`cliff.toml` config groups commits into: New Features, Bug Fixes, Performance, Internal Changes, Documentation. Skips `chore`, `ci`, `test`.

### Release Process

```bash
git checkout main && git pull origin main
git-cliff --unreleased                     # preview changelog
hatch version minor                        # bump 1.0.0 → 1.1.0
git-cliff --output CHANGELOG.md
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): v1.1.0"
git tag v1.1.0
git push origin main && git push origin v1.1.0
# GitHub Actions release.yml triggers automatically
```

Pre-release tags: `v1.1.0b1` → GitHub Release marked as pre-release via `softprops/action-gh-release`.

---

## 6. CI/CD Pipeline

### `ci.yml` — Every push and PR

```yaml
on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install hatch && hatch env create
      - run: hatch run lint
      - run: hatch run types
      - run: hatch run test-cov
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install -e .
      - run: pytest tests/integration/ -v
```

### `release.yml` — Tag push (`v*.*.*`)

Flow: CI tests → build binaries (parallel, 3 OS) → publish to PyPI → create GitHub Release with all binaries.

```yaml
on:
  push:
    tags: ["v*.*.*"]

jobs:
  test:
    uses: ./.github/workflows/ci.yml

  build-binaries:
    needs: test
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - { os: ubuntu-latest,  artifact: dockerwiz-linux-x64 }
          - { os: macos-latest,   artifact: dockerwiz-darwin-arm64 }
          - { os: windows-latest, artifact: dockerwiz-windows-x64.exe }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install pyinstaller && pip install -e .
      - run: pyinstaller --onefile --name ${{ matrix.artifact }} dockerwiz/cli.py
      - uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: dist/${{ matrix.artifact }}

  publish-pypi:
    needs: test
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install hatch && hatch build
      - uses: pypa/gh-action-pypi-publish@release/v1

  create-github-release:
    needs: [build-binaries, publish-pypi]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { path: dist/ }
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/**/*
          generate_release_notes: true
```

### PyPI Trusted Publishing (OIDC)

No API key secret needed. One-time setup on PyPI: add trusted publisher → GitHub, repo `TaukTauk/dockerwiz`, workflow `release.yml`. The `id-token: write` permission handles auth automatically.

### Secrets

| Secret | Purpose |
|---|---|
| `CODECOV_TOKEN` | Upload coverage reports |
| `GITHUB_TOKEN` | Automatic — create release, upload assets |
| PyPI trusted publishing | No secret needed — OIDC |

### Branch Strategy

```
main        production-ready, protected (require PR + CI pass)
dev         active development
feature/*   individual feature branches

Tags: v1.0.0, v1.0.1, v1.1.0  → trigger release pipeline
```

---

## 7. Licensing and OSS Setup

**License: MIT** — dominant in Python CLI ecosystem (`ruff`, `typer`, `httpie`, `black`), short, no friction for contributors or users.

### Required Files

```
LICENSE
README.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md   (Contributor Covenant v2.1)
SECURITY.md
CHANGELOG.md
DEVELOPMENT.md
```

### GitHub Repository Settings

**Branch protection on `main`:** require PR review, require CI to pass (`test (3.11/3.12/3.13)`, `commitlint`), no direct pushes.

**Repository topics:** `docker`, `cli`, `python`, `devtools`, `tui`, `dockerfile`, `docker-compose`, `scaffolding`, `code-generator`, `textual`

**Issue templates:** bug report, feature request (under `.github/ISSUE_TEMPLATE/`).

**PR template:** Summary, Type of Change checkboxes, Checklist (tests pass, lint passes, snapshots updated, CHANGELOG updated, Conventional Commits format).

### CONTRIBUTING.md Highlights

- Fork, clone, `pip install hatch && hatch env create`
- Conventional Commits format required
- Adding a stack: create templates + add entry to `stacks.py` + add snapshot tests
- Adding a service: add to `services.py` + update templates + add snapshot tests
- Snapshots must be updated when templates change: `pytest --snapshot-update`

---

## 8. Documentation

### v1.0 — README Only

README must cover: installation (pipx, brew, binary), quickstart, full command table, supported stacks and services, link to CONTRIBUTING.md. Keep under one screen of content for the summary section.

### v1.1 — MkDocs with Material Theme

```bash
pip install mkdocs-material
mkdocs serve      # local preview at http://127.0.0.1:8000
```

Hosted on GitHub Pages via `mkdocs gh-deploy --force` in `.github/workflows/docs.yml` (triggers on push to `main`).

Doc versioning with `mike` from v1.1 onward: `mike deploy --push --update-aliases ${{ github.ref_name }} latest`.

### Docstring Format (Google style)

```python
def generate(config: ProjectConfig) -> dict[str, str]:
    """
    Render all Jinja2 templates for the given project config.

    Args:
        config: The fully populated ProjectConfig from the TUI wizard.

    Returns:
        A dict mapping filename to rendered file content.

    Raises:
        GeneratorError: If a template is missing or rendering fails.
    """
```

All public functions and classes must have docstrings.

### v1.0 Documentation Checklist

- [ ] README covers install, quickstart, full command table, stacks, services
- [ ] CONTRIBUTING.md complete
- [ ] CODE_OF_CONDUCT.md present
- [ ] SECURITY.md present
- [ ] DEVELOPMENT.md complete
- [ ] CHANGELOG.md generated for v1.0.0
- [ ] All public functions have docstrings
- [ ] `--help` output accurate for every command and flag
