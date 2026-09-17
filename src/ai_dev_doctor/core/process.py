"""Owned process trees; Windows jobs are assigned atomically at process creation."""

import ctypes
import os
import signal
import subprocess
import sys
from collections.abc import Mapping
from contextlib import ExitStack, suppress
from ctypes import wintypes
from typing import IO, Any, Protocol


class Process(Protocol):
    @property
    def stdout(self) -> IO[bytes]: ...
    @property
    def stderr(self) -> IO[bytes]: ...
    @property
    def returncode(self) -> int | None: ...

    def wait(self, timeout: float) -> int: ...
    def close(self) -> None: ...


class _IOCounters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_uint64)
        for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )
    ]


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IOCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [("StartupInfo", _StartupInfo), ("lpAttributeList", ctypes.c_void_p)]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class WindowsProcess:
    _kernel: Any
    _handle: int | None
    _job: int | None
    stdout: IO[bytes]
    stderr: IO[bytes]
    returncode: int | None

    def __init__(self, argv: tuple[str, ...], env: Mapping[str, str]) -> None:
        if sys.platform != "win32":
            raise OSError("Windows required")
        import msvcrt

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel = kernel
        # Every handle-sized parameter and return value must retain all 64 bits.
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD],
                wintypes.BOOL,
            ),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
            "InitializeProcThreadAttributeList": (
                [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)],
                wintypes.BOOL,
            ),
            "UpdateProcThreadAttribute": (
                [
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    ctypes.c_size_t,
                    ctypes.c_void_p,
                    ctypes.c_size_t,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                ],
                wintypes.BOOL,
            ),
            "DeleteProcThreadAttributeList": ([ctypes.c_void_p], None),
            "CreateProcessW": (
                [
                    wintypes.LPCWSTR,
                    wintypes.LPWSTR,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    wintypes.BOOL,
                    wintypes.DWORD,
                    ctypes.c_void_p,
                    wintypes.LPCWSTR,
                    ctypes.POINTER(_StartupInfoEx),
                    ctypes.POINTER(_ProcessInfo),
                ],
                wintypes.BOOL,
            ),
            "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            "GetExitCodeProcess": (
                [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)],
                wintypes.BOOL,
            ),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(kernel, name)
            function.argtypes = arguments
            function.restype = result
        self.returncode: int | None = None
        self._job = kernel.CreateJobObjectW(None, None)
        self._handle: int | None = None
        if not self._job:
            raise ctypes.WinError()
        try:
            limits = _ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE; no breakaway
            if not kernel.SetInformationJobObject(
                self._job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ):
                raise ctypes.WinError()
            with ExitStack() as stack:
                null = stack.enter_context(open(os.devnull, "rb"))
                out_read, out_write = os.pipe()
                stack.callback(os.close, out_write)
                stdout = stack.enter_context(os.fdopen(out_read, "rb", buffering=0))
                err_read, err_write = os.pipe()
                stack.callback(os.close, err_write)
                stderr = stack.enter_context(os.fdopen(err_read, "rb", buffering=0))
                handles = (wintypes.HANDLE * 3)(
                    *(msvcrt.get_osfhandle(fd) for fd in (null.fileno(), out_write, err_write))
                )
                for handle in handles:
                    assert handle is not None
                    os.set_handle_inheritable(handle, True)
                    stack.callback(os.set_handle_inheritable, handle, False)
                size = ctypes.c_size_t()
                kernel.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
                attributes = ctypes.create_string_buffer(size.value)
                if not kernel.InitializeProcThreadAttributeList(
                    attributes, 2, 0, ctypes.byref(size)
                ):
                    raise ctypes.WinError()
                stack.callback(kernel.DeleteProcThreadAttributeList, attributes)
                jobs = (wintypes.HANDLE * 1)(self._job)
                for attribute, values in ((0x20002, handles), (0x2000D, jobs)):
                    if not kernel.UpdateProcThreadAttribute(
                        attributes, 0, attribute, values, ctypes.sizeof(values), None, None
                    ):
                        raise ctypes.WinError()
                startup = _StartupInfoEx()
                startup.StartupInfo.cb = ctypes.sizeof(startup)
                startup.StartupInfo.dwFlags = 0x100  # STARTF_USESTDHANDLES
                (
                    startup.StartupInfo.hStdInput,
                    startup.StartupInfo.hStdOutput,
                    startup.StartupInfo.hStdError,
                ) = handles
                startup.lpAttributeList = ctypes.addressof(attributes)
                info = _ProcessInfo()
                environment = ctypes.create_unicode_buffer(
                    "\0".join(
                        f"{k}={v}" for k, v in sorted(env.items(), key=lambda item: item[0].upper())
                    )
                    + "\0\0"
                )
                command = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
                if not kernel.CreateProcessW(
                    argv[0],
                    command,
                    None,
                    None,
                    True,
                    0x08080400,  # NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT | UNICODE_ENVIRONMENT
                    environment,
                    None,
                    ctypes.byref(startup),
                    ctypes.byref(info),
                ):
                    raise ctypes.WinError()
                self._handle = info.hProcess
                kernel.CloseHandle(info.hThread)
                # Duplicate the parent read descriptors before the stack releases its copies.
                self.stdout = os.fdopen(os.dup(stdout.fileno()), "rb", buffering=0)
                self.stderr = os.fdopen(os.dup(stderr.fileno()), "rb", buffering=0)
        except BaseException:
            self.close()
            for name in ("stdout", "stderr"):
                stream = getattr(self, name, None)
                if stream is not None:
                    stream.close()
            raise

    def wait(self, timeout: float) -> int:
        result = self._kernel.WaitForSingleObject(self._handle, max(1, int(timeout * 1000)))
        if result == 258:
            raise subprocess.TimeoutExpired("reviewed probe", timeout)
        if result != 0:
            raise OSError("Process wait failed")
        code = wintypes.DWORD()
        if not self._kernel.GetExitCodeProcess(self._handle, ctypes.byref(code)):
            raise OSError("Process result unavailable")
        self.returncode = int(code.value)
        return self.returncode

    def close(self) -> None:
        if self._job:
            self._kernel.CloseHandle(self._job)
            self._job = None
        if self._handle:
            self._kernel.WaitForSingleObject(self._handle, 2000)
            self._kernel.CloseHandle(self._handle)
            self._handle = None


class PosixProcess:
    def __init__(self, argv: tuple[str, ...], env: Mapping[str, str]) -> None:
        self._proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            env=dict(env),
            start_new_session=True,
        )
        assert self._proc.stdout is not None and self._proc.stderr is not None
        self.stdout = self._proc.stdout
        self.stderr = self._proc.stderr

    @property
    def returncode(self) -> int | None:
        return self._proc.returncode

    def wait(self, timeout: float) -> int:
        return self._proc.wait(timeout=timeout)

    def close(self) -> None:
        if sys.platform != "win32":
            with suppress(ProcessLookupError):
                os.killpg(self._proc.pid, signal.SIGKILL)
        self._proc.wait(timeout=2)


def start_process(argv: tuple[str, ...], env: Mapping[str, str]) -> Process:
    return WindowsProcess(argv, env) if sys.platform == "win32" else PosixProcess(argv, env)
