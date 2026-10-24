# Integration tests with the real release archive; no network or clipboard access.
# Run in both Windows PowerShell 5.1 and PowerShell 7.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$fixture = Join-Path $root 'dist\release'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
$originalDir = $env:GEN_PASS_INSTALL_DIR
$originalVersion = $env:GEN_PASS_VERSION
$originalPath = $env:Path
$originalUserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$checksumFixture = Join-Path $fixture 'gen-pass-windows-x86_64.zip.sha256'
$originalChecksum = Get-Content -LiteralPath $checksumFixture -Raw
$junction = $null

function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
    if (-not $Uri.StartsWith('https://github.com/mhanayama/gen-pass/releases/download/vtest/')) {
        throw "Unexpected URL: $Uri"
    }
    Copy-Item (Join-Path $fixture ($Uri.Split('/')[-1])) $OutFile
}

function Assert-Installed {
    param([string]$Path, [string]$Hash)
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Installed executable is still a reparse point: $Path"
    }
    if ((Get-FileHash -LiteralPath $Path).Hash -ne $Hash) {
        throw "Installed executable differs from the release: $Path"
    }
    if (Get-ChildItem -LiteralPath (Split-Path $Path -Parent) -Filter '.gen-pass-*.exe') {
        throw 'Installer left a staged executable behind'
    }
}

function Assert-InstallFails {
    param([string]$Pattern)
    $failed = $false
    try { & (Join-Path $root 'install.ps1') }
    catch {
        if ($_.Exception.Message -notlike $Pattern) { throw }
        $failed = $true
    }
    if (-not $failed) { throw "Installer unexpectedly succeeded; expected $Pattern" }
}

try {
    # Use a non-ASCII path without requiring a BOM in this PS 5.1-compatible file.
    $name = 'install with spaces ' + [char]0x65E5 + [char]0x672C
    $installedDir = Join-Path $temporary $name
    $env:GEN_PASS_INSTALL_DIR = $installedDir
    $env:GEN_PASS_VERSION = 'vtest'
    & (Join-Path $root 'install.ps1')
    $binary = Join-Path $installedDir 'gen-pass.exe'
    $expectedHash = (Get-FileHash -LiteralPath $binary).Hash
    Assert-Installed $binary $expectedHash
    if (-not (Test-Path (Join-Path $installedDir 'licenses\Python-LICENSE.txt'))) {
        throw 'Missing Python license'
    }
    Write-Host 'PASS fresh install in a path containing spaces and Japanese characters'

    # Ordinary old file, discovered through PATH instead of an explicit directory.
    Add-Content -LiteralPath $binary -Value 'older release'
    $env:GEN_PASS_INSTALL_DIR = $null
    & (Join-Path $root 'install.ps1')
    Assert-Installed $binary $expectedHash
    Write-Host 'PASS ordinary executable update detected on PATH'

    foreach ($kind in @('SymbolicLink', 'HardLink')) {
        $target = Join-Path $temporary ("old-" + $kind + '.exe')
        Copy-Item -LiteralPath $binary -Destination $target
        Add-Content -LiteralPath $target -Value 'old linked executable'
        $targetHash = (Get-FileHash -LiteralPath $target).Hash
        [IO.File]::Delete($binary)
        New-Item -ItemType $kind -Path $binary -Target $target | Out-Null
        if ((Get-Item -LiteralPath $binary -Force).LinkType -ne $kind) {
            throw "Test did not create a real $kind"
        }
        & (Join-Path $root 'install.ps1')
        Assert-Installed $binary $expectedHash
        if ((Get-FileHash -LiteralPath $target).Hash -ne $targetHash) {
            throw "Installer changed the $kind target"
        }
        Write-Host "PASS $kind update detected on PATH; target remains unchanged"
    }

    # A dangling symlink must be replaced even though its target does not exist.
    $env:GEN_PASS_INSTALL_DIR = $installedDir
    $missingTarget = Join-Path $temporary 'missing-target.exe'
    Set-Content -LiteralPath $missingTarget -Value 'temporary target'
    [IO.File]::Delete($binary)
    New-Item -ItemType SymbolicLink -Path $binary -Target $missingTarget | Out-Null
    [IO.File]::Delete($missingTarget)
    & (Join-Path $root 'install.ps1')
    Assert-Installed $binary $expectedHash
    if (Test-Path -LiteralPath $missingTarget) { throw 'Installer recreated the missing link target' }
    Write-Host 'PASS dangling symlink update without creating its target'

    # Keep the old command usable if replacement is denied by an open file handle.
    $before = (Get-FileHash -LiteralPath $binary).Hash
    $handle = [IO.File]::Open($binary, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try { Assert-InstallFails '*Could not update gen-pass.exe*' }
    finally { $handle.Dispose() }
    Assert-Installed $binary $before
    Write-Host 'PASS locked executable stays intact after replacement fails'

    # A directory junction in the installation path must itself stay a junction.
    $physical = Join-Path $temporary 'physical bin'
    $junction = Join-Path $temporary 'junction bin'
    New-Item -ItemType Directory -Path $physical | Out-Null
    New-Item -ItemType Junction -Path $junction -Target $physical | Out-Null
    Copy-Item -LiteralPath $binary -Destination (Join-Path $physical 'gen-pass.exe')
    Add-Content -LiteralPath (Join-Path $physical 'gen-pass.exe') -Value 'older release'
    $env:GEN_PASS_INSTALL_DIR = $junction
    & (Join-Path $root 'install.ps1')
    Assert-Installed (Join-Path $physical 'gen-pass.exe') $expectedHash
    if ((Get-Item -LiteralPath $junction -Force).LinkType -ne 'Junction') {
        throw 'Installer replaced the directory junction'
    }
    Write-Host 'PASS update through a directory junction'

    # A bad checksum must leave both an existing symlink and its target intact.
    $env:GEN_PASS_INSTALL_DIR = $installedDir
    $target = Join-Path $temporary 'checksum-link-target.exe'
    Copy-Item -LiteralPath $binary -Destination $target
    $targetHash = (Get-FileHash -LiteralPath $target).Hash
    [IO.File]::Delete($binary)
    New-Item -ItemType SymbolicLink -Path $binary -Target $target | Out-Null
    Set-Content -LiteralPath $checksumFixture -Value ('0' * 64)
    Assert-InstallFails '*SHA-256 mismatch*'
    if ((Get-Item -LiteralPath $binary -Force).LinkType -ne 'SymbolicLink') {
        throw 'Checksum failure changed the symlink'
    }
    if ((Get-FileHash -LiteralPath $target).Hash -ne $targetHash) {
        throw 'Checksum failure changed the link target'
    }
    Set-Content -LiteralPath $checksumFixture -Value $originalChecksum -NoNewline
    Write-Host 'PASS checksum failure preserves the old symlink and target'

    # Do not replace a directory that happens to have the executable's name.
    [IO.File]::Delete($binary)
    New-Item -ItemType Directory -Path $binary | Out-Null
    $marker = Join-Path $binary 'keep.txt'
    Set-Content -LiteralPath $marker -Value 'keep'
    Assert-InstallFails '*Expected an executable, found a directory*'
    if (-not (Test-Path -LiteralPath $marker)) { throw 'Installer modified the existing directory' }
    Write-Host 'PASS directory at the executable path is preserved'

    Write-Host ("PASS all Windows installer scenarios on PowerShell " + $PSVersionTable.PSVersion)
}
finally {
    Set-Content -LiteralPath $checksumFixture -Value $originalChecksum -NoNewline
    [Environment]::SetEnvironmentVariable('Path', $originalUserPath, 'User')
    $env:Path = $originalPath
    $env:GEN_PASS_INSTALL_DIR = $originalDir
    $env:GEN_PASS_VERSION = $originalVersion
    # Unlink the junction first; never recursively traverse its target in cleanup.
    if ($junction -and (Test-Path -LiteralPath $junction)) { [IO.Directory]::Delete($junction) }
    if (Test-Path $temporary) { Remove-Item $temporary -Recurse -Force }
}
