param(
    [string]$Version,
    [ValidateSet("zip", "tar.gz", "all")]
    [string]$Format = "zip"
)

$ErrorActionPreference = "Stop"

$PluginRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistRoot = Join-Path $PluginRoot "dist"
$PackageRoot = Join-Path $DistRoot "kicad-backport"
$ZipArchivePath = Join-Path $DistRoot "kicad-backport.zip"
$TarGzArchivePath = Join-Path $DistRoot "kicad-backport.tar.gz"

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

function Get-ArchiveEntryName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $separators = [char[]]@(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $distFull = [System.IO.Path]::GetFullPath($DistRoot).TrimEnd($separators)
    $pathFull = [System.IO.Path]::GetFullPath($Path)
    $relative = $pathFull.Substring($distFull.Length).TrimStart($separators)
    return $relative.Replace("\", "/")
}

function Assert-ArchiveEntries {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Entries,
        [Parameter(Mandatory = $true)]
        [string]$ArchiveName
    )

    $hasPackageRoot = $false
    $archiveEntries = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($entry in $Entries) {
        if ($entry.Contains("\")) {
            throw "$ArchiveName contains a Windows path separator: $entry"
        }
        [void]$archiveEntries.Add($entry)
        if ($entry -like 'kicad-backport/*') {
            $hasPackageRoot = $true
        }
    }
    if (-not $hasPackageRoot) {
        throw "$ArchiveName does not contain the kicad-backport directory."
    }
    foreach ($file in $requiredPackageFiles) {
        $entryName = "kicad-backport/$file"
        if (-not $archiveEntries.Contains($entryName)) {
            throw "$ArchiveName is missing required file: $entryName"
        }
    }
}

function New-ZipPackageArchive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchivePath
    )

    Add-Type -AssemblyName System.IO.Compression
    if (Test-Path -LiteralPath $ArchivePath) {
        Remove-Item -LiteralPath $ArchivePath -Force
    }

    $stream = [System.IO.File]::Open($ArchivePath, [System.IO.FileMode]::CreateNew)
    $zip = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        Get-ChildItem -LiteralPath $PackageRoot -Recurse -File |
            Sort-Object FullName |
            ForEach-Object {
                $entryName = Get-ArchiveEntryName -Path $_.FullName
                $entry = $zip.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
                $entryStream = $entry.Open()
                $fileStream = [System.IO.File]::OpenRead($_.FullName)
                try {
                    $fileStream.CopyTo($entryStream)
                }
                finally {
                    $fileStream.Dispose()
                    $entryStream.Dispose()
                }
            }
    }
    finally {
        $zip.Dispose()
        $stream.Dispose()
    }
}

function Test-ZipPackageArchive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchivePath
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        Assert-ArchiveEntries -Entries @($zip.Entries | ForEach-Object { $_.FullName }) -ArchiveName "Archive"
    }
    finally {
        $zip.Dispose()
    }
}

function New-TarGzPackageArchive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchivePath
    )

    if (Test-Path -LiteralPath $ArchivePath) {
        Remove-Item -LiteralPath $ArchivePath -Force
    }

    $tar = Get-Command tar -ErrorAction SilentlyContinue
    if (-not $tar) {
        throw "tar was not found; cannot create .tar.gz archive."
    }

    & $tar.Source -czf $ArchivePath -C $DistRoot "kicad-backport"
    if ($LASTEXITCODE -ne 0) {
        throw "tar failed with exit code $LASTEXITCODE."
    }
}

function Test-TarGzPackageArchive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchivePath
    )

    $tar = Get-Command tar -ErrorAction SilentlyContinue
    if (-not $tar) {
        throw "tar was not found; cannot verify .tar.gz archive."
    }

    $entries = & $tar.Source -tzf $ArchivePath
    if ($LASTEXITCODE -ne 0) {
        throw "tar verification failed with exit code $LASTEXITCODE."
    }
    Assert-ArchiveEntries -Entries @($entries) -ArchiveName "Archive"
}

$builtArchives = @()
if ($Format -in @("zip", "all")) {
    New-ZipPackageArchive -ArchivePath $ZipArchivePath
    Test-ZipPackageArchive -ArchivePath $ZipArchivePath
    $builtArchives += $ZipArchivePath
}
if ($Format -in @("tar.gz", "all")) {
    New-TarGzPackageArchive -ArchivePath $TarGzArchivePath
    Test-TarGzPackageArchive -ArchivePath $TarGzArchivePath
    $builtArchives += $TarGzArchivePath
}

Write-Host "Built unpacked package: $PackageRoot"
foreach ($archive in $builtArchives) {
    Write-Host "Built archive: $archive"
}
Write-Host "Version: $Version"
