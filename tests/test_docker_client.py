"""Tests for docker_client.py — unit-testable parts only (no live Docker daemon)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dockerwiz.docker_client import check_port_available


class TestCheckPortAvailable:
    def test_returns_true_when_port_is_free(self):
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 111  # ECONNREFUSED — port is free

        with patch("dockerwiz.docker_client.socket.socket", return_value=mock_sock):
            assert check_port_available(5432) is True

    def test_returns_false_when_port_is_in_use(self):
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 0  # 0 = connected = port in use

        with patch("dockerwiz.docker_client.socket.socket", return_value=mock_sock):
            assert check_port_available(5432) is False

    def test_checks_localhost(self):
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 111

        with patch("dockerwiz.docker_client.socket.socket", return_value=mock_sock):
            check_port_available(8080)
            mock_sock.connect_ex.assert_called_once_with(("127.0.0.1", 8080))

    def test_sets_timeout(self):
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect_ex.return_value = 111

        with patch("dockerwiz.docker_client.socket.socket", return_value=mock_sock):
            check_port_available(80)
            mock_sock.settimeout.assert_called_once_with(0.3)
