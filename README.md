# Patch Codex Fast

Patch the Codex desktop app so **Fast/Speed mode** and **Plugins** remain available when you sign in with an **API key** instead of ChatGPT OAuth.

This project turns the original `patch-codex-fast` Codex skill into a small open-source utility with:

- macOS and Windows support.
- Automatic backup before patching.
- One-command rollback.
- Bundle pattern discovery when Codex updates.
- A reusable Codex skill file in `skill/SKILL.md`.

> [!WARNING]
> This is an unofficial local patch. It modifies your installed Codex desktop app and disables selected Electron integrity fuses so the unpacked app can load. Use it only on machines where you accept that tradeoff.

## What it enables

Codex desktop currently gates several UI paths behind `authMethod=chatgpt`. If you use API key mode, these features can be hidden or disabled even when the underlying model endpoint works.

This patch changes the local desktop bundle so API key mode can access:

1. Fast/Speed mode.
2. The Plugins sidebar.
3. Plugin installation flow and connector availability checks.

## What it changes

The script:

1. Stops Codex if it is running.
2. Backs up `app.asar` to `app.asar.bak`.
3. Extracts `app.asar` into `app/`.
4. Renames `app.asar` to `app.asar1` so Electron loads the unpacked `app/` directory.
5. Patches selected minified JavaScript gates under `app/webview/assets`.
6. Disables Electron fuses needed to load the modified unpacked app.
7. Re-signs the app on macOS.

Rollback removes `app/`, restores `app.asar`, and re-signs on macOS.

## Requirements

- Codex desktop app installed.
- Node.js with `npx`.
- Python 3.
- macOS: `codesign` from Xcode Command Line Tools.
- Windows: PowerShell.

The patch uses `npx @electron/asar` and `npx @electron/fuses`. `npx` may download those packages the first time it runs.

## Quick start

Clone the repo:

```bash
git clone https://github.com/yangchuansheng/patch-codex-fast.git
cd patch-codex-fast
```

Run a doctor check first:

```bash
python3 scripts/patch_codex_fast.py doctor
```

Patch Codex:

```bash
python3 scripts/patch_codex_fast.py patch
```

Open Codex and verify:

- Fast/Speed mode is visible while using API key mode.
- The Plugins sidebar is visible.
- Plugin install flow does not mark every connector unavailable.

## macOS

Default app paths:

- Resources: `/Applications/Codex.app/Contents/Resources`
- App path for fuses and signing: `/Applications/Codex.app`

Run:

```bash
python3 scripts/patch_codex_fast.py doctor
python3 scripts/patch_codex_fast.py patch
```

Or use the wrapper:

```bash
./scripts/macos-patch.sh
```

Rollback:

```bash
python3 scripts/patch_codex_fast.py rollback
```

Or:

```bash
./scripts/macos-rollback.sh
```

If your Codex app is installed somewhere else:

```bash
python3 scripts/patch_codex_fast.py patch \
  --resources-dir "/Applications/Codex.app/Contents/Resources" \
  --app-path "/Applications/Codex.app"
```

## Windows

Default app paths:

- Resources: `%LOCALAPPDATA%\Programs\Codex\resources`
- App path for fuses: `%LOCALAPPDATA%\Programs\Codex\Codex.exe`

Run from PowerShell:

```powershell
python .\scripts\patch_codex_fast.py doctor
python .\scripts\patch_codex_fast.py patch
```

Or use the wrapper:

```powershell
.\scripts\windows-patch.ps1
```

Rollback:

```powershell
python .\scripts\patch_codex_fast.py rollback
```

Or:

```powershell
.\scripts\windows-rollback.ps1
```

If Codex is installed somewhere else:

```powershell
python .\scripts\patch_codex_fast.py patch `
  --resources-dir "$env:LOCALAPPDATA\Programs\Codex\resources" `
  --app-path "$env:LOCALAPPDATA\Programs\Codex\Codex.exe"
```

## Commands

```bash
python3 scripts/patch_codex_fast.py doctor
python3 scripts/patch_codex_fast.py patch
python3 scripts/patch_codex_fast.py rollback
```

Options:

| Option | Applies to | Purpose |
| --- | --- | --- |
| `--resources-dir` | all commands | Override the Codex resources directory. |
| `--app-path` | all commands | Override the path passed to `@electron/fuses` and macOS `codesign`. |
| `--no-stop` | `patch`, `rollback` | Do not stop the running Codex app before changing files. |

## Manual rollback

Use the scripted rollback first. If you need to recover manually, close Codex and run the commands for your OS.

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

## How it works

| Change | Reason | Location |
| --- | --- | --- |
| `OnlyLoadAppFromAsar=off` | Allows Electron to load the unpacked `app/` directory. | Electron fuse |
| `EnableEmbeddedAsarIntegrityValidation=off` | Avoids embedded asar integrity validation after local modification. | Electron fuse |
| `GrantFileProtocolExtraPrivileges=off` | Keeps the modified unpacked bundle loadable in current Codex builds. | Electron fuse |
| `EnableCookieEncryption=off` | Avoids a local runtime check that can block the patched app. | Electron fuse |
| `app.asar` → `app.asar1` | Makes Electron fall back to the extracted `app/` directory. | Resources directory |
| Fast auth gate → `return true` | Removes the `authMethod=chatgpt` requirement for Fast mode. | `permissions-mode-helpers-*.js` |
| Fast hook early return → `if(false){` | Prevents API key mode from returning `canUseFastMode:false` before model checks. | `permissions-mode-helpers-*.js` |
| Fast model check → `true` | Works around relay `/v1/models` responses that do not include `additionalSpeedTiers`. | `permissions-mode-helpers-*.js` |
| Plugin sidebar gate `X?` → `0?` | Keeps the Plugins sidebar enabled in API key mode. | `index-*.js` |
| API key detector → `return false` | Prevents plugin code from treating API key mode as unsupported. | `gradient-*.js` |
| Connector unavailable assignment → `false&&(...)` | Stops connector availability from marking every connector unavailable in API key mode. | `use-plugin-install-flow-*.js` |

## When Codex updates

Codex updates usually change hashed filenames and may change minified variable names. Re-run:

```bash
python3 scripts/patch_codex_fast.py patch
```

If no patches are applied, inspect the extracted assets:

```bash
cd /Applications/Codex.app/Contents/Resources/app/webview/assets
```

On Windows, use:

```powershell
cd "$env:LOCALAPPDATA\Programs\Codex\resources\app\webview\assets"
```

Then search for the new targets.

### Fast mode gate

```bash
grep -rl "authMethod" *.js | xargs grep -l "fast_mode"
grep -o ".{0,50}authMethod.{0,100}fast_mode.{0,80}" <target_file>
grep -o ".{0,50}authMethod.{0,80}canUseFastMode.{0,80}" <target_file>
```

Patch the top-level fast availability return to `return true`. If there is an auth-only early return that sets `canUseFastMode:false`, change that condition to `if(false){`.

### Fast model check

```bash
grep -o ".{0,30}\\.models.some(.{0,50}" <target_file>
```

Replace the model fast-tier availability expression with `true`.

### Plugins sidebar gate

```bash
grep -rl "pluginsDisabledTooltip" *.js
grep -o ".{0,80}pluginsDisabledTooltip" <target_file>
```

Find the single-letter ternary gate before the disabled tooltip and change `X?(...)` to `0?(...)`.

### API key plugin gate

```bash
grep -rl 'return e===.apikey.' *.js | grep -v locale
grep -o 'function e(e){return e===.apikey.}' <target_file>
```

Change it to:

```js
function e(e){return false}
```

### Connector availability gate

```bash
grep -rl "connector-unavailable" *.js | grep plugin
grep -o '.{0,10}connector-unavailable.{0,10}' <target_file>
```

Prefix the connector-unavailable assignment with `false&&`, for example:

```js
false&&(i=`connector-unavailable`)
```

## Troubleshooting

### `No patches were applied`

The Codex bundle probably changed. Run the manual target discovery commands above and open an issue with:

- Codex version.
- Operating system.
- The bundle filenames found by the grep commands.
- Redacted patch output.

Do not paste API keys, cookies, tokens, or proprietary bundle chunks.

### Codex does not launch after patching

Run rollback:

```bash
python3 scripts/patch_codex_fast.py rollback
```

On macOS, make sure `codesign` exists and the final signing step completed.

### `npx` asks to install packages

Allow it if you trust npm on your machine. The script uses `@electron/asar` and `@electron/fuses`.

### Permission denied on macOS

Your user may not have permission to modify `/Applications/Codex.app`. Run the command from an administrator shell, or install Codex in a user-writable location and pass `--resources-dir` plus `--app-path`.

## Repository layout

```text
.
├── README.md
├── LICENSE
├── SECURITY.md
├── scripts/
│   ├── patch_codex_fast.py
│   ├── codex_fast_patch/
│   ├── macos-patch.sh
│   ├── macos-rollback.sh
│   ├── windows-patch.ps1
│   └── windows-rollback.ps1
└── skill/
    └── SKILL.md
```

## Skill usage

The original Codex skill is included at `skill/SKILL.md`. To install it as a local Codex skill, copy or symlink the folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/skill" ~/.codex/skills/patch-codex-fast
```

Then invoke it as `patch-codex-fast` in Codex.

## Responsible use

This repository is for local experimentation and workflow recovery. It is not affiliated with OpenAI or the Codex desktop app. Review the script before running it, keep backups, and re-run rollback if anything looks wrong.

## License

MIT. See `LICENSE`.
