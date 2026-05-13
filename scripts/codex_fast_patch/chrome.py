"""Chrome plugin preservation patches for Codex bundled plugins."""

from __future__ import annotations

import re
from pathlib import Path

from .app import AppPaths


class ChromePatchReporter:
    """Minimal reporting protocol used by Chrome preservation patches."""

    def add_file(self) -> None: ...

    def add_patch(self, message: str) -> None: ...

    def warn(self, message: str) -> None: ...


EXTERNAL_BROWSER_FILTER_RE = re.compile(
    r"function (?P<fn>[A-Za-z_$][\w$]*)"
    r"\(e,\{isComputerUseAvailable:t,"
    r"isExternalBrowserUseAvailable:n,"
    r"isInAppBrowserUseAvailable:r\}\)"
    r"\{return!\(!r&&(?P<inapp>[A-Za-z_$][\w$]*)\(e\)"
    r"\|\|!n&&(?P<external>[A-Za-z_$][\w$]*)\(e\)"
    r"\|\|!t&&(?P<computer>[A-Za-z_$][\w$]*)\(e\)\)\}"
)

CHROME_MARKETPLACE_DESCRIPTOR_RE = re.compile(
    r"(\{forceReload:!0,name:[^,]+,"
    r"isAvailable:\(\{buildFlavor:e,features:t\}\)=>)"
    r"(?P<gate>[A-Za-z_$][\w$]*)\(e\)&&t\.externalBrowserUseAllowed\}"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def replace_first(content: str, old: str, new: str) -> tuple[str, bool]:
    if old not in content:
        return content, False
    return content.replace(old, new, 1), True


def patch_chrome_plugin_preservation(paths: AppPaths, report: ChromePatchReporter) -> None:
    """Keep the Google Chrome plugin visible after the Dev marketplace rebuilds."""

    if not chrome_patch_surfaces_exist(paths):
        return

    patched_name = patch_chrome_runtime_plugin_name(paths, report)
    patched_descriptor = patch_chrome_marketplace_descriptor(paths, report)
    patched_visibility = patch_chrome_visibility_filter(paths, report)

    if not patched_name:
        report.warn("Chrome runtime plugin-name gate not found; inspect app-session bundle if Chrome disappears.")
    if not patched_descriptor:
        report.warn("Chrome marketplace descriptor not found; inspect main bundle if Chrome is removed on restart.")
    if not patched_visibility:
        report.warn("Chrome visibility filter not found; inspect use-plugins bundle if Chrome is hidden.")


def chrome_patch_surfaces_exist(paths: AppPaths) -> bool:
    build_dir = paths.extracted_app_dir / ".vite" / "build"
    return build_dir.exists() or any(paths.assets_dir.glob("use-plugins-*.js"))


def patch_chrome_runtime_plugin_name(paths: AppPaths, report: ChromePatchReporter) -> bool:
    build_dir = paths.extracted_app_dir / ".vite" / "build"
    if not build_dir.exists():
        report.warn(f"Build directory not found: {build_dir}")
        return False

    for path in sorted(build_dir.glob("*.js")):
        content = read_text(path)
        if not is_chrome_runtime_constants_bundle(content):
            continue

        content, changed = replace_first(content, "`chrome-internal`", "`chrome`")
        if changed:
            write_text(path, content)
            report.add_file()
            report.add_patch(f"{path.name}: chrome-internal plugin name -> chrome")
            return True

        if "`chrome`" in content and "`chrome-internal`" not in content:
            return True

    return False


def patch_chrome_marketplace_descriptor(paths: AppPaths, report: ChromePatchReporter) -> bool:
    build_dir = paths.extracted_app_dir / ".vite" / "build"
    if not build_dir.exists():
        return False

    for path in sorted(build_dir.glob("*.js")):
        content = read_text(path)
        if "externalBrowserUseAllowed" not in content or "forceReload:!0" not in content:
            continue

        content, changed = remove_external_browser_gate_from_descriptor(content)
        if changed:
            write_text(path, content)
            report.add_file()
            report.add_patch(f"{path.name}: Chrome marketplace descriptor kept for Dev builds")
            return True

        if chrome_marketplace_descriptor_already_patched(content):
            return True

    return False


def chrome_marketplace_descriptor_already_patched(content: str) -> bool:
    return "name:e.On" in content and "=>Jn(e)}" in content


def remove_external_browser_gate_from_descriptor(content: str) -> tuple[str, bool]:
    def replacement(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group('gate')}(e)}}"

    content, count = CHROME_MARKETPLACE_DESCRIPTOR_RE.subn(replacement, content, count=1)
    return content, count > 0


def is_chrome_runtime_constants_bundle(content: str) -> bool:
    return (
        "openai-bundled-dev" in content
        and ("`chrome-internal`" in content or "`chrome`" in content)
        and "`computer-use`" in content
        and "`latex-tectonic`" in content
    )


def patch_chrome_visibility_filter(paths: AppPaths, report: ChromePatchReporter) -> bool:
    for path in chrome_visibility_candidate_files(paths):
        content = read_text(path)
        content, changed = remove_external_browser_gate_from_chrome_filter(content)
        if changed:
            write_text(path, content)
            report.add_file()
            report.add_patch(f"{path.name}: Chrome plugin no longer hidden by external browser gate")
            return True
        if "isExternalBrowserUseAvailable" in content and "`chrome`" in content and "!n&&" not in content:
            return True
    return False


def chrome_visibility_candidate_files(paths: AppPaths) -> list[Path]:
    files = sorted(paths.assets_dir.glob("use-plugins-*.js"))
    if files:
        return files
    return [
        path
        for path in sorted(paths.assets_dir.glob("*.js"))
        if "isExternalBrowserUseAvailable" in read_text(path) and "`chrome`" in read_text(path)
    ]


def remove_external_browser_gate_from_chrome_filter(content: str) -> tuple[str, bool]:
    def replacement(match: re.Match[str]) -> str:
        return (
            f"function {match.group('fn')}"
            "(e,{isComputerUseAvailable:t,isExternalBrowserUseAvailable:n,isInAppBrowserUseAvailable:r})"
            f"{{return!(!r&&{match.group('inapp')}(e)||!t&&{match.group('computer')}(e))}}"
        )

    content, count = EXTERNAL_BROWSER_FILTER_RE.subn(replacement, content, count=1)
    return content, count > 0
