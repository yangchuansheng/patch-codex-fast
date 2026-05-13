---
name: patch-codex-fast
description: Patch Codex App to enable Fast/Speed mode and Plugins when using API key mode. Supports macOS and Windows with backup, rollback, and bundle pattern discovery.
---

# Patch Codex Fast

Use this skill when the user wants to enable Codex desktop Fast/Speed mode or Plugins while running Codex with an API key instead of ChatGPT OAuth login.

This skill is the main interface after installation through `npx skills` or a manual symlink. Do not make the user copy long shell snippets from the README. Use the scripts in this repository as execution assets, run the right command for the current OS, then report the result and verification steps.

This is an unofficial local patch. Before changing the app, make sure the user understands that it modifies the installed Codex desktop bundle, disables selected Electron integrity fuses, and may need to be re-applied after Codex updates.

## Intent

The user should be able to say:

```text
[$patch-codex-fast] Patch my local Codex app so Fast mode and Plugins work in API key mode.
```

Then the agent should execute the workflow end to end, not respond with a manual recipe. The script commands below are for the agent to run, not for the user to copy as the primary path.

## Workflow

1. Identify the repository root that contains this `SKILL.md`.
2. Run a doctor check with the repository script.
3. If the environment is valid, run the patch script for the current OS.
4. Read the full command output and report:
   - whether patch actions were applied,
   - any warnings,
   - the exact rollback command.
5. Ask the user to completely quit and reopen Codex, then verify:
   - Fast/Speed mode is visible in API key mode,
   - the Plugins sidebar is visible in API key mode,
   - plugin install flow no longer marks all connectors unavailable,
   - Computer Use settings still show the Google Chrome plugin row.
6. If Codex fails to launch or the user reports a broken state, run rollback immediately.

## Commands

Prefer the cross-platform Python entrypoint:

```bash
python3 scripts/patch_codex_fast.py doctor
python3 scripts/patch_codex_fast.py patch
python3 scripts/patch_codex_fast.py rollback
```

On Windows, use `python` if `python3` is unavailable:

```powershell
python .\scripts\patch_codex_fast.py doctor
python .\scripts\patch_codex_fast.py patch
python .\scripts\patch_codex_fast.py rollback
```

Wrappers are also available:

```bash
./scripts/macos-patch.sh
./scripts/macos-rollback.sh
```

```powershell
.\scripts\windows-patch.ps1
.\scripts\windows-rollback.ps1
```

## Default paths

macOS:

- Resources: `/Applications/Codex.app/Contents/Resources`
- App path: `/Applications/Codex.app`

Windows:

- Resources: `%LOCALAPPDATA%\Programs\Codex\resources`
- App path: `%LOCALAPPDATA%\Programs\Codex\Codex.exe`

If Codex is installed somewhere else, pass `--resources-dir` and `--app-path` to the Python command.

## Rollback policy

Rollback is part of the skill, not an afterthought. If patching fails after files were changed, or if the app does not launch, run:

```bash
python3 scripts/patch_codex_fast.py rollback
```

On Windows:

```powershell
python .\scripts\patch_codex_fast.py rollback
```

## Bundle update handling

When Codex updates, bundle hashes and minified variable names may change. First re-run the skill normally. If the script reports `No patches were applied`, inspect the extracted `app/webview/assets` directory with these searches:

```bash
grep -rl "authMethod" *.js | xargs grep -l "fast_mode"
grep -rl "pluginsDisabledTooltip" *.js
grep -rl 'return e===.apikey.' *.js | grep -v locale
grep -rl "connector-unavailable" *.js | grep plugin
```

Patch the same logical gates described in the README if automated patterns no longer match. Also preserve Chrome by checking these app-bundle surfaces:

```bash
grep -rl "chrome-internal" app/.vite/build
grep -rl "externalBrowserUseAllowed" app/.vite/build
grep -rl "isExternalBrowserUseAvailable" app/webview/assets
```

The current fix maps the Dev runtime Chrome plugin name from `chrome-internal` to `chrome`, keeps the Chrome marketplace descriptor from being dropped by the external-browser feature gate, and prevents the renderer plugin list from hiding Chrome when `isExternalBrowserUseAvailable` is false.

## Success criteria

The task is not complete until the agent has command evidence for the patch or rollback path and has told the user exactly what to verify in the Codex UI, including the Google Chrome row under Computer Use.
