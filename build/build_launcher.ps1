# Сборка лаунчера
param(
    [string]$OutDir = "$PSScriptRoot\..\dist\launcher"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."

Write-Host "=== Сборка RLOXLauncher ==="

$OutDir = Join-Path $Root "dist\launcher"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

& pyinstaller --noconfirm `
    --onedir `
    --name RLOXLauncher `
    --distpath $OutDir `
    --workpath build\pyinstaller_launcher `
    --windowed `
    --collect-data=psutil `
    launcher\src\launcher.py

if (-not $?) { throw "Launcher build failed" }

Write-Host "Лаунчер собран: $OutDir"
