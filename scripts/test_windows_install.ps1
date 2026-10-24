# Integration test using the actual locally built archive, without network access.
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
function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
    if (-not $Uri.StartsWith('https://github.com/mhanayama/gen-pass/releases/download/vtest/')) {
        throw "Unexpected URL: $Uri"
    }
    Copy-Item (Join-Path $fixture ($Uri.Split('/')[-1])) $OutFile
}
try {
    $env:GEN_PASS_INSTALL_DIR = Join-Path $temporary 'install with spaces'
    $env:GEN_PASS_VERSION = 'vtest'
    & (Join-Path $root 'install.ps1')
    $binary = Join-Path $env:GEN_PASS_INSTALL_DIR 'gen-pass.exe'
    $installedDir = $env:GEN_PASS_INSTALL_DIR
    $expectedHash = (Get-FileHash $binary).Hash
    # Simulate an older executable in a custom directory; find it via PATH on update.
    Add-Content -LiteralPath $binary -Value 'older release'
    $env:GEN_PASS_INSTALL_DIR = $null
    & (Join-Path $root 'install.ps1')
    if ((Get-FileHash $binary).Hash -ne $expectedHash) { throw 'Old executable was not updated' }
    $env:GEN_PASS_INSTALL_DIR = $installedDir
    if (-not (Test-Path (Join-Path $env:GEN_PASS_INSTALL_DIR 'licenses\Python-LICENSE.txt'))) {
        throw 'Missing Python license'
    }
    & $binary --hr --no-clipboard | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Installed executable failed' }
    $before = (Get-FileHash $binary).Hash
    Set-Content -LiteralPath $checksumFixture -Value ('0' * 64)
    $failed = $false
    try { & (Join-Path $root 'install.ps1') }
    catch {
        if ($_.Exception.Message -notlike '*SHA-256 mismatch*') { throw }
        $failed = $true
    }
    if (-not $failed) { throw 'Installer accepted a bad checksum' }
    if ((Get-FileHash $binary).Hash -ne $before) { throw 'Existing executable changed after failure' }
    if (Get-ChildItem -LiteralPath $installedDir -Filter '.gen-pass-*.exe') {
        throw 'Installer left a staged executable behind'
    }
    Write-Host 'PASS Windows install, update, licenses, and checksum failure'
}
finally {
    Set-Content -LiteralPath $checksumFixture -Value $originalChecksum -NoNewline
    [Environment]::SetEnvironmentVariable('Path', $originalUserPath, 'User')
    $env:Path = $originalPath
    $env:GEN_PASS_INSTALL_DIR = $originalDir
    $env:GEN_PASS_VERSION = $originalVersion
    if (Test-Path $temporary) { Remove-Item $temporary -Recurse -Force }
}
