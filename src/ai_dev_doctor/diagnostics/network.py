"""Network, proxy, adapter, route and listener diagnostics."""

import ipaddress

from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.core.network import TARGETS, ProbeKind
from ai_dev_doctor.core.windows import ProxyState
from ai_dev_doctor.diagnostics.parsing import ProxyEndpoint, parse_proxy, parse_windows_proxy
from ai_dev_doctor.models import CheckResult, Severity, Status

COMMON_PORTS = (1080, 3000, 3128, 5173, 7890, 8000, 8080, 8888)


def _endpoint_label(endpoint: ProxyEndpoint) -> str:
    host = endpoint.host.casefold().strip("[]")
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    location = "localhost" if local else "remote host"
    return f"{endpoint.scheme} {location} port {endpoint.port}"


def proxy_check(ctx: Context) -> CheckResult:
    evidence: list[tuple[str, str]] = []
    endpoints = set()
    malformed = False
    for key, value in ctx.host.environment.items():
        upper = key.upper()
        if upper not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY") or not value:
            continue
        if upper == "NO_PROXY":
            evidence.append((upper, "configured (host list omitted)"))
            continue
        endpoint = parse_proxy(value)
        if endpoint is None:
            malformed = True
            evidence.append((upper, "unrecognized URL (value omitted)"))
        else:
            endpoints.add(endpoint)
            evidence.append((upper, _endpoint_label(endpoint)))
    status = Status.WARNING if malformed else Status.INFO
    if malformed:
        summary = "Proxy environment contains an unrecognized URL"
    elif len(endpoints) > 1:
        summary = "Multiple proxy endpoints are configured"
    elif evidence:
        summary = "Proxy environment detected"
    else:
        summary = "No proxy environment variables detected"
    return CheckResult(
        "proxy-environment",
        "Proxy environment",
        "network",
        status,
        summary,
        evidence=tuple(evidence),
        details=(
            "Proxy presence alone is not a fault; credentials and NO_PROXY hosts are omitted.",
        ),
        severity=Severity.MEDIUM if malformed else Severity.INFO,
        recommendations=("Compare proxy layers with your intended routing.",) if evidence else (),
    )


def _proxy_result(check_id: str, name: str, state: ProxyState) -> CheckResult:
    if state.outcome == "unsupported":
        return CheckResult(
            check_id, name, "network", Status.SKIPPED, "Windows proxy API unavailable"
        )
    if state.outcome != "ok":
        return CheckResult(check_id, name, "network", Status.INFO, "Proxy state could not be read")
    endpoints = parse_windows_proxy(state.server) if state.server else ()
    malformed = bool(state.server and endpoints is None)
    evidence: list[tuple[str, str]] = [
        ("enabled", str(state.enabled).lower()),
        ("bypass-list", "configured" if state.bypass_configured else "not configured"),
    ]
    if state.auto_configured:
        evidence.append(("automatic-config", "configured (URL omitted)"))
    if endpoints:
        evidence.extend(("endpoint", _endpoint_label(endpoint)) for endpoint in endpoints)
    if malformed:
        evidence.append(("endpoint", "unrecognized (value omitted)"))
    status = Status.WARNING if malformed else Status.INFO
    return CheckResult(
        check_id,
        name,
        "network",
        status,
        "Proxy configuration needs review"
        if malformed
        else (
            "Proxy configuration detected"
            if state.enabled or state.auto_configured
            else "Direct access configured"
        ),
        evidence=tuple(evidence),
        severity=Severity.LOW if malformed else Severity.INFO,
        details=("Proxy server hostnames and bypass entries are omitted from reports.",),
    )


def system_proxy_check(ctx: Context) -> CheckResult:
    return _proxy_result("proxy-system", "Windows system proxy", ctx.windows.system_proxy())


def winhttp_proxy_check(ctx: Context) -> CheckResult:
    return _proxy_result("proxy-winhttp", "WinHTTP proxy", ctx.windows.winhttp_proxy())


def adapter_check(ctx: Context) -> CheckResult:
    adapters = ctx.windows.adapters()
    if adapters is None:
        return CheckResult(
            "network-adapters",
            "Network adapters and route",
            "network",
            Status.SKIPPED if not ctx.windows.available else Status.INFO,
            "Windows adapter API unavailable",
        )
    route = ctx.windows.default_route_interface()
    route_present = route is not None and any(adapter.index == route for adapter in adapters)
    tunnels = sum(adapter.possible_tunnel for adapter in adapters)
    evidence = (
        ("active-adapters", str(len(adapters))),
        ("default-route", "available" if route_present else "not identified"),
        ("possible-tunnel-adapters", str(tunnels)),
    )
    status = Status.PASS if adapters and route_present else Status.WARNING
    return CheckResult(
        "network-adapters",
        "Network adapters and route",
        "network",
        status,
        f"{len(adapters)} active adapter{'s' if len(adapters) != 1 else ''}; "
        + ("default route identified" if route_present else "default route not identified"),
        evidence=evidence,
        severity=Severity.MEDIUM if status == Status.WARNING else Severity.INFO,
        details=(
            "Tunnel classification is heuristic; a tunnel adapter is not inherently a problem.",
        ),
        recommendations=("Review adapter and route state if connectivity is failing.",)
        if status == Status.WARNING
        else (),
    )


def listener_check(ctx: Context) -> CheckResult:
    listeners = ctx.windows.listeners(COMMON_PORTS)
    if listeners is None:
        return CheckResult(
            "localhost-listeners",
            "Localhost listeners",
            "network",
            Status.SKIPPED if not ctx.windows.available else Status.INFO,
            "Windows TCP listener table unavailable",
        )
    evidence = tuple((f"port-{item.port}", f"listening (PID {item.pid})") for item in listeners)
    return CheckResult(
        "localhost-listeners",
        "Localhost listeners",
        "network",
        Status.INFO,
        f"{len(listeners)} listener{'s' if len(listeners) != 1 else ''} on inspected common ports",
        evidence=evidence,
        details=(
            "An occupied port is not automatically a conflict. Only IPv4 TCP listeners on a fixed port list are inspected.",
        ),
    )


def proxy_layers_check(ctx: Context) -> CheckResult:
    endpoints: list[ProxyEndpoint] = []
    for key, value in ctx.host.environment.items():
        if key.upper() in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY") and value:
            endpoint = parse_proxy(value)
            if endpoint:
                endpoints.append(endpoint)
    for state in (ctx.windows.system_proxy(), ctx.windows.winhttp_proxy()):
        if state.server:
            parsed = parse_windows_proxy(state.server)
            if parsed:
                endpoints.extend(parsed)
    listeners = ctx.windows.listeners(tuple(sorted({item.port for item in endpoints})))
    listening_ports = {item.port for item in listeners or ()}
    missing_local = []
    for endpoint in endpoints:
        host = endpoint.host.casefold().strip("[]")
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host == "localhost"
        if local and listeners is not None and endpoint.port not in listening_ports:
            missing_local.append(endpoint.port)
    adapters = ctx.windows.adapters() or ()
    tunnels = sum(adapter.possible_tunnel for adapter in adapters)
    layers = len(set((item.scheme, item.host.casefold(), item.port) for item in endpoints))
    if missing_local:
        status = Status.WARNING
        summary = "Possible conflict: configured localhost proxy has no inspected TCP listener"
    elif layers > 1 and tunnels:
        status = Status.INFO
        summary = "Multiple proxy endpoints and a possible tunnel adapter are active"
    elif layers > 1:
        status = Status.INFO
        summary = "Multiple proxy endpoints are configured"
    else:
        status = Status.INFO
        summary = "No corroborated proxy or tunnel conflict detected"
    return CheckResult(
        "proxy-layers",
        "Proxy and tunnel layers",
        "network",
        status,
        summary,
        evidence=(
            ("distinct-proxy-endpoints", str(layers)),
            ("possible-tunnel-adapters", str(tunnels)),
            ("localhost-proxies-without-listener", str(len(set(missing_local)))),
        ),
        severity=Severity.MEDIUM if missing_local else Severity.INFO,
        details=(
            "This check is conservative: different layers or an occupied port alone do not prove a fault.",
        ),
        recommendations=(
            "Start the intended proxy service or correct the localhost proxy endpoint.",
        )
        if missing_local
        else (),
    )


def _network(ctx: Context, kind: ProbeKind) -> CheckResult:
    probes = [ctx.network.probe(kind, target, ctx.config.network_timeout) for target in TARGETS]
    passed = sum(probe.ok for probe in probes)
    status = Status.PASS if passed == len(probes) else Status.WARNING if passed else Status.FAIL
    return CheckResult(
        f"network-{kind}",
        f"{kind.upper()} connectivity",
        "network",
        status,
        f"{passed}/{len(probes)} public targets succeeded",
        severity=Severity.MEDIUM if not passed else Severity.INFO,
        evidence=tuple(
            (probe.target, f"{probe.stage}: {probe.detail}; {probe.elapsed_ms} ms")
            for probe in probes
        ),
        details=(
            "Direct connectivity only; configured proxies are not used. No redirects are followed.",
        ),
        recommendations=()
        if status == Status.PASS
        else ("Review the failure stage; one target alone does not prove a general outage.",),
    )


def dns_check(ctx: Context) -> CheckResult:
    return _network(ctx, "dns")


def tcp_check(ctx: Context) -> CheckResult:
    return _network(ctx, "tcp")


def https_check(ctx: Context) -> CheckResult:
    return _network(ctx, "https")
