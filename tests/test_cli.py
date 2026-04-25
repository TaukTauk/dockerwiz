"""Tests for the CLI entrypoint via typer.testing.CliRunner."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from dockerwiz.cli import app
from dockerwiz.docker_client import DockerNotAvailableError

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


def test_config_unset(tmp_path, monkeypatch):
    monkeypatch.setattr("dockerwiz.config.CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setattr("dockerwiz.config.CONFIG_DIR",  tmp_path)

    runner.invoke(app, ["config", "set", "default.language", "python"])
    result = runner.invoke(app, ["config", "unset", "default.language"])
    assert result.exit_code == 0
    assert "default.language" in result.output


# ── dockerwiz start ────────────────────────────────────────────────────────────

def test_start_all_services():
    with patch("dockerwiz.cli.start_containers") as mock_start:
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0
        mock_start.assert_called_once_with(None)


def test_start_named_service():
    with patch("dockerwiz.cli.start_containers") as mock_start:
        result = runner.invoke(app, ["start", "web"])
        assert result.exit_code == 0
        mock_start.assert_called_once_with("web")


def test_start_docker_unavailable():
    err = DockerNotAvailableError("daemon down")
    with patch("dockerwiz.cli.start_containers", side_effect=err):
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 1


# ── dockerwiz health ───────────────────────────────────────────────────────────

def test_health_all_ok():
    ok_results = [
        {"service": "docker-compose.yml", "status": "OK", "message": "valid syntax"},
        {"service": "web",                "status": "OK", "message": "running (none)"},
    ]
    with patch("dockerwiz.cli.run_health_check", return_value=ok_results):
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output


def test_health_with_failures():
    fail_results = [
        {"service": "docker-compose.yml", "status": "OK",   "message": "valid syntax"},
        {"service": "db",                 "status": "FAIL", "message": "unhealthy"},
    ]
    with patch("dockerwiz.cli.run_health_check", return_value=fail_results):
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "1 failure" in result.output


# ── dockerwiz shell ────────────────────────────────────────────────────────────

def test_shell_calls_exec():
    with patch("dockerwiz.cli.exec_shell") as mock_exec:
        result = runner.invoke(app, ["shell", "web"])
        assert result.exit_code == 0
        mock_exec.assert_called_once_with("web")


def test_shell_docker_unavailable():
    with patch("dockerwiz.cli.exec_shell", side_effect=DockerNotAvailableError("daemon down")):
        result = runner.invoke(app, ["shell", "web"])
        assert result.exit_code == 1


# ── dockerwiz clean ────────────────────────────────────────────────────────────

def test_clean_nothing_to_remove():
    mock_client = MagicMock()
    empty_resources = {"stopped_containers": [], "dangling_images": []}
    with patch("dockerwiz.cli.require_docker", return_value=mock_client), \
         patch("dockerwiz.cli.list_unused_resources", return_value=empty_resources):
        result = runner.invoke(app, ["clean"])
        assert result.exit_code == 0
        assert "Nothing to clean" in result.output


def test_clean_with_force():
    mock_client = MagicMock()
    resources = {
        "stopped_containers": [MagicMock()],
        "dangling_images":    [MagicMock()],
    }
    clean_result = {"containers": 1, "images": 1}
    with patch("dockerwiz.cli.require_docker", return_value=mock_client), \
         patch("dockerwiz.cli.list_unused_resources", return_value=resources), \
         patch("dockerwiz.cli.clean_resources", return_value=clean_result) as mock_clean:
        result = runner.invoke(app, ["clean", "--force"])
        assert result.exit_code == 0
        mock_clean.assert_called_once()


def test_clean_docker_unavailable():
    with patch("dockerwiz.cli.require_docker", side_effect=DockerNotAvailableError("daemon down")):
        result = runner.invoke(app, ["clean"])
        assert result.exit_code == 1
