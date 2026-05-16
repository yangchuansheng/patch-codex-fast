# patch-codex-fast skill package

This directory is the installable `patch-codex-fast` skill package. It is the canonical package discovered by `npx skills` and rendered by skills.sh.

> [!WARNING]
> This skill applies an unofficial local patch to the Codex desktop app. It modifies the installed app bundle and disables selected Electron integrity fuses so the unpacked app can load.

## Use

After installation, invoke the skill in Codex:

```text
[$patch-codex-fast] Patch my local Codex app so Fast mode and Plugins work in API key mode.
```

The agent should run the doctor check, execute the patch script for the current OS, report command evidence, and give rollback guidance. The user should not need to copy the patch commands manually.

## Agent execution assets

Preferred Python entrypoint:

```bash
python3 scripts/patch_codex_fast.py doctor
python3 scripts/patch_codex_fast.py patch
python3 scripts/patch_codex_fast.py patch-zed-remote
python3 scripts/patch_codex_fast.py zed-remote-status
python3 scripts/patch_codex_fast.py rollback
```

Rollback restores `app.asar` before deleting the extracted `app/` directory, then restores stock Electron fuses and re-signs on macOS. If macOS blocks bundle writes, keep `app/` in place until `app.asar` has been restored.

Windows fallback:

```powershell
python .\scripts\patch_codex_fast.py doctor
python .\scripts\patch_codex_fast.py patch
python .\scripts\patch_codex_fast.py patch-zed-remote
python .\scripts\patch_codex_fast.py zed-remote-status
python .\scripts\patch_codex_fast.py rollback
```

Shell wrappers are also included:

```bash
./scripts/macos-patch.sh
./scripts/macos-rollback.sh
```

```powershell
.\scripts\windows-patch.ps1
.\scripts\windows-rollback.ps1
```

## Success criteria

The task is complete only when the agent has command evidence for the patch or rollback path and has told the user to verify these Codex UI states:

- Fast/Speed mode is visible in API key mode.
- The Plugins sidebar is visible in API key mode.
- Plugin install flow no longer marks every connector unavailable.
- Computer Use settings still show the Google Chrome plugin row after Codex restarts.

For the optional Zed remote-open patch, the task is complete only when the agent has command evidence that `patch-zed-remote` ran or rolled back, and has told the user to verify that a remote Codex file shows Zed under Open With and opens in Zed Remote Development.

See the repository README for the full implementation notes and troubleshooting guide: <https://github.com/yangchuansheng/patch-codex-fast>.
