# patch-codex-fast

[![skills.sh](https://skills.sh/b/yangchuansheng/patch-codex-fast)](https://skills.sh/yangchuansheng/patch-codex-fast)

A Codex skill that patches the local Codex desktop app so **Fast/Speed mode** and **Plugins** are available when Codex is signed in with an **API key** instead of ChatGPT OAuth.

The main artifact is the skill. You install this repository as a Codex skill, then ask Codex to run `patch-codex-fast`. Codex should handle the doctor check, patch execution, verification, and rollback guidance for you.

> [!WARNING]
> This is an unofficial local patch. It modifies your installed Codex desktop app and disables selected Electron integrity fuses so the unpacked app can load. Use it only on machines where you accept that tradeoff.

## What this skill does

When invoked, the skill guides Codex to:

1. Check the local Codex app path and required tools.
2. Back up the original `app.asar`.
3. Extract and patch the local Codex desktop bundle.
4. Re-sign the app on macOS.
5. Ask you to verify Fast/Speed mode and Plugins in API key mode.
6. Roll back immediately if Codex fails to launch.

You do not need to copy the long patch commands manually. The scripts under `scripts/` are implementation assets used by the skill.

## Install as a Codex skill

Recommended install through `npx skills`:

```bash
npx skills add yangchuansheng/patch-codex-fast -g -a codex -y
```

This installs the repository as a global Codex skill. You can inspect the available skill before installing:

```bash
npx skills add yangchuansheng/patch-codex-fast --list
```

For the interactive cross-agent installer, run:

```bash
npx skills add yangchuansheng/patch-codex-fast
```

Manual install is still possible if you do not want to use `npx skills`:

```bash
git clone https://github.com/yangchuansheng/patch-codex-fast.git
mkdir -p ~/.codex/skills
ln -s "$(pwd)/patch-codex-fast" ~/.codex/skills/patch-codex-fast
```

Confirm the skill file exists:

```bash
ls ~/.codex/skills/patch-codex-fast/SKILL.md
```

## Use the skill

In Codex, invoke the skill directly:

```text
[$patch-codex-fast] Patch my local Codex app so Fast mode and Plugins work in API key mode.
```

Or describe the goal naturally:

```text
Use patch-codex-fast to enable Fast mode and Plugins for my API-key Codex desktop setup.
```

The skill will run the appropriate local script for your OS. It should not ask you to perform the patch steps manually unless your environment blocks execution or the Codex bundle changed enough that manual inspection is required.

## Expected Codex flow

The skill is designed for this workflow:

1. Run `doctor` to inspect environment and app paths.
2. Run `patch` for the current OS.
3. Report the patch result and any warnings.
4. Ask you to open Codex and verify the UI.
5. Run `rollback` if launch or verification fails.

Because this modifies an installed desktop application, Codex may warn before executing commands that stop Codex or write under the app installation directory.

## Requirements

- Codex desktop app installed.
- Node.js with `npx`.
- Python 3.
- macOS: `codesign` from Xcode Command Line Tools.
- Windows: PowerShell.

The patch uses `npx @electron/asar` and `npx @electron/fuses`. `npx` may download those packages on first run.

## Repository layout

```text
.
├── SKILL.md                 # Root skill entrypoint for npx skills
├── README.md                # Skill-first usage and reference
├── LICENSE
├── SECURITY.md
├── skills/patch-codex-fast/ # Mirrored skill entrypoint for skills.sh detail pages
├── scripts/                 # Skill implementation assets
│   ├── patch_codex_fast.py  # Cross-platform CLI
│   ├── codex_fast_patch/    # Python modules
│   ├── macos-patch.sh
│   ├── macos-rollback.sh
│   ├── windows-patch.ps1
│   └── windows-rollback.ps1
└── tests/
    └── test_patch_logic.py
```

## skills.sh listing

This repository is compatible with `npx skills` because it keeps a root `SKILL.md` for CLI discovery and mirrors the same entrypoint at `skills/patch-codex-fast/SKILL.md` for skills.sh detail-page rendering. It can be installed directly from GitHub:

```bash
npx skills add yangchuansheng/patch-codex-fast -g -a codex -y
```

The skills.sh page is expected at <https://skills.sh/yangchuansheng/patch-codex-fast/patch-codex-fast>. If the page or its SKILL.md preview does not update immediately, verify installation with the CLI and allow time for directory indexing or usage statistics to update.

## Direct script usage

Direct script usage is mainly for debugging or for environments where you are not using Codex skills.

### macOS

```bash
python3 scripts/patch_codex_fast.py doctor
python3 scripts/patch_codex_fast.py patch
```

Rollback:

```bash
python3 scripts/patch_codex_fast.py rollback
```

### Windows

```powershell
python .\scripts\patch_codex_fast.py doctor
python .\scripts\patch_codex_fast.py patch
```

Rollback:

```powershell
python .\scripts\patch_codex_fast.py rollback
```

### Options

| Option | Applies to | Purpose |
| --- | --- | --- |
| `--resources-dir` | all commands | Override the Codex resources directory. |
| `--app-path` | all commands | Override the path passed to `@electron/fuses` and macOS `codesign`. |
| `--no-stop` | `patch`, `rollback` | Do not stop the running Codex app before changing files. |

## Default app paths

| OS | Resources directory | App path |
| --- | --- | --- |
| macOS | `/Applications/Codex.app/Contents/Resources` | `/Applications/Codex.app` |
| Windows | `%LOCALAPPDATA%\Programs\Codex\resources` | `%LOCALAPPDATA%\Programs\Codex\Codex.exe` |

If Codex is installed somewhere else, pass both paths through the skill request or direct CLI options.

## What the patch changes

The patch changes local desktop bundle gates that currently depend on `authMethod=chatgpt`:

| Area | Local change | Purpose |
| --- | --- | --- |
| Fast auth gate | Return `true` for the fast availability check. | Allow API key mode to see Fast/Speed mode. |
| Fast hook early return | Disable the auth-only early return. | Prevent `canUseFastMode:false` before model checks. |
| Fast model check | Replace speed-tier model availability check with `true`. | Support relay `/v1/models` responses without `additionalSpeedTiers`. |
| Plugins sidebar | Change the disabled ternary gate from `X?` to `0?`. | Keep the Plugins sidebar enabled. |
| API key detector | Force API key plugin gate to return `false`. | Stop plugin code from treating API key mode as unsupported. |
| Connector gate | Prefix connector-unavailable assignment with `false&&`. | Stop every connector from being marked unavailable. |

It also changes Electron fuses required for the unpacked modified app to load:

| Fuse | Why |
| --- | --- |
| `OnlyLoadAppFromAsar=off` | Allows Electron to load `app/` instead of only `app.asar`. |
| `EnableEmbeddedAsarIntegrityValidation=off` | Avoids integrity failure after local modification. |
| `GrantFileProtocolExtraPrivileges=off` | Keeps the modified unpacked bundle loadable in current Codex builds. |
| `EnableCookieEncryption=off` | Avoids a local runtime check that can block the patched app. |

## When Codex updates

Codex updates can change bundle hashes and minified variable names. Re-run the skill first. If it reports that no patches were applied, the skill should inspect the extracted bundle and look for these targets:

```bash
grep -rl "authMethod" *.js | xargs grep -l "fast_mode"
grep -rl "pluginsDisabledTooltip" *.js
grep -rl 'return e===.apikey.' *.js | grep -v locale
grep -rl "connector-unavailable" *.js | grep plugin
```

The same logical gates should be patched even if filenames or minified variables changed.

## Manual rollback

Use the skill rollback first:

```text
[$patch-codex-fast] Roll back the Codex desktop patch.
```

If you must recover manually, close Codex and run the commands for your OS.

### macOS

```bash
cd /Applications/Codex.app/Contents/Resources
rm -rf app
[ -f app.asar1 ] && mv app.asar1 app.asar
[ -f app.asar.bak ] && cp app.asar.bak app.asar
codesign --force --deep --sign - /Applications/Codex.app
```

### Windows

```powershell
cd "$env:LOCALAPPDATA\Programs\Codex\resources"
Remove-Item -Recurse -Force app -ErrorAction SilentlyContinue
if (Test-Path app.asar1) { Rename-Item app.asar1 app.asar }
if (Test-Path app.asar.bak) { Copy-Item app.asar.bak app.asar }
```

## Troubleshooting

### Skill is not detected

Confirm that Codex can read the root skill file:

```bash
ls ~/.codex/skills/patch-codex-fast/SKILL.md
```

The skill entrypoint is the repository root `SKILL.md`, not a nested file.

### Patch reports `No patches were applied`

The installed Codex version likely changed the bundle patterns. Ask Codex to use this skill to inspect the extracted assets and update the target patterns.

Do not paste API keys, cookies, tokens, or proprietary bundle chunks into public issues.

### Codex does not launch after patching

Ask the skill to roll back immediately:

```text
[$patch-codex-fast] Roll back now. Codex does not launch after the patch.
```

On macOS, also verify that the `codesign` step completed.

## Security note

This repository is for local experimentation and workflow recovery. It is not affiliated with OpenAI or the Codex desktop app. Review the scripts before running them and keep rollback available.

## License

MIT. See `LICENSE`.
