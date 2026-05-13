$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Get-Command python3 -ErrorAction SilentlyContinue

if (-not $Python) {
    $Python = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $Python) {
    throw "Python 3 was not found. Install Python 3 and run this script again."
}

& $Python.Source "$ScriptDir\patch_codex_fast.py" rollback @args
