"""Patch minified JavaScript gates inside the extracted Codex bundle."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .app import AppPaths
from .chrome import patch_chrome_plugin_preservation
from .patterns import (
    APIKEY_GATE_PATTERNS,
    CONNECTOR_PATTERNS,
    FAST_AUTH_PATTERNS,
    FAST_HOOK_AUTH_PATTERNS,
    FAST_MODELS_PATTERNS,
)
from .zed_remote import patch_zed_remote_open


SIDEBAR_GATE_RE = re.compile(r"([A-Z])\?\(0,\$\.jsx\)\(Sl,\{tooltipContent")

# Fallback regex for the gradient-*.js gate. Matches either the old
# "API key" phrasing or the current "not chatgpt" phrasing, regardless of
# what identifier names the minifier has picked.
APIKEY_GATE_FALLBACK_RE = re.compile(
    r"function\s+([A-Za-z_$])\(\1\)\{return\s+\1(?:===|!==)`(?:apikey|chatgpt)`\}"
)


@dataclass
class PatchReport:
    """Counts and warnings collected while patching bundled JavaScript files."""

    patched_files: int = 0
    patch_actions: int = 0
    warnings: list[str] | None = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []

    def add_patch(self, message: str) -> None:
        self.patch_actions += 1
        print(f"[PATCHED] {message}")

    def add_file(self) -> None:
        self.patched_files += 1

    def warn(self, message: str) -> None:
        assert self.warnings is not None
        self.warnings.append(message)
        print(f"[WARN] {message}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def replace_first(content: str, old: str, new: str) -> tuple[str, bool]:
    if old not in content:
        return content, False
    return content.replace(old, new, 1), True


def patch_fast_mode(paths: AppPaths, report: PatchReport) -> None:
    files = sorted(paths.assets_dir.glob("permissions-mode-helpers-*.js"))
    for path in files:
        content = read_text(path)
        original = content

        content = patch_fast_auth(path, content, report)
        content = patch_fast_hook(path, content, report)
        content = patch_fast_models(path, content, report)

        if content != original:
            write_text(path, content)
            report.add_file()

    if not files:
        report.warn("permissions-mode-helpers-*.js not found; searching all assets")
        find_likely_fast_file(paths, report)


def patch_fast_auth(path: Path, content: str, report: PatchReport) -> str:
    for pattern in FAST_AUTH_PATTERNS:
        content, changed = replace_first(content, pattern, "return true")
        if changed:
            report.add_patch(f"{path.name}: fast auth check -> return true")
            return content

    if "authMethod" in content and "fast_mode" in content:
        report.warn(f"{path.name}: fast auth pattern changed; inspect manually")
    return content


def patch_fast_hook(path: Path, content: str, report: PatchReport) -> str:
    for old, new in FAST_HOOK_AUTH_PATTERNS:
        content, changed = replace_first(content, old, new)
        if changed:
            report.add_patch(f"{path.name}: fast hook auth early return disabled")
            return content
    return content


def patch_fast_models(path: Path, content: str, report: PatchReport) -> str:
    for old, new in FAST_MODELS_PATTERNS:
        content, changed = replace_first(content, old, new)
        if changed:
            report.add_patch(f"{path.name}: model fast-tier check -> true")
            return content

    if "modelsByType.models.some" in content or ".models.some(" in content:
        report.warn(f"{path.name}: fast model pattern changed; inspect manually")
    return content


def find_likely_fast_file(paths: AppPaths, report: PatchReport) -> None:
    for path in sorted(paths.assets_dir.glob("*.js")):
        content = read_text(path)
        if "authMethod" in content and "fast_mode" in content:
            report.warn(f"Likely fast-mode bundle: {path.name}")
            return


def patch_plugin_sidebar(paths: AppPaths, report: PatchReport) -> None:
    for path in sorted(paths.assets_dir.glob("index-*.js")):
        content = read_text(path)
        original = content
        marker = "pluginsDisabledTooltip"

        if marker in content:
            idx = content.find(marker)
            window = content[max(0, idx - 240) : idx + 120]
            match = SIDEBAR_GATE_RE.search(window)
            if match:
                content = replace_sidebar_gate(path, content, match.group(1), report)
            else:
                report.warn(f"{path.name}: plugins sidebar gate pattern changed")

        if content != original:
            write_text(path, content)
            report.add_file()


def replace_sidebar_gate(path: Path, content: str, gate: str, report: PatchReport) -> str:
    old = f"{gate}?(0,$.jsx)(Sl,{{tooltipContent"
    new = "0?(0,$.jsx)(Sl,{tooltipContent"
    content, changed = replace_first(content, old, new)
    if changed:
        report.add_patch(f"{path.name}: plugins sidebar gate {gate}? -> 0?")
    return content


def patch_apikey_gate(paths: AppPaths, report: PatchReport) -> None:
    files = sorted(paths.assets_dir.glob("gradient-*.js"))
    for path in files:
        content = read_text(path)
        original = content

        for pattern in APIKEY_GATE_PATTERNS:
            content, changed = replace_first(content, pattern, "function e(e){return false}")
            if changed:
                report.add_patch(f"{path.name}: apikey gate -> return false")
                break
        else:
            match = APIKEY_GATE_FALLBACK_RE.search(content)
            if match:
                ident = match.group(1)
                replacement = f"function {ident}({ident}){{return false}}"
                content = content[: match.start()] + replacement + content[match.end() :]
                report.add_patch(
                    f"{path.name}: apikey gate (regex fallback) -> return false"
                )
            elif "apikey" in content or "chatgpt" in content:
                report.warn(
                    f"{path.name}: known gate patterns not found; inspect manually"
                )

        if content != original:
            write_text(path, content)
            report.add_file()

    if not files:
        report.warn("gradient-*.js not found; search for return e===`apikey` or return e!==`chatgpt` manually")


def patch_connector_gate(paths: AppPaths, report: PatchReport) -> None:
    for path in sorted(paths.assets_dir.glob("use-plugin-install-flow-*.js")):
        content = read_text(path)
        original = content

        for old, new in CONNECTOR_PATTERNS:
            if old in content and f"false&&{old}" not in content:
                idx = content.find(old)
                if "false&&" not in content[max(0, idx - 20) : idx]:
                    content = content.replace(old, new, 1)
                    report.add_patch(f"{path.name}: connector unavailable gate disabled")
                    break

        if content != original:
            write_text(path, content)
            report.add_file()


def patch_js(paths: AppPaths, *, include_fast_plugins: bool = True, include_zed_remote: bool = False) -> PatchReport:
    if not paths.assets_dir.exists():
        raise SystemExit(f"Assets directory not found after extraction: {paths.assets_dir}")

    report = PatchReport()
    if include_fast_plugins:
        patch_fast_mode(paths, report)
        patch_plugin_sidebar(paths, report)
        patch_apikey_gate(paths, report)
        patch_connector_gate(paths, report)
        patch_chrome_plugin_preservation(paths, report)
    if include_zed_remote:
        patch_zed_remote_open(paths, report)

    if report.patch_actions == 0:
        raise SystemExit(
            "No patches were applied. Codex bundle patterns likely changed. "
            "See README troubleshooting commands."
        )
    return report
