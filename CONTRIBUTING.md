# Contributing to dockerwiz

Thank you for your interest in contributing.

## Getting Started

```bash
git clone https://github.com/TaukTauk/dockerwiz
cd dockerwiz
pip install -e .
```

Install dev dependencies via Hatch:

```bash
pip install hatch
hatch shell
```

## Development Workflow

```bash
hatch run test        # run all tests
hatch run lint        # check for lint errors
hatch run lint-fix    # auto-fix lint errors
hatch run types       # run mypy type checking
hatch run check       # lint + types + tests (mirrors CI)
```

## Running the CLI Locally

```bash
pip install -e .
dockerwiz --help
dockerwiz new
```

## Project Structure

See [CLAUDE.md](CLAUDE.md) for module responsibilities and dependency rules.

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(new): add PHP Laravel stack support
fix(health): handle missing .env file gracefully
docs(readme): update installation instructions
```

Valid scopes: `new`, `health`, `shell`, `clean`, `config`, `logs`, `monitor`,
`update`, `convert`, `publish`, `generator`, `docker-hub`, `tui`, `cli`, `deps`, `release`

## Adding a New Stack

1. Add a `StackDefinition` entry to `dockerwiz/stacks.py`
2. Create a template directory at `dockerwiz/templates/<language>/<framework>/`
3. Add at minimum: `Dockerfile.j2`, `docker-compose.yml.j2`, `.dockerignore.j2`, `Makefile.j2`
4. Update `build_jinja_env()` in `generator.py` if the new language needs special handling
5. Add snapshot tests for the new stack

## Adding a New Service

1. Add a `ServiceDefinition` entry to `dockerwiz/services.py`
2. Add Jinja2 conditionals in the compose/Makefile templates (follow existing `has_postgres` pattern)
3. Add the service checkbox to `dockerwiz/tui/screens/services.py`
4. Update snapshot tests

## Submitting a Pull Request

- Keep PRs focused on a single change
- Ensure `hatch run check` passes
- Update snapshot files with `pytest --snapshot-update` if templates changed
- Add or update tests for new behaviour

## Reporting Issues

Open an issue at [github.com/TaukTauk/dockerwiz/issues](https://github.com/TaukTauk/dockerwiz/issues).
Include: OS, Python version, `dockerwiz version` output, and the full error message.
