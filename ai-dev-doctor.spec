# PyInstaller onedir bundle: no runtime extraction or elevation.
from pathlib import Path
import tomllib
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct)

root = Path(SPECPATH)
version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
version_numbers = tuple(int(part) for part in version.split(".")[:3]) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_numbers, prodvers=version_numbers, mask=0x3f,
                     flags=2 if "dev" in version else 0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable("040904B0", [
        StringStruct("FileDescription", "Windows AI Dev Doctor"),
        StringStruct("FileVersion", version), StringStruct("ProductVersion", version),
        StringStruct("ProductName", "Windows AI Dev Doctor"),
        StringStruct("OriginalFilename", "ai-dev-doctor.exe"),
    ])]), VarFileInfo([VarStruct("Translation", [1033, 1200])])],
)
a = Analysis(
    [str(root / "packaging" / "entry.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "LICENSE"), ".")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "ruff", "mypy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="ai-dev-doctor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    uac_admin=False,
    version=version_info,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ai-dev-doctor")
