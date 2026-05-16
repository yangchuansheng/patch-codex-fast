---
name: patch-codex-fast
description: Patch Codex App to enable Fast/Speed mode and Plugins in API key mode, or optionally enable Zed as an SSH-capable remote open target. Supports macOS and Windows with backup, rollback, and bundle pattern discovery.
---

# Patch Codex Fast

Use this skill when the user wants to enable Codex desktop Fast/Speed mode or Plugins while running Codex with an API key instead of ChatGPT OAuth login. Also use it when the user asks whether Codex remote SSH sessions can open files in Zed, or asks to patch Codex so remote files can be opened with Zed.

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

For the Zed remote-open patch only:

1. Run `doctor` or `zed-remote-status`.
2. If the environment is valid, run `patch-zed-remote`.
3. Read the full output and report whether the Zed target was marked `supportsSsh` and whether the remote URL helper was inserted.
4. Tell the user to completely quit and reopen Codex, then verify that a remote Codex file shows Zed under Open With and opens in Zed Remote Development.
5. If Codex fails to launch or the user reports a broken state, run rollback immediately.

## Commands

Prefer the cross-platform Python entrypoint:

```bash
python3 scripts/patch_codex_fast.py doctor
python3 scripts/patch_codex_fast.py patch
python3 scripts/patch_codex_fast.py patch-zed-remote
python3 scripts/patch_codex_fast.py zed-remote-status
python3 scripts/patch_codex_fast.py rollback
```

On Windows, use `python` if `python3` is unavailable:

```powershell
python .\scripts\patch_codex_fast.py doctor
python .\scripts\patch_codex_fast.py patch
python .\scripts\patch_codex_fast.py patch-zed-remote
python .\scripts\patch_codex_fast.py zed-remote-status
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

The rollback script must restore `app.asar` before deleting `app/`, then restore the stock Electron fuses and re-sign on macOS. If macOS blocks writing inside `/Applications/Codex.app` with `Operation not permitted`, stop before deleting `app/`; grant App Management access or move the app bundle aside, copy it back, restore `app.asar`, and re-sign.

## Bundle update handling

When Codex updates, bundle hashes and minified variable names may change. First re-run the skill normally. If the script reports `No patches were applied`, inspect the extracted `app/webview/assets` directory with these searches:

```bash
grep -rl "authMethod" *.js | xargs grep -l "fast_mode"
grep -rl "pluginsDisabledTooltip" *.js
# Gate exported from gradient-*.js. Two known variants live in the wild:
#   older builds: function e(e){return e===`apikey`}
#   newer builds: function e(e){return e!==`chatgpt`}
# Both should be rewritten to `return false`.
grep -rlE 'return [A-Za-z_$]+(===|!==)`(apikey|chatgpt)`' *.js | grep -v locale
grep -rl "connector-unavailable" *.js | grep plugin
```

Patch the same logical gates described in the README if automated patterns no longer match. Also preserve Chrome by checking these app-bundle surfaces:

```bash
grep -rl "chrome-internal" app/.vite/build
grep -rl "externalBrowserUseAllowed" app/.vite/build
grep -rl "isExternalBrowserUseAvailable" app/webview/assets
```

The current fix maps the Dev runtime Chrome plugin name from `chrome-internal` to `chrome`, keeps the Chrome marketplace descriptor from being dropped by the external-browser feature gate, and prevents the renderer plugin list from hiding Chrome when `isExternalBrowserUseAvailable` is false.

For Zed remote-open support, inspect the main process open-target bundle:

```bash
grep -rl "id:\`zed\`" app/.vite/build
grep -rl "supportsSsh" app/.vite/build
grep -rl "vscode-remote://" app/.vite/build
```

The Zed patch keeps local Zed behavior unchanged, marks Zed as SSH-capable for Codex remote sessions, and converts the remote path passed by Codex into a Zed Remote Development URL such as `ssh://user@host[:port]/path`. Prefer Codex’s structured SSH config fields over the display alias so Zed does not fall back to the wrong local macOS username.

## Success criteria

The task is not complete until the agent has command evidence for the patch or rollback path and has told the user exactly what to verify in the Codex UI, including the Google Chrome row under Computer Use for the Fast/Plugins patch or the remote Open With → Zed flow for the Zed remote patch.
