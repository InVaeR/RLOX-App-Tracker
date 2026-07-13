# Сборка C# лаунчера
param(
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
$Project = Join-Path $Root "launcher\src\RLOXLauncher\RLOXLauncher.csproj"
$OutDir = Join-Path $Root "dist\launcher"

Write-Host "=== Сборка RLOXLauncher (C#) ==="

dotnet publish $Project `
    --configuration $Configuration `
    --runtime win-x64 `
    --self-contained false `
    --output $OutDir `
    -p:PublishSingleFile=true `
    -p:IncludeNativeLibrariesForSelfExtract=true

if (-not $?) { throw "Launcher build failed" }

Write-Host "Лаунчер собран: $OutDir\RLOXLauncher.exe"
