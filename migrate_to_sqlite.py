"""
Разовый перенос данных из продакшен Postgres (Supabase) в локальный SQLite.

Использование:
    python3 migrate_to_sqlite.py [путь_к_sqlite]

Источник берётся из переменной окружения DATABASE_URL (.env) — должен
указывать на Postgres. Если путь к SQLite не передан, используется
./life_os_local.db (не life_os.db, чтобы не перезаписать то, что уже
может использоваться локально).
"""
import sys
import os
from sqlalchemy import create_engine, MetaData, Table, insert, select

# Импортируем все модели, чтобы Base.metadata знал обо всех таблицах
from database import Base
import models  # noqa: F401
import kanban_models  # noqa: F401
import habits_models  # noqa: F401
import workouts_models  # noqa: F401
import finance_models  # noqa: F401
import profile_models  # noqa: F401
import roadmap_models  # noqa: F401


def main():
    source_url = os.getenv("DATABASE_URL")
    if not source_url or source_url.startswith("sqlite"):
        print("DATABASE_URL не задан или уже указывает на SQLite — нечего мигрировать.")
        sys.exit(1)

    dest_path = sys.argv[1] if len(sys.argv) > 1 else "./life_os_local.db"
    dest_url = f"sqlite:///{dest_path}"

    print(f"Источник: {source_url.split('@')[-1] if '@' in source_url else source_url}")
    print(f"Назначение: {dest_url}")

    source_engine = create_engine(source_url)
    dest_engine = create_engine(dest_url, connect_args={"check_same_thread": False})

    # Схема в назначении создаётся из текущих ORM-моделей (актуальная,
    # со всеми последними колонками), а не копированием схемы источника
    Base.metadata.create_all(bind=dest_engine)

    total_rows = 0
    with source_engine.connect() as src_conn, dest_engine.begin() as dest_conn:
        for table in Base.metadata.sorted_tables:
            rows = src_conn.execute(select(table)).mappings().all()
            if not rows:
                print(f"  {table.name}: 0 строк")
                continue
            dest_conn.execute(insert(table), [dict(r) for r in rows])
            total_rows += len(rows)
            print(f"  {table.name}: {len(rows)} строк")

    print(f"Готово. Перенесено строк: {total_rows}")
    print(f"Локальная БД: {os.path.abspath(dest_path)}")


if __name__ == "__main__":
    main()
