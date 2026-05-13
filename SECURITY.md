# Security

This project modifies a locally installed desktop application. Treat it as a development and experimentation tool, not as a hardening tool.

## What the patch changes

The patch extracts `app.asar`, changes selected minified JavaScript gates, and disables selected Electron fuses so the unpacked app can load.

Those fuse changes reduce integrity checks for the local Codex app installation. Do not use this project on machines where that violates your organization policy.

## Reporting issues

Please open a GitHub issue for:

- Patch patterns that no longer match a new Codex version.
- Rollback failures.
- Unexpected writes outside the Codex resources directory.
- Documentation that could lead to unsafe use.

Do not include API keys, tokens, cookies, logs with secrets, or copied proprietary bundle contents in public issues.
