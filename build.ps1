param(
    [string]$Version,
    [ValidateSet("zip", "tar.gz", "all")]
    [string]$Format = "zip"
)

$ErrorActionPreference = "Stop"

$packageScript = Join-Path $PSScriptRoot "scripts\package.ps1"
if (-not (Test-Path -LiteralPath $packageScript)) {
    throw "Package script not found: $packageScript"
}

& $packageScript -Version $Version -Format $Format
