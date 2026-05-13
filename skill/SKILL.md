---
name: patch-codex-fast
description: Patch Codex App to enable Fast/Speed mode and Plugins when using API key mode. Supports macOS and Windows with backup, rollback, and bundle pattern discovery.
---

# Patch Codex Fast

Use this skill when the user wants to enable Codex desktop Fast/Speed mode or Plugins while running Codex with an API key instead of ChatGPT OAuth login.

This is an unofficial local patch. Before changing the app, make sure the user understands that it modifies the installed Codex desktop bundle, disables selected Electron integrity fuses, and may need to be re-applied after Codex updates.

## Workflow

1. Read the repository README first.
2. Run a doctor check.
3. Run the patch script for the current OS.
4. Open Codex and verify:
   - Fast/Speed mode is visible in API key mode.
   - The Plugins sidebar is visible in API key mode.
   - Plugin install flow no longer marks all connectors unavailable.
5. If Codex fails to launch, run rollback immediately.

## macOS

```bash
python3 scripts/patch_codex_fast.py doctor
python3 scripts/patch_codex_fast.py patch
```

Rollback:

```bash
python3 scripts/patch_codex_fast.py rollback
```

## Windows

```powershell
python .\scripts\patch_codex_fast.py doctor
python .\scripts\patch_codex_fast.py patch
```

Rollback:

```powershell
python .\scripts\patch_codex_fast.py rollback
```

## Manual target discovery

When Codex updates, bundle hashes and minified variable names may change. Search under the extracted `app/webview/assets` directory:

```bash
grep -rl "authMethod" *.js | xargs grep -l "fast_mode"
grep -rl "pluginsDisabledTooltip" *.js
grep -rl 'return e===.apikey.' *.js | grep -v locale
grep -rl "connector-unavailable" *.js | grep plugin
```

Patch the same logical gates described in the README if the automated patterns no longer match.
