param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$release = Join-Path $root "release\$Version\windows-x64"
$work = Join-Path $root "build\pyinstaller-$Version"
$exe = Join-Path $release "OpenVisionMeasure.exe"
$checksums = Join-Path $release "SHA256SUMS.txt"
$archive = Join-Path $release "OpenVisionMeasure-$Version-win64.zip"

Push-Location $root
try {
    New-Item -ItemType Directory -Force -Path $release, $work | Out-Null
    uv sync --extra dev
    uv run pyinstaller `
        --noconfirm `
        --clean `
        --distpath $release `
        --workpath $work `
        packaging\OpenVisionMeasure.spec

    if (-not (Test-Path -LiteralPath $exe)) {
        throw "PyInstaller did not produce $exe"
    }

    $env:QT_QPA_PLATFORM = "offscreen"
    $process = Start-Process `
        -FilePath $exe `
        -ArgumentList "--smoke-test" `
        -Wait `
        -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Packaged application smoke test failed with exit code $($process.ExitCode)"
    }

    $hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash *OpenVisionMeasure.exe" |
        Set-Content -LiteralPath $checksums -Encoding ascii

    Compress-Archive `
        -LiteralPath $exe, $checksums, (Join-Path $root "LICENSE"), (Join-Path $root "THIRD_PARTY_NOTICES.md") `
        -DestinationPath $archive `
        -Force

    [pscustomobject]@{
        Exe = $exe
        ExeBytes = (Get-Item -LiteralPath $exe).Length
        Sha256 = $hash
        Archive = $archive
        ArchiveBytes = (Get-Item -LiteralPath $archive).Length
    } | ConvertTo-Json
}
finally {
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    Pop-Location
}
