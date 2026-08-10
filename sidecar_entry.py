"""
Точка входа для запуска бэкенда как sidecar-процесса внутри Tauri.
Собирается PyInstaller'ом в отдельный бинарь (см. build_sidecar.sh).

Порт и путь к БД приходят через переменные окружения PORT / DATABASE_URL,
которые задаёт Rust-код Tauri при запуске процесса (main.rs).
"""
import os
import uvicorn
from main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8420"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
