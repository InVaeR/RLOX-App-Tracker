# Сборка приложения в onedir
param(
    [string]$Version = "2.0.0",
    [string]$OutDir = "$PSScriptRoot\..\dist\app"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
$SpecFile = "$Root\app\RLOXAppTracker.spec"
$VersionDir = "$OutDir\versions\$Version"

Write-Host "=== Сборка RLOXAppTracker v$Version ==="

# Создаём spec если не существует
if (-not (Test-Path $SpecFile)) {
    Write-Host "Создание spec файла..."
    python -c "
import PyInstaller.__main__
PyInstaller.__main__.run([
    'app/src/rlox_app_tracker/__main__.py',
    '--name=RLOXAppTracker',
    '--onedir',
    '--distpath=dist/app/versions/$Version',
    '--workpath=build/pyinstaller',
    '--add-data=app/assets;assets',
    '--hidden-import=win32gui',
    '--hidden-import=win32process',
    '--hidden-import=psutil',
    '--collect-data=PySide6',
    '--windowed',
    '--icon=app/assets/app.ico',
])
" -join "`n"
    if (-not $?) { throw "PyInstaller failed" }
}

# Если spec уже есть, просто запускаем
if (Test-Path $SpecFile) {
    & pyinstaller $SpecFile --noconfirm
    if (-not $?) { throw "PyInstaller spec build failed" }
}

Write-Host "Сборка завершена: $VersionDir"
