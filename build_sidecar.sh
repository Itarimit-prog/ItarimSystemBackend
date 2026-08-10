#!/bin/bash
# Собирает Python-бэкенд в один бинарь через PyInstaller и кладёт его
# в src-tauri/binaries с именем, которое ожидает Tauri sidecar
# (<name>-<target-triple>).
set -euo pipefail
cd "$(dirname "$0")"

VENV_DIR="venv_build"
BIN_NAME="itarim-backend"
DEST_DIR="../frontend/src-tauri/binaries"

if [ ! -d "$VENV_DIR" ]; then
  echo "Создаю чистое окружение для сборки ($VENV_DIR)..."
  python3 -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  pip install -q pyinstaller
else
  source "$VENV_DIR/bin/activate"
fi

rm -rf build dist "${BIN_NAME}.spec"

pyinstaller --name "$BIN_NAME" --onefile \
  --collect-all uvicorn --collect-submodules routers \
  --exclude-module psycopg2 --exclude-module databases \
  sidecar_entry.py

TARGET_TRIPLE=$(rustc -Vv | grep host | cut -d' ' -f2)
mkdir -p "$DEST_DIR"
cp "dist/${BIN_NAME}" "${DEST_DIR}/${BIN_NAME}-${TARGET_TRIPLE}"
chmod +x "${DEST_DIR}/${BIN_NAME}-${TARGET_TRIPLE}"

echo "Готово: ${DEST_DIR}/${BIN_NAME}-${TARGET_TRIPLE}"
