"""Codex app filesystem operations."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .patterns import FUSE_FLAGS


@dataclass
class AppPaths:
    """Resolved Codex app paths for the current operating system."""

    resources_dir: Path
    fuse_app_path: Path

    @property
    def asar_path(self) -> Path:
        return self.resources_dir / "app.asar"

    @property
    def renamed_asar_path(self) -> Path:
        return self.resources_dir / "app.asar1"

    @property
    def backup_asar_path(self) -> Path:
        return self.resources_dir / "app.asar.bak"

    @property
    def extracted_app_dir(self) -> Path:
        return self.resources_dir / "app"

    @property
    def assets_dir(self) -> Path:
        return self.extracted_app_dir / "webview" / "assets"

    @property
    def plugins_dir(self) -> Path:
        return self.resources_dir / "plugins"


def detect_paths(resources_dir: str | None, fuse_app_path: str | None) -> AppPaths:
    """Resolve default Codex paths for macOS or Windows."""

    system = platform.system()
    if system == "Darwin":
        default_resources = Path("/Applications/Codex.app/Contents/Resources")
        default_fuse_app = Path("/Applications/Codex.app")
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data and resources_dir is None:
            raise SystemExit("LOCALAPPDATA is not set. Pass --resources-dir explicitly.")
        base = Path(local_app_data or "")
        default_resources = base / "Programs" / "Codex" / "resources"
        default_fuse_app = base / "Programs" / "Codex" / "Codex.exe"
    else:
        raise SystemExit(f"Unsupported platform: {system}. Use macOS or Windows.")

    return AppPaths(
        resources_dir=Path(resources_dir) if resources_dir else default_resources,
        fuse_app_path=Path(fuse_app_path) if fuse_app_path else default_fuse_app,
    )


def run(command: list[str], *, cwd: Path | None = None) -> None:
    """Run a subprocess and fail on non-zero exit."""

    print(f"[RUN] {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def ensure_prerequisites(paths: AppPaths) -> None:
    missing = [tool for tool in ("npx",) if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"Missing required tool(s): {', '.join(missing)}")
    if not paths.resources_dir.exists():
        raise SystemExit(f"Resources directory not found: {paths.resources_dir}")
    if not paths.asar_path.exists() and not paths.renamed_asar_path.exists():
        raise SystemExit(f"Neither app.asar nor app.asar1 exists in {paths.resources_dir}")


def stop_codex() -> None:
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["pkill", "-x", "Codex"], check=False)
    elif system == "Windows":
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Stop-Process -Name Codex -Force -ErrorAction SilentlyContinue"],
            check=False,
        )


def backup_asar(paths: AppPaths) -> None:
    if paths.backup_asar_path.exists():
        print(f"[OK] Backup already exists: {paths.backup_asar_path}")
        return
    if not paths.asar_path.exists():
        raise SystemExit(f"Cannot create backup because app.asar is missing: {paths.asar_path}")
    shutil.copy2(paths.asar_path, paths.backup_asar_path)
    print(f"[OK] Backed up app.asar -> {paths.backup_asar_path}")


def prepare_extracted_app(paths: AppPaths) -> None:
    if paths.extracted_app_dir.exists():
        shutil.rmtree(paths.extracted_app_dir)
        print(f"[OK] Removed previous extracted app directory: {paths.extracted_app_dir}")
    if not paths.asar_path.exists() and paths.renamed_asar_path.exists():
        shutil.copy2(paths.renamed_asar_path, paths.asar_path)
        print("[OK] Restored app.asar from app.asar1 for re-patching")

    run(["npx", "@electron/asar", "e", str(paths.asar_path), "app"], cwd=paths.resources_dir)
    paths.asar_path.rename(paths.renamed_asar_path)
    print("[OK] Renamed app.asar -> app.asar1 so Electron can load app/")


def disable_fuses(paths: AppPaths) -> None:
    for flag in FUSE_FLAGS:
        run(["npx", "@electron/fuses", "write", "--app", str(paths.fuse_app_path), flag])


def resign_if_needed(paths: AppPaths) -> None:
    if platform.system() == "Darwin":
        run(["codesign", "--force", "--deep", "--sign", "-", str(paths.fuse_app_path)])


def rollback_files(paths: AppPaths) -> None:
    if paths.extracted_app_dir.exists():
        shutil.rmtree(paths.extracted_app_dir)
        print(f"[OK] Removed extracted app directory: {paths.extracted_app_dir}")
    if paths.renamed_asar_path.exists():
        if paths.asar_path.exists():
            paths.asar_path.unlink()
        paths.renamed_asar_path.rename(paths.asar_path)
        print("[OK] Restored app.asar from app.asar1")
    if paths.backup_asar_path.exists():
        shutil.copy2(paths.backup_asar_path, paths.asar_path)
        print("[OK] Restored app.asar from app.asar.bak")


def print_doctor(paths: AppPaths) -> None:
    print(f"Platform: {platform.system()}")
    print(f"Resources: {paths.resources_dir}")
    print(f"Fuse app: {paths.fuse_app_path}")
    print(f"app.asar: {'yes' if paths.asar_path.exists() else 'no'}")
    print(f"app.asar1: {'yes' if paths.renamed_asar_path.exists() else 'no'}")
    print(f"app.asar.bak: {'yes' if paths.backup_asar_path.exists() else 'no'}")
    print(f"extracted app/: {'yes' if paths.extracted_app_dir.exists() else 'no'}")
    print(f"plugins/: {'yes' if paths.plugins_dir.exists() else 'no'}")
    print(f"openai-bundled marketplace: {'yes' if (paths.plugins_dir / 'openai-bundled').exists() else 'no'}")
    python_tool = shutil.which("python3") or shutil.which("python")
    for tool in ("npx", "codesign"):
        if tool == "codesign" and platform.system() != "Darwin":
            continue
        print(f"{tool}: {shutil.which(tool) or 'missing'}")
    print(f"python: {python_tool or 'missing'}")
