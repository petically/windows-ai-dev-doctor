"""Read-only Windows API and registry inspection behind a narrow typed boundary."""

from __future__ import annotations

import ctypes
import os
import shutil
import socket
import sys
from collections.abc import Mapping
from ctypes import wintypes
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Protocol, cast

from ai_dev_doctor.core.paths import is_local_path


@dataclass(frozen=True)
class WindowsVersion:
    product_name: str
    display_version: str
    build: str


@dataclass(frozen=True)
class DirectoryState:
    label: str
    path: str
    exists: bool
    readable: bool


@dataclass(frozen=True)
class DiskState:
    label: str
    free_bytes: int
    total_bytes: int


@dataclass(frozen=True)
class ProxyState:
    outcome: str
    enabled: bool = False
    server: str | None = None
    bypass_configured: bool = False
    auto_configured: bool = False


@dataclass(frozen=True)
class AdapterState:
    index: int
    kind: str
    possible_tunnel: bool


@dataclass(frozen=True)
class ListenerState:
    port: int
    pid: int


@dataclass(frozen=True)
class GPUState:
    name: str
    driver_version: str | None = None


@dataclass(frozen=True)
class AppState:
    installed: bool | None
    running: bool | None
    data_directories: int = 0
    config_readable: bool | None = None

    cache_directories: int = 0
    cache_bytes: int = 0
    cache_scan_truncated: bool = False


class WindowsInspector(Protocol):
    @property
    def available(self) -> bool: ...
    def version(self) -> WindowsVersion | None: ...
    def is_admin(self) -> bool | None: ...
    def important_directories(self) -> tuple[DirectoryState, ...]: ...
    def disks(self) -> tuple[DiskState, ...]: ...
    def webview2_versions(self) -> tuple[str, ...] | None: ...
    def system_proxy(self) -> ProxyState: ...
    def winhttp_proxy(self) -> ProxyState: ...
    def adapters(self) -> tuple[AdapterState, ...] | None: ...
    def default_route_interface(self) -> int | None: ...
    def listeners(self, ports: tuple[int, ...]) -> tuple[ListenerState, ...] | None: ...
    def process_names(self) -> tuple[str, ...] | None: ...
    def gpus(self) -> tuple[GPUState, ...] | None: ...
    def app_state(self, app: str) -> AppState: ...


class NullWindowsInspector:
    available = False

    def version(self) -> WindowsVersion | None:
        return None

    def is_admin(self) -> bool | None:
        return None

    def important_directories(self) -> tuple[DirectoryState, ...]:
        return ()

    def disks(self) -> tuple[DiskState, ...]:
        return ()

    def webview2_versions(self) -> tuple[str, ...] | None:
        return None

    def system_proxy(self) -> ProxyState:
        return ProxyState("unsupported")

    def winhttp_proxy(self) -> ProxyState:
        return ProxyState("unsupported")

    def adapters(self) -> tuple[AdapterState, ...] | None:
        return None

    def default_route_interface(self) -> int | None:
        return None

    def listeners(self, ports: tuple[int, ...]) -> tuple[ListenerState, ...] | None:
        return None

    def process_names(self) -> tuple[str, ...] | None:
        return None

    def gpus(self) -> tuple[GPUState, ...] | None:
        return None

    def app_state(self, app: str) -> AppState:
        return AppState(None, None)


def _registry_value(root: int, key: str, name: str) -> object | None:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(root, key, 0, winreg.KEY_READ) as handle:
            return cast(object, winreg.QueryValueEx(handle, name)[0])
    except OSError:
        return None


def _subkeys(root: int, key: str, limit: int = 512) -> tuple[str, ...]:
    if sys.platform != "win32":
        return ()
    import winreg

    values: list[str] = []
    try:
        with winreg.OpenKey(root, key, 0, winreg.KEY_READ) as handle:
            for index in range(limit):
                try:
                    values.append(winreg.EnumKey(handle, index))
                except OSError:
                    break
    except OSError:
        pass
    return tuple(values)


def _process_entries() -> tuple[tuple[int, str], ...] | None:
    if sys.platform != "win32":
        return None

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_snapshot = kernel32.CreateToolhelp32Snapshot
    create_snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    create_snapshot.restype = wintypes.HANDLE
    snapshot = create_snapshot(0x00000002, 0)
    process_first = kernel32.Process32FirstW
    process_first.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
    process_first.restype = wintypes.BOOL
    process_next = kernel32.Process32NextW
    process_next.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
    process_next.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    if snapshot == ctypes.c_void_p(-1).value:
        return None
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    values: list[tuple[int, str]] = []
    try:
        ok = process_first(snapshot, ctypes.byref(entry))
        while ok:
            values.append((int(entry.th32ProcessID), entry.szExeFile))
            ok = process_next(snapshot, ctypes.byref(entry))
    finally:
        close_handle(snapshot)
    return tuple(values)


def _cache_metadata(roots: tuple[Path, ...], limit: int = 4096) -> tuple[int, int, bool]:
    """Bounded metadata-only scan of known application roots for common cache directories."""
    cache_names = {"cache", "code cache", "gpucache"}
    stack: list[tuple[Path, int, bool]] = []
    for root in roots:
        try:
            if is_local_path(root) and root.is_dir():
                stack.append((root, 0, False))
        except OSError:
            pass
    cache_directories = 0
    total_bytes = 0
    inspected = 0
    truncated = False
    while stack:
        directory, depth, inside_cache = stack.pop()
        if depth > 5:
            truncated = True
            continue
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    inspected += 1
                    if inspected > limit:
                        truncated = True
                        return cache_directories, total_bytes, truncated
                    try:
                        if entry.is_symlink():
                            continue
                        entry_cache = inside_cache or entry.name.casefold() in cache_names
                        if entry.is_dir(follow_symlinks=False):
                            if entry_cache and not inside_cache:
                                cache_directories += 1
                            path = Path(entry.path)
                            if is_local_path(path):
                                stack.append((path, depth + 1, entry_cache))
                        elif entry_cache and entry.is_file(follow_symlinks=False):
                            total_bytes += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        truncated = True
        except OSError:
            truncated = True
    return cache_directories, total_bytes, truncated


class LocalWindowsInspector:
    """Best-effort Windows inspection without subprocesses or state changes."""

    def __init__(self, environment: Mapping[str, str]) -> None:
        self.environment = dict(environment)

    @property
    def available(self) -> bool:
        return sys.platform == "win32"

    def version(self) -> WindowsVersion | None:
        if not self.available:
            return None
        import winreg

        key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        product = _registry_value(winreg.HKEY_LOCAL_MACHINE, key, "ProductName")
        display = _registry_value(winreg.HKEY_LOCAL_MACHINE, key, "DisplayVersion")
        build = _registry_value(winreg.HKEY_LOCAL_MACHINE, key, "CurrentBuildNumber")
        ubr = _registry_value(winreg.HKEY_LOCAL_MACHINE, key, "UBR")
        if not all(isinstance(value, (str, int)) for value in (product, display, build)):
            return None
        product_text = str(product)
        try:
            build_number = int(str(build))
        except ValueError:
            return None
        if build_number >= 22000 and product_text.startswith("Windows 10"):
            # The legacy ProductName value can remain "Windows 10" on Windows 11.
            product_text = "Windows 11" + product_text.removeprefix("Windows 10")
        build_text = str(build_number) + (f".{ubr}" if isinstance(ubr, int) else "")
        return WindowsVersion(product_text, str(display), build_text)

    def is_admin(self) -> bool | None:
        if not self.available:
            return None
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return None

    def important_directories(self) -> tuple[DirectoryState, ...]:
        if not self.available:
            return ()
        labels = {
            "profile": self.environment.get("USERPROFILE"),
            "local-app-data": self.environment.get("LOCALAPPDATA"),
            "roaming-app-data": self.environment.get("APPDATA"),
            "program-data": self.environment.get("PROGRAMDATA"),
            "temporary": self.environment.get("TEMP") or self.environment.get("TMP"),
        }
        states: list[DirectoryState] = []
        for label, raw in labels.items():
            if not raw:
                continue
            path = Path(raw)
            if not is_local_path(path):
                states.append(DirectoryState(label, raw, False, False))
                continue
            try:
                states.append(
                    DirectoryState(label, raw, path.is_dir(), os.access(path, os.R_OK | os.X_OK))
                )
            except OSError:
                states.append(DirectoryState(label, raw, False, False))
        return tuple(states)

    def disks(self) -> tuple[DiskState, ...]:
        if not self.available:
            return ()
        candidates = {
            "system": self.environment.get("SYSTEMROOT"),
            "temporary": self.environment.get("TEMP") or self.environment.get("TMP"),
        }
        states: list[DiskState] = []
        seen: set[str] = set()
        for label, raw in candidates.items():
            if not raw:
                continue
            path = Path(raw)
            drive = path.anchor.casefold()
            if drive in seen or not is_local_path(path):
                continue
            seen.add(drive)
            try:
                usage = shutil.disk_usage(path)
            except OSError:
                continue
            states.append(DiskState(label, usage.free, usage.total))
        return tuple(states)

    def webview2_versions(self) -> tuple[str, ...] | None:
        if not self.available:
            return None
        import winreg

        guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        locations = (
            (
                winreg.HKEY_LOCAL_MACHINE,
                rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{guid}",
            ),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}"),
            (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{guid}"),
        )
        versions = {
            value
            for root, key in locations
            if isinstance((value := _registry_value(root, key, "pv")), str)
            and value not in ("", "0.0.0.0")
        }
        return tuple(sorted(versions))

    def system_proxy(self) -> ProxyState:
        if not self.available:
            return ProxyState("unsupported")
        import winreg

        key = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        enabled = _registry_value(winreg.HKEY_CURRENT_USER, key, "ProxyEnable")
        server = _registry_value(winreg.HKEY_CURRENT_USER, key, "ProxyServer")
        bypass = _registry_value(winreg.HKEY_CURRENT_USER, key, "ProxyOverride")
        auto = _registry_value(winreg.HKEY_CURRENT_USER, key, "AutoConfigURL")
        if enabled is None and server is None and auto is None:
            return ProxyState("unavailable")
        return ProxyState(
            "ok",
            bool(enabled),
            server if isinstance(server, str) and server else None,
            isinstance(bypass, str) and bool(bypass),
            isinstance(auto, str) and bool(auto),
        )

    def winhttp_proxy(self) -> ProxyState:
        if not self.available:
            return ProxyState("unsupported")

        class WINHTTP_PROXY_INFO(ctypes.Structure):
            _fields_ = [
                ("access_type", wintypes.DWORD),
                ("proxy", ctypes.c_void_p),
                ("bypass", ctypes.c_void_p),
            ]

        info = WINHTTP_PROXY_INFO()
        try:
            winhttp = ctypes.WinDLL("winhttp", use_last_error=True)
            get_default = winhttp.WinHttpGetDefaultProxyConfiguration
            get_default.argtypes = (ctypes.POINTER(WINHTTP_PROXY_INFO),)
            get_default.restype = wintypes.BOOL
            if not get_default(ctypes.byref(info)):
                return ProxyState("unavailable")
            proxy = ctypes.wstring_at(info.proxy) if info.proxy else None
            return ProxyState("ok", info.access_type == 3, proxy, bool(info.bypass))
        except (OSError, ValueError):
            return ProxyState("unavailable")
        finally:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            global_free = kernel32.GlobalFree
            global_free.argtypes = (ctypes.c_void_p,)
            global_free.restype = ctypes.c_void_p
            if info.proxy:
                global_free(info.proxy)
            if info.bypass:
                global_free(info.bypass)

    def adapters(self) -> tuple[AdapterState, ...] | None:
        if not self.available:
            return None

        class IP_ADAPTER_ADDRESSES(ctypes.Structure):
            pass

        pointer = ctypes.POINTER(IP_ADAPTER_ADDRESSES)
        IP_ADAPTER_ADDRESSES._fields_ = [
            ("Length", wintypes.ULONG),
            ("IfIndex", wintypes.DWORD),
            ("Next", pointer),
            ("AdapterName", ctypes.c_char_p),
            ("FirstUnicastAddress", ctypes.c_void_p),
            ("FirstAnycastAddress", ctypes.c_void_p),
            ("FirstMulticastAddress", ctypes.c_void_p),
            ("FirstDnsServerAddress", ctypes.c_void_p),
            ("DnsSuffix", wintypes.LPWSTR),
            ("Description", wintypes.LPWSTR),
            ("FriendlyName", wintypes.LPWSTR),
            ("PhysicalAddress", ctypes.c_ubyte * 8),
            ("PhysicalAddressLength", wintypes.DWORD),
            ("Flags", wintypes.DWORD),
            ("Mtu", wintypes.DWORD),
            ("IfType", wintypes.DWORD),
            ("OperStatus", ctypes.c_int),
        ]
        size = wintypes.ULONG(15_000)
        for _ in range(2):
            buffer = ctypes.create_string_buffer(size.value)
            result = ctypes.windll.iphlpapi.GetAdaptersAddresses(
                0, 0x0F, None, buffer, ctypes.byref(size)
            )
            if result == 0:
                break
            if result != 111:
                return None
        else:
            return None
        type_names = {6: "ethernet", 24: "loopback", 71: "wireless", 131: "tunnel"}
        states: list[AdapterState] = []
        current = ctypes.cast(buffer, pointer)
        count = 0
        while current and count < 256:
            item = current.contents
            friendly = (item.FriendlyName or "").casefold()
            possible_tunnel = item.IfType in (53, 131) or any(
                term in friendly for term in ("vpn", "tun", "tap", "wireguard", "wintun")
            )
            if item.OperStatus == 1:
                states.append(
                    AdapterState(
                        int(item.IfIndex),
                        type_names.get(int(item.IfType), f"type-{int(item.IfType)}"),
                        possible_tunnel,
                    )
                )
            current = item.Next
            count += 1
        return tuple(states)

    def default_route_interface(self) -> int | None:
        if not self.available:
            return None

        class SOCKADDR_IN(ctypes.Structure):
            _fields_ = [
                ("family", ctypes.c_ushort),
                ("port", ctypes.c_ushort),
                ("address", ctypes.c_ubyte * 4),
                ("zero", ctypes.c_ubyte * 8),
            ]

        target = SOCKADDR_IN(socket.AF_INET, 0, (1, 1, 1, 1), (0,) * 8)
        index = wintypes.DWORD()
        try:
            result = ctypes.windll.iphlpapi.GetBestInterfaceEx(
                ctypes.byref(target), ctypes.byref(index)
            )
        except (AttributeError, OSError):
            return None
        return int(index.value) if result == 0 else None

    def listeners(self, ports: tuple[int, ...]) -> tuple[ListenerState, ...] | None:
        if not self.available:
            return None

        class ROW(ctypes.Structure):
            _fields_ = [
                ("state", wintypes.DWORD),
                ("local_address", wintypes.DWORD),
                ("local_port", wintypes.DWORD),
                ("remote_address", wintypes.DWORD),
                ("remote_port", wintypes.DWORD),
                ("pid", wintypes.DWORD),
            ]

        size = wintypes.DWORD(0)
        api = ctypes.windll.iphlpapi.GetExtendedTcpTable
        result = api(None, ctypes.byref(size), False, socket.AF_INET, 3, 0)
        if result not in (0, 122) or size.value > 16 * 1024 * 1024:
            return None
        buffer = ctypes.create_string_buffer(size.value)
        if api(buffer, ctypes.byref(size), False, socket.AF_INET, 3, 0) != 0:
            return None
        count = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value
        base = ctypes.addressof(buffer) + ctypes.sizeof(wintypes.DWORD)
        found: list[ListenerState] = []
        for index in range(min(count, 65_536)):
            row = ROW.from_address(base + index * ctypes.sizeof(ROW))
            port = socket.ntohs(int(row.local_port) & 0xFFFF)
            if port in ports:
                found.append(ListenerState(port, int(row.pid)))
        return tuple(found)

    def process_names(self) -> tuple[str, ...] | None:
        entries = _process_entries()
        if entries is None:
            return None
        relevant = (
            "chatgpt",
            "codex",
            "git",
            "gh",
            "node",
            "python",
            "powershell",
            "pwsh",
            "wt",
            "wireguard",
            "openvpn",
            "clash",
            "tailscale",
            "zerotier",
        )
        names: set[str] = set()
        for _, name in entries:
            stem = Path(name).stem.casefold()
            if any(stem == term or stem.startswith(term + "-") for term in relevant):
                names.add(name)
        return tuple(sorted(names, key=str.casefold))

    def gpus(self) -> tuple[GPUState, ...] | None:
        if not self.available:
            return None
        import winreg

        base = r"SYSTEM\CurrentControlSet\Control\Video"
        values: set[GPUState] = set()
        for child in _subkeys(winreg.HKEY_LOCAL_MACHINE, base, 64):
            key = base + "\\" + child + r"\0000"
            name = _registry_value(winreg.HKEY_LOCAL_MACHINE, key, "DriverDesc")
            version = _registry_value(winreg.HKEY_LOCAL_MACHINE, key, "DriverVersion")
            if isinstance(name, str) and name:
                values.add(GPUState(name, version if isinstance(version, str) else None))
        return tuple(sorted(values, key=lambda item: item.name.casefold()))

    def app_state(self, app: str) -> AppState:
        if not self.available or app not in ("chatgpt", "codex", "terminal"):
            return AppState(None, None)
        processes = tuple(name.casefold() for name in (self.process_names() or ()))
        if app == "chatgpt":
            running = any("chatgpt" in name for name in processes)
            roots = (self.environment.get("LOCALAPPDATA"), self.environment.get("APPDATA"))
            candidates = tuple(
                Path(root) / "OpenAI" / "ChatGPT" for root in roots if root is not None
            )
            count = sum(path.is_dir() for path in candidates if is_local_path(path))
            package_root_raw = self.environment.get("LOCALAPPDATA")
            if package_root_raw:
                package_root = Path(package_root_raw) / "Packages"
                if is_local_path(package_root):
                    try:
                        with os.scandir(package_root) as scan:
                            entries = tuple(islice(scan, 512))
                        count += sum(
                            entry.is_dir(follow_symlinks=False)
                            and (
                                "chatgpt" in entry.name.casefold()
                                or "openai" in entry.name.casefold()
                            )
                            for entry in entries
                        )
                    except OSError:
                        pass
            cache_directories, cache_bytes, truncated = _cache_metadata(candidates)
            return AppState(
                count > 0,
                running,
                count,
                None,
                cache_directories,
                cache_bytes,
                truncated,
            )
        if app == "codex":
            running = any(Path(name).stem.casefold() == "codex" for name in processes)
            profile = self.environment.get("USERPROFILE")
            root = Path(profile) / ".codex" if profile else None
            exists = bool(root and is_local_path(root) and root.is_dir())
            config = root / "config.toml" if root else None
            readable = (
                bool(config and config.is_file() and os.access(config, os.R_OK)) if exists else None
            )
            return AppState(exists, running, int(exists), readable)
        running = any(Path(name).stem.casefold() in ("wt", "windowsterminal") for name in processes)
        local_app_data = self.environment.get("LOCALAPPDATA")
        executable = (
            Path(local_app_data) / "Microsoft" / "WindowsApps" / "wt.exe"
            if local_app_data
            else None
        )
        installed = bool(executable and is_local_path(executable) and executable.is_file())
        return AppState(installed, running)
