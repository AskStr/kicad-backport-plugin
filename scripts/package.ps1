param(
    [string]$Version
)

$ErrorActionPreference = "Stop"

$PluginRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistRoot = Join-Path $PluginRoot "dist"
$PackageRoot = Join-Path $DistRoot "kicad-backport"
$ArchivePath = Join-Path $DistRoot "kicad-backport.zip"

if (-not $Version) {
    $PluginJson = Get-Content -LiteralPath (Join-Path $PluginRoot "plugin.json") -Raw | ConvertFrom-Json
    $Version = [string]$PluginJson.version
}

Remove-Item -LiteralPath $DistRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null

$rootFiles = @("__init__.py", "plugin.json", "README.md", "requirements.txt")
foreach ($item in $rootFiles) {
    Copy-Item -LiteralPath (Join-Path $PluginRoot $item) -Destination $PackageRoot -Force
}

$rootDirs = @("assets", "legacy", "plugin", "docs")
foreach ($dir in $rootDirs) {
    Copy-Item -LiteralPath (Join-Path $PluginRoot $dir) -Destination $PackageRoot -Recurse -Force
}

Get-ChildItem -LiteralPath $PackageRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $PackageRoot -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
    Remove-Item -Force

$requiredPackageFiles = @(
    "__init__.py",
    "plugin.json",
    "README.md",
    "requirements.txt",
    "plugin/plugin.py",
    "plugin/backport_core.py",
    "plugin/i18n.py"
)
foreach ($file in $requiredPackageFiles) {
    $path = Join-Path $PackageRoot $file
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Package is missing required file: kicad-backport/$file"
    }
}

Compress-Archive -LiteralPath $PackageRoot -DestinationPath $ArchivePath -Force

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
try {
    $hasPackageRoot = $false
    $archiveEntries = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $zip.Entries) {
        [void]$archiveEntries.Add($entry.FullName)
        if ($entry.FullName -like 'kicad-backport/*') {
            $hasPackageRoot = $true
        }
    }
    if (-not $hasPackageRoot) {
        throw "Archive does not contain the kicad-backport directory."
    }
    foreach ($file in $requiredPackageFiles) {
        $entryName = "kicad-backport/$file"
        if (-not $archiveEntries.Contains($entryName)) {
            throw "Archive is missing required file: $entryName"
        }
    }
}
finally {
    $zip.Dispose()
}

Write-Host "Built unpacked package: $PackageRoot"
Write-Host "Built archive: $ArchivePath"
Write-Host "Version: $Version"
