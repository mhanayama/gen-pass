# Install the Windows x64 standalone release. No Python or administrator rights.
& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $cpu = $env:PROCESSOR_ARCHITEW6432
    if (-not $cpu) { $cpu = $env:PROCESSOR_ARCHITECTURE }
    if ($cpu -ne 'AMD64') { throw 'This installer supports Windows x64 only.' }

    $version = $env:GEN_PASS_VERSION
    if (-not $version) { $version = 'latest' }
    if ($version -notmatch '^[a-zA-Z0-9._-]+$') { throw 'Invalid GEN_PASS_VERSION.' }
    $base = 'https://github.com/mhanayama/gen-pass/releases'
    if ($version -eq 'latest') { $base += '/latest/download' }
    else { $base += "/download/$version" }
    $asset = 'gen-pass-windows-x86_64.zip'
    $installDir = $env:GEN_PASS_INSTALL_DIR
    if (-not $installDir) {
        $existing = Get-Command gen-pass.exe -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($existing) { $installDir = Split-Path $existing.Source -Parent }
    }
    if (-not $installDir) { $installDir = Join-Path $env:LOCALAPPDATA 'Programs\gen-pass' }
    if (-not [IO.Path]::IsPathRooted($installDir)) { throw 'GEN_PASS_INSTALL_DIR must be an absolute path.' }
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
    $staged = $null
    New-Item -ItemType Directory -Path $temporary | Out-Null
    try {
        Write-Host "Downloading $asset ($version)..."
        $archive = Join-Path $temporary $asset
        Invoke-WebRequest -UseBasicParsing "$base/$asset" -OutFile $archive
        $checksum = Join-Path $temporary 'checksum'
        Invoke-WebRequest -UseBasicParsing "$base/$asset.sha256" -OutFile $checksum
        $expected = ((Get-Content $checksum -Raw).Trim() -split '\s+')[0]
        if ($expected -notmatch '^[0-9a-fA-F]{64}$') { throw 'Invalid SHA-256 checksum.' }
        if ((Get-FileHash -Path $archive -Algorithm SHA256).Hash -ne $expected) {
            throw 'SHA-256 mismatch; nothing was installed.'
        }
        Expand-Archive -Path $archive -DestinationPath $temporary
        $bundle = Join-Path $temporary 'gen-pass'
        $binary = Join-Path $bundle 'gen-pass.exe'
        & $binary --help | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'The downloaded executable could not run.' }
        New-Item -ItemType Directory -Force -Path $installDir | Out-Null
        $destination = Join-Path $installDir 'gen-pass.exe'
        $previous = Get-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
        if ($previous -and $previous.PSIsContainer) {
            throw "Expected an executable, found a directory: $destination"
        }
        $staged = Join-Path $installDir ('.gen-pass-' + [guid]::NewGuid().ToString() + '.exe')
        Copy-Item -LiteralPath $binary -Destination $staged
        Get-ChildItem -LiteralPath $bundle | Where-Object { $_.Name -ne 'gen-pass.exe' } |
            Copy-Item -Destination $installDir -Recurse -Force
        if ($previous) {
            Write-Host "Updating existing installation: $destination"
        }
        # File.Replace rejects symbolic links on Windows. Rename the staged file
        # over the directory entry instead, without opening or writing its target.
        # Stage in the destination directory so no cross-volume copy is necessary.
        if (-not ('GenPass.Installer.FileOperations' -as [type])) {
            Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
namespace GenPass.Installer {
    public static class FileOperations {
        [DllImport("kernel32.dll", EntryPoint = "MoveFileExW", ExactSpelling = true,
            CharSet = CharSet.Unicode, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool MoveFileEx(string source, string destination, uint flags);
    }
}
'@
        }
        if (-not [GenPass.Installer.FileOperations]::MoveFileEx($staged, $destination, 1)) {
            $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
            $reason = [ComponentModel.Win32Exception]::new($code).Message
            throw "Could not update gen-pass.exe; the existing executable was kept. $reason"
        }

        $userPath = [string][Environment]::GetEnvironmentVariable('Path', 'User')
        if ($installDir -notin ($userPath -split ';')) {
            $newPath = ($userPath.TrimEnd(';') + ';' + $installDir).TrimStart(';')
            [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        }
        if ($installDir -notin ($env:Path -split ';')) { $env:Path += ";$installDir" }
        Write-Host "Installed: $installDir\gen-pass.exe"
        Write-Host 'Run: gen-pass (reopen other terminals to refresh PATH)'
    }
    finally {
        if ($staged -and (Test-Path -LiteralPath $staged)) {
            Remove-Item -LiteralPath $staged -Force
        }
        Remove-Item -LiteralPath $temporary -Recurse -Force
    }
}
