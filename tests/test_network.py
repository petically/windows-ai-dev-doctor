import socket
import ssl
import time
from multiprocessing.connection import Connection
from unittest.mock import MagicMock, patch

import pytest

from ai_dev_doctor.core.network import NetworkProbe, ProbeKind, ProbeResult, _perform


def stalled_worker(pipe: Connection, kind: ProbeKind, target: str, timeout: float) -> None:
    time.sleep(20)


def fixture_worker(pipe: Connection, kind: ProbeKind, target: str, timeout: float) -> None:
    pipe.send(ProbeResult(target, "dns", True, "fixture"))
    pipe.close()


def test_network_worker_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ai_dev_doctor.core.network._worker", stalled_worker)
    start = time.monotonic()
    result = NetworkProbe().probe("dns", "example.com", 0.1)
    assert result.stage == "timeout"
    assert time.monotonic() - start < 4


def test_network_worker_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ai_dev_doctor.core.network._worker", fixture_worker)
    assert NetworkProbe().probe("dns", "example.com", 4).detail == "fixture"


def test_reject_arbitrary_target() -> None:
    with pytest.raises(ValueError):
        NetworkProbe().probe("https", "private.example", 1)


def test_dns_failure_classification() -> None:
    with patch("socket.getaddrinfo", side_effect=socket.gaierror("private message")):
        result = _perform("https", "example.com", 1)
    assert not result.ok and result.stage == "dns"
    assert "private" not in result.detail


def test_dns_addresses() -> None:
    addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443))]
    with patch("socket.getaddrinfo", return_value=addresses):
        result = _perform("dns", "example.com", 1)
    assert result.ok and result.detail == "192.0.2.1"


@pytest.mark.parametrize("stage", ["tcp", "tls", "http", "success"])
def test_https_stages(stage: str) -> None:
    addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443))]
    sock = MagicMock()
    if stage == "tcp":
        sock.connect.side_effect = OSError("private message")
    tls = MagicMock()
    tls.wrap_socket.return_value = sock
    if stage == "tls":
        tls.wrap_socket.side_effect = ssl.SSLError("private TLS message")
    response = MagicMock()
    response.status = 503 if stage == "http" else 200
    with (
        patch("socket.getaddrinfo", return_value=addresses),
        patch("socket.socket", return_value=sock),
        patch("ssl.create_default_context", return_value=tls),
        patch("http.client.HTTPResponse", return_value=response),
    ):
        result = _perform("https", "example.com", 1)
    assert result.ok == (stage == "success")
    assert result.stage == ("http" if stage == "success" else stage)
    if stage == "success":
        tls.wrap_socket.assert_called_once_with(sock, server_hostname="example.com")
        assert b"HEAD / HTTP/1.1" in sock.sendall.call_args.args[0]
    sock.close.assert_called()


def test_tcp_probe_stops_before_tls() -> None:
    addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443))]
    sock = MagicMock()
    with (
        patch("socket.getaddrinfo", return_value=addresses),
        patch("socket.socket", return_value=sock),
        patch("ssl.create_default_context") as tls,
    ):
        result = _perform("tcp", "example.com", 1)
    assert result.ok and result.stage == "tcp"
    assert result.detail == "TCP connection established"
    tls.assert_not_called()
    sock.close.assert_called()
