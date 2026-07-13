# Сборка установщика через Inno Setup
param(
    [string]$Version = "2.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
$InnoDir = "${env:ProgramFiles(x86)}\Inno Setup 6"
$ISCC = "$InnoDir\ISCC.exe"

if (-not (Test-Path $ISCC)) {
    Write-Warning "Inno Setup не найден по пути $ISCC"
    Write-Warning "Установите Inno Setup 6: https://jrsoftware.org/isdl.php"
    exit 1
}

Write-Host "=== Сборка установщика v$Version ==="

& $ISCC `
    "/DAppVersion=$Version" `
    "$Root\installer\RLOXAppTracker.iss"

if (-not $?) { throw "Installer build failed" }

Write-Host "Установщик собран: dist\RLOX-App-Tracker-Setup-${Version}-x64.exe"
