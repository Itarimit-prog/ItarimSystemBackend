#!/usr/bin/env python3
"""
Очистка: удалить все существующие колонки 'Done' и их карточки.
Запуск: cd /app && python cleanup_done_columns.py
"""
import sys
sys.path.insert(0, '/app')

from database import SessionLocal, engine
from kanban_models import KanbanColumnModel, KanbanCardModel
from sqlalchemy import inspect


def cleanup_done_columns():
    db = SessionLocal()
    try:
        # Находим все колонки с title = 'Done'
        done_cols = db.query(KanbanColumnModel).filter(
            KanbanColumnModel.title == 'Done'
        ).all()

        if not done_cols:
            print("Колонок 'Done' не найдено.")
            return

        for col in done_cols:
            # Удаляем карточки в колонке
            cards = db.query(KanbanCardModel).filter(
                KanbanCardModel.column_id == col.id
            ).all()
            for card in cards:
                db.delete(card)
                print(f"  Удалена карточка '{card.title}' из колонки {col.id}")

            db.delete(col)
            print(f"Удалена колонка 'Done' (id={col.id}, board_id={col.board_id})")

        db.commit()
        print(f"\nГотово. Удалено колонок: {len(done_cols)}")
    except Exception as e:
        db.rollback()
        print(f"Ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    cleanup_done_columns()
