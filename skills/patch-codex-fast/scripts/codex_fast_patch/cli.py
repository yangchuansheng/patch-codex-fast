"""CLI for patch-codex-fast."""

from __future__ import annotations

import argparse

from .app import (
    backup_asar,
    detect_paths,
    disable_fuses,
    ensure_prerequisites,
    prepare_extracted_app,
    print_doctor,
    resign_if_needed,
    rollback_files,
    restore_stock_fuses,
    stop_codex,
)
from .bundle import patch_js
from .zed_remote import detect_zed_remote_status


def rollback_after_failed_patch(paths) -> None:
    """Best-effort restore when a patch fails after app.asar was moved aside."""

    try:
        rollback_files(paths)
    except BaseException as rollback_error:
        print("")
        print("=== Automatic rollback failed ===")
        print(rollback_error)
        print("Run doctor and restore app.asar manually before reopening Codex.")
        return
    try:
        restore_stock_fuses(paths)
        resign_if_needed(paths)
    except BaseException as cleanup_error:
        print("")
        print("=== Automatic rollback fuse/sign cleanup failed ===")
        print(cleanup_error)
        print("Run rollback manually after fixing filesystem permissions.")
        return
    print("")
    print("=== Automatic rollback complete after failed patch ===")


def patch_app(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    ensure_prerequisites(paths)
    if not args.no_stop:
        stop_codex()
    backup_asar(paths)
    prepare_extracted_app(paths)
    try:
        report = patch_js(paths, include_fast_plugins=True, include_zed_remote=args.zed_remote)
        disable_fuses(paths)
        resign_if_needed(paths)
    except BaseException:
        rollback_after_failed_patch(paths)
        raise

    print("")
    print("=== Patch complete ===")
    print(f"Patched files: {report.patched_files}")
    print(f"Patch actions: {report.patch_actions}")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")
    print("Completely quit and reopen Codex, then verify Fast mode, Plugins, and the Google Chrome row in Computer Use.")
    if args.zed_remote:
        print("Also verify that a remote Codex file shows Zed under Open With and opens through Zed Remote Development.")


def rollback_app(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    if not args.no_stop:
        stop_codex()
    rollback_files(paths)
    restore_stock_fuses(paths)
    resign_if_needed(paths)
    print("=== Rollback complete ===")


def doctor(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    print_doctor(paths)
    if paths.extracted_app_dir.exists():
        print_zed_remote_status(paths)


def patch_zed_remote_app(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    ensure_prerequisites(paths)
    if not args.no_stop:
        stop_codex()
    backup_asar(paths)
    prepare_extracted_app(paths)
    try:
        report = patch_js(paths, include_fast_plugins=False, include_zed_remote=True)
        disable_fuses(paths)
        resign_if_needed(paths)
    except BaseException:
        rollback_after_failed_patch(paths)
        raise

    print("")
    print("=== Zed remote patch complete ===")
    print(f"Patched files: {report.patched_files}")
    print(f"Patch actions: {report.patch_actions}")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")
    print_zed_remote_status(paths)
    print("Completely quit and reopen Codex, then verify that remote files offer Zed under Open With.")


def zed_remote_status(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    print_zed_remote_status(paths)


def print_zed_remote_status(paths) -> None:
    status = detect_zed_remote_status(paths)
    print("")
    print("=== Zed remote status ===")
    print(f"bundle: {status.bundle_path or 'not found'}")
    print(f"Zed target found: {'yes' if status.zed_target_found else 'no'}")
    print(f"supports SSH: {'yes' if status.supports_ssh else 'no'}")
    print(f"remote URL helper: {'yes' if status.remote_helper_found else 'no'}")
    print(f"Zed app found: {'yes' if status.zed_app_found else 'no'}")
    print(f"`zed` on PATH: {'yes' if status.zed_cli_found else 'no'}")
    print(f"patched: {'yes' if status.patched else 'no'}")


def add_common_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--resources-dir", help="Override Codex resources directory.")
    sub.add_argument("--app-path", help="Override app path passed to @electron/fuses/codesign.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Patch Codex desktop Fast mode and Plugins for API key mode.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    patch_parser = subparsers.add_parser("patch")
    add_common_args(patch_parser)
    patch_parser.add_argument("--no-stop", action="store_true", help="Do not stop the running Codex app first.")
    patch_parser.add_argument(
        "--zed-remote",
        action="store_true",
        help="Also patch Codex remote sessions so Zed appears as an SSH-capable open target.",
    )
    patch_parser.set_defaults(handler=patch_app)

    zed_remote_parser = subparsers.add_parser("patch-zed-remote")
    add_common_args(zed_remote_parser)
    zed_remote_parser.add_argument("--no-stop", action="store_true", help="Do not stop the running Codex app first.")
    zed_remote_parser.set_defaults(handler=patch_zed_remote_app)

    zed_status_parser = subparsers.add_parser("zed-remote-status")
    add_common_args(zed_status_parser)
    zed_status_parser.set_defaults(handler=zed_remote_status)

    rollback_parser = subparsers.add_parser("rollback")
    add_common_args(rollback_parser)
    rollback_parser.add_argument("--no-stop", action="store_true", help="Do not stop the running Codex app first.")
    rollback_parser.set_defaults(handler=rollback_app)

    doctor_parser = subparsers.add_parser("doctor")
    add_common_args(doctor_parser)
    doctor_parser.set_defaults(handler=doctor)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)
