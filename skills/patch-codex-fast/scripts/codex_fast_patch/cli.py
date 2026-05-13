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
    stop_codex,
)
from .bundle import patch_js


def patch_app(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    ensure_prerequisites(paths)
    if not args.no_stop:
        stop_codex()
    backup_asar(paths)
    prepare_extracted_app(paths)
    report = patch_js(paths)
    disable_fuses(paths)
    resign_if_needed(paths)

    print("")
    print("=== Patch complete ===")
    print(f"Patched files: {report.patched_files}")
    print(f"Patch actions: {report.patch_actions}")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")
    print("Completely quit and reopen Codex, then verify Fast mode, Plugins, and the Google Chrome row in Computer Use.")


def rollback_app(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    if not args.no_stop:
        stop_codex()
    rollback_files(paths)
    resign_if_needed(paths)
    print("=== Rollback complete ===")


def doctor(args: argparse.Namespace) -> None:
    paths = detect_paths(args.resources_dir, args.app_path)
    print_doctor(paths)


def add_common_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--resources-dir", help="Override Codex resources directory.")
    sub.add_argument("--app-path", help="Override app path passed to @electron/fuses/codesign.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Patch Codex desktop Fast mode and Plugins for API key mode.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    patch_parser = subparsers.add_parser("patch")
    add_common_args(patch_parser)
    patch_parser.add_argument("--no-stop", action="store_true", help="Do not stop the running Codex app first.")
    patch_parser.set_defaults(handler=patch_app)

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
