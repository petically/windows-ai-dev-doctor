"""Consent is enforced by the engine; workers enforce wall-clock deadlines."""

import http.client
import multiprocessing
import socket
import ssl
import time
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Literal, Protocol

TARGETS = ("example.com", "www.python.org")
ProbeKind = Literal["dns", "https"]


@dataclass(frozen=True)
class ProbeResult:
    target: str
    stage: str
    ok: bool
    detail: str
    elapsed_ms: int = 0


class Network(Protocol):
    def probe(self, kind: ProbeKind, target: str, timeout: float) -> ProbeResult: ...


def _perform(kind: ProbeKind, target: str, timeout: float) -> ProbeResult:
    start = time.monotonic()
    stage = "dns"
    sock: socket.socket | None = None
    try:
        addresses = socket.getaddrinfo(target, 443, type=socket.SOCK_STREAM)
        if kind == "dns":
            ips = sorted({str(item[4][0]) for item in addresses})[:8]
            return ProbeResult(
                target, stage, True, ", ".join(ips), int((time.monotonic() - start) * 1000)
            )
        stage = "tcp"
        # Try all resolved addresses within the remaining overall budget.
        for family, socktype, proto, _, address in addresses:
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                break
            sock = socket.socket(family, socktype, proto)
            sock.settimeout(min(remaining, 1.5))
            try:
                sock.connect(address)
                break
            except OSError:
                sock.close()
                sock = None
        if sock is None:
            return ProbeResult(
                target, stage, False, "No resolved address accepted a TCP connection"
            )
        stage = "tls"
        sock.settimeout(max(0.1, timeout - (time.monotonic() - start)))
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=target)
        stage = "http"
        sock.sendall(
            f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n".encode("ascii")
        )
        response = http.client.HTTPResponse(sock)
        response.begin()
        status = response.status
        response.close()
        return ProbeResult(
            target,
            stage,
            200 <= status < 400,
            f"HTTP {status}",
            int((time.monotonic() - start) * 1000),
        )
    except (OSError, http.client.HTTPException, ValueError):
        return ProbeResult(
            target,
            stage,
            False,
            f"{stage.upper()} probe failed",
            int((time.monotonic() - start) * 1000),
        )
    finally:
        if sock is not None:
            sock.close()


def _worker(pipe: Connection, kind: ProbeKind, target: str, timeout: float) -> None:
    try:
        pipe.send(_perform(kind, target, timeout))
    finally:
        pipe.close()


class NetworkProbe:
    def probe(self, kind: ProbeKind, target: str, timeout: float) -> ProbeResult:
        if kind not in ("dns", "https") or target not in TARGETS or not 0.1 <= timeout <= 30:
            raise ValueError("Unreviewed network probe")
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=_worker, args=(child, kind, target, timeout), daemon=True)
        started = False
        try:
            process.start()
            started = True
            child.close()
            if parent.poll(timeout):
                value = parent.recv()
                if isinstance(value, ProbeResult):
                    return value
                return ProbeResult(target, "worker", False, "Invalid probe response")
            return ProbeResult(target, "timeout", False, "Overall probe deadline exceeded")
        except (OSError, EOFError):
            return ProbeResult(target, "worker", False, "Probe worker unavailable")
        finally:
            parent.close()
            child.close()
            if started:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
                if not process.is_alive():
                    process.close()
