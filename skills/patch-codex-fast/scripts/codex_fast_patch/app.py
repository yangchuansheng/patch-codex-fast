"""Codex app filesystem operations."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .patterns import FUSE_FLAGS, STOCK_FUSE_FLAGS


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
    backup_source = paths.asar_path if paths.asar_path.exists() else paths.renamed_asar_path
    if not backup_source.exists():
        raise SystemExit(
            "Cannot create backup because neither app.asar nor app.asar1 exists: "
            f"{paths.resources_dir}"
        )
    shutil.copy2(backup_source, paths.backup_asar_path)
    print(f"[OK] Backed up app.asar -> {paths.backup_asar_path}")


def prepare_extracted_app(paths: AppPaths) -> None:
    work_dir = paths.resources_dir / "app.patch-work"
    if work_dir.exists():
        shutil.rmtree(work_dir)
        print(f"[OK] Removed previous patch work directory: {work_dir}")
    if not paths.asar_path.exists() and paths.renamed_asar_path.exists():
        shutil.copy2(paths.renamed_asar_path, paths.asar_path)
        print("[OK] Restored app.asar from app.asar1 for re-patching")

    run(["npx", "@electron/asar", "e", str(paths.asar_path), work_dir.name], cwd=paths.resources_dir)
    if paths.extracted_app_dir.exists():
        shutil.rmtree(paths.extracted_app_dir)
        print(f"[OK] Removed previous extracted app directory: {paths.extracted_app_dir}")
    work_dir.rename(paths.extracted_app_dir)
    paths.asar_path.replace(paths.renamed_asar_path)
    print("[OK] Renamed app.asar -> app.asar1 so Electron can load app/")


def disable_fuses(paths: AppPaths) -> None:
    for flag in FUSE_FLAGS:
        run(["npx", "@electron/fuses", "write", "--app", str(paths.fuse_app_path), flag])


def restore_stock_fuses(paths: AppPaths) -> None:
    for flag in STOCK_FUSE_FLAGS:
        run(["npx", "@electron/fuses", "write", "--app", str(paths.fuse_app_path), flag])


def resign_if_needed(paths: AppPaths) -> None:
    if platform.system() == "Darwin":
        run(["codesign", "--force", "--deep", "--sign", "-", str(paths.fuse_app_path)])


def restore_asar(paths: AppPaths) -> None:
    """Restore app.asar before deleting app/ so rollback cannot leave Codex unlaunchable."""

    if paths.backup_asar_path.exists():
        try:
            shutil.copy2(paths.backup_asar_path, paths.asar_path)
        except PermissionError as exc:
            raise SystemExit(build_restore_permission_error(paths, exc)) from exc
        print("[OK] Restored app.asar from app.asar.bak")
        return

    if paths.renamed_asar_path.exists():
        try:
            shutil.copy2(paths.renamed_asar_path, paths.asar_path)
        except PermissionError as exc:
            raise SystemExit(build_restore_permission_error(paths, exc)) from exc
        print("[OK] Restored app.asar from app.asar1")
        return

    if paths.asar_path.exists():
        print(f"[OK] app.asar already exists: {paths.asar_path}")
        return

    raise SystemExit(
        "Cannot rollback safely: app.asar is missing and no app.asar.bak/app.asar1 backup was found. "
        f"Resources: {paths.resources_dir}"
    )


def build_restore_permission_error(paths: AppPaths, exc: PermissionError) -> str:
    return (
        "macOS blocked writing app.asar inside the Codex.app bundle. "
        "Rollback stopped before deleting app/, so the current extracted app remains available. "
        "Grant Terminal/Python App Management access, or move /Applications/Codex.app aside, copy it back, "
        "then copy app.asar.bak to app.asar and re-sign. "
        f"Resources: {paths.resources_dir}. Original error: {exc}"
    )


def rollback_files(paths: AppPaths) -> None:
    restore_asar(paths)
    if paths.extracted_app_dir.exists():
        shutil.rmtree(paths.extracted_app_dir)
        print(f"[OK] Removed extracted app directory: {paths.extracted_app_dir}")


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
