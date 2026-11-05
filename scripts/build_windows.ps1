param(
    [string]$Version = "0.3.0",
    [switch]$WithAI
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
    if ($WithAI) {
        uv sync --extra dev --extra ai
        $env:OVM_WITH_AI = "1"
    }
    else {
        uv sync --extra dev
    }
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
    if ($WithAI) {
        $aiLog = Join-Path $work "ai-smoke.log"
        Remove-Item -LiteralPath $aiLog -ErrorAction SilentlyContinue
        $env:OVM_AI_SMOKE_LOG = $aiLog
        $aiProcess = Start-Process `
            -FilePath $exe `
            -ArgumentList "--ai-smoke-test" `
            -Wait `
            -PassThru
        if ($aiProcess.ExitCode -ne 0) {
            $details = if (Test-Path -LiteralPath $aiLog) {
                Get-Content -LiteralPath $aiLog -Raw
            }
            else {
                "No AI smoke log was produced."
            }
            throw "Packaged AI runtime smoke test failed with exit code $($aiProcess.ExitCode):`n$details"
        }
        Remove-Item -LiteralPath $aiLog -ErrorAction SilentlyContinue
        $modelProcess = Start-Process `
            -FilePath $exe `
            -ArgumentList "--ai-model-smoke-test" `
            -Wait `
            -PassThru
        if ($modelProcess.ExitCode -ne 0) {
            $details = if (Test-Path -LiteralPath $aiLog) {
                Get-Content -LiteralPath $aiLog -Raw
            }
            else {
                "No AI model smoke log was produced."
            }
            throw "Packaged AI model smoke test failed with exit code $($modelProcess.ExitCode):`n$details"
        }
        Remove-Item Env:OVM_AI_SMOKE_LOG -ErrorAction SilentlyContinue
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
    Remove-Item Env:OVM_AI_SMOKE_LOG -ErrorAction SilentlyContinue
    Remove-Item Env:OVM_WITH_AI -ErrorAction SilentlyContinue
    Pop-Location
}
