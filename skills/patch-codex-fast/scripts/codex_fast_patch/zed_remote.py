"""Zed remote-open patch for Codex desktop."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .app import AppPaths


IDENT = r"[A-Za-z_$][\w$]*"

ZED_TARGET_RE = re.compile(
    r"(?P<prefix>id:`zed`,platforms:\{darwin:\{label:`Zed`,"
    r"icon:`apps/zed\.png`,kind:`editor`,)"
    r"(?P<supports>supportsSsh:!0,)?"
    rf"detect:(?P<detect>{IDENT}),args:(?P<args>{IDENT}),"
    rf"open:async\(\{{command:(?P<command>{IDENT}),path:(?P<path>{IDENT}),"
    rf"location:(?P<location>{IDENT})\}}\)=>\{{await (?P<open_fn>{IDENT})"
    r"\((?P=command),(?P=path),(?P=location)\)\}"
)

HOST_ALIAS_FN_RE = re.compile(
    rf"function (?P<host_fn>{IDENT})\(e\)"
    rf"\{{if\(e\.kind===`ssh`\)\{{let t={IDENT}\(e\);if\(t\)return t\}}"
    rf"return e\.name\?\.trim\(\)\|\|{IDENT}\(e\.id\)\}}"
)

REMOTE_HELPER_NAME = "zedRemotePathForCodexPatch"


class ZedPatchReporter:
    """Minimal reporting protocol used by the Zed remote patch."""

    def add_file(self) -> None: ...

    def add_patch(self, message: str) -> None: ...

    def warn(self, message: str) -> None: ...


@dataclass
class ZedRemoteStatus:
    """Read-only status for the Zed remote-open patch surface."""

    bundle_path: Path | None
    zed_target_found: bool
    supports_ssh: bool
    remote_helper_found: bool
    zed_app_found: bool
    zed_cli_found: bool

    @property
    def patched(self) -> bool:
        return self.zed_target_found and self.supports_ssh and self.remote_helper_found


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def detect_zed_remote_status(paths: AppPaths) -> ZedRemoteStatus:
    """Inspect whether the extracted bundle already supports Zed remote open."""

    bundle_path = find_zed_bundle(paths)
    content = read_text(bundle_path) if bundle_path else ""
    return ZedRemoteStatus(
        bundle_path=bundle_path,
        zed_target_found=bool(bundle_path),
        supports_ssh=has_zed_supports_ssh(content),
        remote_helper_found=REMOTE_HELPER_NAME in content and "zedSshConfigForCodexPatch" in content,
        zed_app_found=find_zed_app_path() is not None,
        zed_cli_found=shutil.which("zed") is not None,
    )


def patch_zed_remote_open(paths: AppPaths, report: ZedPatchReporter) -> ZedRemoteStatus:
    """Patch the main process open-target bundle so Zed appears for SSH remotes."""

    bundle_path = find_zed_bundle(paths)
    if bundle_path is None:
        report.warn("Zed open target was not found in app/.vite/build; inspect main bundle manually.")
        return detect_zed_remote_status(paths)

    content = read_text(bundle_path)
    original = content
    content = patch_zed_open_function(bundle_path, content, report)
    content = patch_zed_target(bundle_path, content, report)

    if content != original:
        write_text(bundle_path, content)
        report.add_file()

    status = detect_zed_remote_status(paths)
    if not status.patched:
        report.warn(f"{bundle_path.name}: Zed remote patch is incomplete; inspect bundle manually.")
    if status.patched and not status.zed_cli_found:
        report.warn(
            "Zed app was found, but `zed` is not on PATH; "
            "line/column remote opens may fall back to file-only opens."
        )
    return status


def find_zed_bundle(paths: AppPaths) -> Path | None:
    build_dir = paths.extracted_app_dir / ".vite" / "build"
    if not build_dir.exists():
        return None
    for path in sorted(build_dir.glob("*.js")):
        content = read_text(path)
        if (
            "id:`zed`" in content
            and "label:`Zed`" in content
            and (
                "function cC" in content
                or "vscode-remote://" in content
                or "Remote control does not support VS Code remote open yet." in content
            )
        ):
            return path
    return None


def has_zed_supports_ssh(content: str) -> bool:
    match = zed_target_window(content)
    return bool(match and "supportsSsh:!0" in match)


def zed_target_window(content: str) -> str | None:
    start = content.find("id:`zed`")
    if start < 0:
        return None
    end = content.find("function iT", start)
    if end < 0:
        end = content.find("var lT=", start)
    return content[start:end if end > start else start + 1200]


def patch_zed_target(path: Path, content: str, report: ZedPatchReporter) -> str:
    if REMOTE_HELPER_NAME in content and has_zed_supports_ssh(content):
        return content

    match = ZED_TARGET_RE.search(content)
    if match is None:
        if "id:`zed`" in content and "label:`Zed`" in content:
            report.warn(f"{path.name}: Zed target pattern changed; cannot mark supportsSsh.")
        return content

    replacement = (
        f"{match.group('prefix')}supportsSsh:!0,"
        f"detect:{match.group('detect')},args:{match.group('args')},"
        "open:async({"
        f"command:{match.group('command')},path:{match.group('path')},"
        f"location:{match.group('location')},"
        "hostConfig:zedHostConfig,remoteWorkspaceRoot:zedRemoteRoot,remotePath:zedRemotePath"
        "})=>{await "
        f"{match.group('open_fn')}("
        f"{match.group('command')},{match.group('path')},{match.group('location')},"
        "zedHostConfig,zedRemoteRoot,zedRemotePath)}"
    )
    report.add_patch(f"{path.name}: Zed target marked as SSH-capable")
    return content[: match.start()] + replacement + content[match.end() :]


def patch_zed_open_function(path: Path, content: str, report: ZedPatchReporter) -> str:
    if REMOTE_HELPER_NAME in content:
        return content

    target = ZED_TARGET_RE.search(content)
    open_fn = target.group("open_fn") if target else find_zed_open_function_name(content)
    host_alias_fn = find_host_alias_function_name(content)
    if open_fn is None or host_alias_fn is None:
        report.warn(f"{path.name}: cannot locate Zed open function or SSH alias helper.")
        return content

    pattern = build_open_function_re(open_fn)
    match = pattern.search(content)
    if match is None:
        report.warn(f"{path.name}: Zed open function pattern changed; cannot add remote URL builder.")
        return content

    replacement = build_open_function_replacement(match, host_alias_fn)
    report.add_patch(f"{path.name}: Zed remote paths now open through ssh:// URLs")
    return content[: match.start()] + replacement + content[match.end() :]


def find_zed_open_function_name(content: str) -> str | None:
    match = ZED_TARGET_RE.search(content)
    return match.group("open_fn") if match else None


def find_host_alias_function_name(content: str) -> str | None:
    match = HOST_ALIAS_FN_RE.search(content)
    return match.group("host_fn") if match else None


def build_open_function_re(open_fn: str) -> re.Pattern[str]:
    return re.compile(
        rf"async function {re.escape(open_fn)}"
        rf"\((?P<command>{IDENT}),(?P<path>{IDENT}),(?P<location>{IDENT})\)"
        rf"\{{let (?P<args>{IDENT})=(?P<args_fn>{IDENT})"
        r"\((?P=path),(?P=location)\),"
        rf"(?P<app>{IDENT})=(?P<app_from_command>{IDENT})"
        rf"\((?P=command)\)\?\?(?P<app_fallback>{IDENT})\(\);"
        rf"if\((?P=app)\)\{{if\(await (?P<run>{IDENT})"
        r"\(`open`,\[`-a`,(?P=app),(?P=path)\]\),!(?P=location)\)return;"
        rf"let (?P<zed_cli>{IDENT})=(?P<which>{IDENT})\(`zed`\);"
        r"if\((?P=zed_cli)\)try\{await (?P=run)\((?P=zed_cli),(?P=args)\)\}"
        r"catch\{\}return\}await (?P=run)\((?P=command),(?P=args)\)\}"
    )


def build_open_function_replacement(match: re.Match[str], host_alias_fn: str) -> str:
    signature_match = re.match(r"async function (?P<name>[A-Za-z_$][\w$]*)", match.group(0))
    if signature_match is None:
        raise ValueError("Could not parse Zed open function name.")
    open_fn = signature_match.group("name")
    command = match.group("command")
    path = match.group("path")
    location = match.group("location")
    args = match.group("args")
    args_fn = match.group("args_fn")
    app = match.group("app")
    app_from_command = match.group("app_from_command")
    app_fallback = match.group("app_fallback")
    run = match.group("run")
    zed_cli = match.group("zed_cli")
    which = match.group("which")

    return (
        f"async function {open_fn}({command},{path},{location},"
        "zedHostConfig,zedRemoteRoot,zedRemotePath){"
        "let zedTarget="
        f"{REMOTE_HELPER_NAME}(zedHostConfig,zedRemotePath??zedRemoteRoot)??{path},"
        f"{args}={args_fn}(zedTarget,{location}),"
        f"{app}={app_from_command}({command})??{app_fallback}();"
        f"if({app}){{if(await {run}(`open`,[`-a`,{app},zedTarget]),!{location})return;"
        f"let {zed_cli}={which}(`zed`);"
        f"if({zed_cli})try{{await {run}({zed_cli},{args})}}catch{{}}return}}"
        f"await {run}({command},{args})}}"
        f"function {REMOTE_HELPER_NAME}(e,t){{"
        "if(e==null||t==null)return null;"
        "if(e.kind===`remote-control`)throw Error(`Remote control does not support Zed remote open yet.`);"
        "let n=t.trim();if(!n)return null;"
        f"let r={host_alias_fn}(e),i=n.startsWith(`/`)?n:`/${{n}}`;"
        "let a=zedSshConfigForCodexPatch(e,r);"
        "if(a)return`ssh://${a}${i.split(`/`).map(encodeURIComponent).join(`/`)}`;"
        "return`ssh://${r}${i.split(`/`).map(encodeURIComponent).join(`/`)}`}"
        "function zedSshConfigForCodexPatch(e,t){"
        "let n=e?.ssh_config??e?.sshConfig??e?.config??null;"
        "if(n&&typeof n==`object`){"
        "let r=typeof n.user==`string`?n.user.trim():typeof n.username==`string`?n.username.trim():``,"
        "i=typeof n.host==`string`?n.host.trim():typeof n.hostname==`string`?n.hostname.trim():typeof n.hostName==`string`?n.hostName.trim():``,"
        "a=Number.isInteger(n.port)?`:${n.port}`:typeof n.port==`string`&&n.port.trim()?`:${n.port.trim()}`:``;"
        "if(i)return`${r?`${r}@`:``}${i}${a}`;}"
        "let r=typeof e?.user==`string`?e.user.trim():typeof e?.username==`string`?e.username.trim():``,"
        "i=typeof e?.host==`string`?e.host.trim():typeof e?.hostname==`string`?e.hostname.trim():typeof e?.hostName==`string`?e.hostName.trim():``;"
        "return i?`${r?`${r}@`:``}${i}`:t;}"
    )


def find_zed_app_path() -> Path | None:
    candidates = [
        Path("/Applications/Zed.app"),
        Path("/Applications/Zed Preview.app"),
        Path("/Applications/Zed Nightly.app"),
        Path.home() / "Applications" / "Zed.app",
        Path.home() / "Applications" / "Zed Preview.app",
        Path.home() / "Applications" / "Zed Nightly.app",
    ]
    return next((path for path in candidates if path.exists()), None)
