"""Tests for the CLI entrypoint via typer.testing.CliRunner."""

from typer.testing import CliRunner

from dockerwiz.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "dockerwiz" in result.output


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "new" in result.output
    assert "version" in result.output


def test_list_stacks():
    result = runner.invoke(app, ["list", "stacks"])
    assert result.exit_code == 0
    assert "fastapi" in result.output.lower() or "FastAPI" in result.output
    assert "django" in result.output.lower() or "Django" in result.output


def test_list_services():
    result = runner.invoke(app, ["list", "services"])
    assert result.exit_code == 0
    assert "postgres" in result.output.lower() or "PostgreSQL" in result.output


def test_config_set_and_get(tmp_path, monkeypatch):
    monkeypatch.setattr("dockerwiz.config.CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setattr("dockerwiz.config.CONFIG_DIR",  tmp_path)

    result = runner.invoke(app, ["config", "set", "default.language", "python"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["config", "get", "default.language"])
    assert result.exit_code == 0
    assert "python" in result.output


def test_config_set_invalid_key():
    result = runner.invoke(app, ["config", "set", "invalid.key", "value"])
    assert result.exit_code != 0


def test_config_list(tmp_path, monkeypatch):
    monkeypatch.setattr("dockerwiz.config.CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setattr("dockerwiz.config.CONFIG_DIR",  tmp_path)

    result = runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0
    assert "defaults" in result.output
