# Сборка Python-бэкенда в один .exe для Tauri sidecar (Windows).
# Запускать из папки backend:  powershell -ExecutionPolicy Bypass -File .\build_sidecar.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venv = "venv_build"
$binName = "itarim-backend"
$destDir = "..\frontend\src-tauri\binaries"

if (-not (Test-Path $venv)) {
    Write-Host "Создаю окружение для сборки ($venv)..."
    python -m venv $venv
    & "$venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    & "$venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    & "$venv\Scripts\python.exe" -m pip install --quiet pyinstaller
}

Remove-Item -Recurse -Force build, dist, "$binName.spec" -ErrorAction SilentlyContinue

& "$venv\Scripts\python.exe" -m PyInstaller --name $binName --onefile `
    --collect-all uvicorn --collect-submodules routers `
    --exclude-module psycopg2 --exclude-module databases `
    sidecar_entry.py

$triple = ((rustc -Vv) | Select-String "^host:").ToString().Split(" ")[1]
New-Item -ItemType Directory -Force $destDir | Out-Null
Copy-Item "dist\$binName.exe" "$destDir\$binName-$triple.exe" -Force

Write-Host "Готово: $destDir\$binName-$triple.exe"
