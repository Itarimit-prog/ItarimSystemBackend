from datetime import datetime
from sqlalchemy.orm import Session
from kanban_models import (
    BoardModel, Board, BoardCreate,
    KanbanColumnModel, KanbanColumn, ColumnCreate, ColumnUpdate,
    KanbanCardModel, KanbanCard, CardCreate, CardUpdate, MoveCardRequest
)
from models import TaskModel, TaskStatus
import uuid


# Seed data function removed to avoid test data in production
def _placeholder_seed_kanban(): pass


# Boards
def get_all_boards(db: Session) -> list[Board]:
    boards = db.query(BoardModel).all()
    return [Board(id=b.id, name=b.name) for b in boards]

def create_board(db: Session, board: Board) -> Board:
    db_board = BoardModel(id=board.id, name=board.name)
    db.add(db_board)
    db.commit()
    db.refresh(db_board)
    return board

def delete_board(db: Session, board_id: str) -> bool:
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        return False
    
    # Удаляем все колонки и карточки
    columns = db.query(KanbanColumnModel).filter(KanbanColumnModel.board_id == board_id).all()
    for col in columns:
        db.query(KanbanCardModel).filter(KanbanCardModel.column_id == col.id).delete()
        db.delete(col)
    
    db.delete(board)
    db.commit()
    return True


# Columns
def get_columns(db: Session, board_id: str) -> list[KanbanColumn]:
    columns = db.query(KanbanColumnModel).filter(
        KanbanColumnModel.board_id == board_id
    ).order_by(KanbanColumnModel.position).all()
    
    return [
        KanbanColumn(id=c.id, board_id=c.board_id, title=c.title, color=c.color, position=c.position, is_completed_column=bool(c.is_completed_column))
        for c in columns
    ]

def create_column(db: Session, col: KanbanColumn) -> KanbanColumn:
    db_col = KanbanColumnModel(
        id=col.id,
        board_id=col.board_id,
        title=col.title,
        color=col.color,
        position=col.position,
        is_completed_column=1 if col.is_completed_column else 0
    )
    db.add(db_col)
    db.commit()
    db.refresh(db_col)
    return col

def update_column(db: Session, col_id: str, updates: dict) -> KanbanColumn | None:
    db_col = db.query(KanbanColumnModel).filter(KanbanColumnModel.id == col_id).first()
    if not db_col:
        return None
    
    for key, value in updates.items():
        if value is not None:
            if key == 'is_completed_column':
                value = 1 if value else 0
            setattr(db_col, key, value)
    
    db.commit()
    db.refresh(db_col)
    
    return KanbanColumn(
        id=db_col.id,
        board_id=db_col.board_id,
        title=db_col.title,
        color=db_col.color,
        position=db_col.position,
        is_completed_column=bool(db_col.is_completed_column)
    )

def delete_column(db: Session, col_id: str) -> bool:
    db_col = db.query(KanbanColumnModel).filter(KanbanColumnModel.id == col_id).first()
    if not db_col:
        return False
    
    # Удаляем все карточки в колонке
    db.query(KanbanCardModel).filter(KanbanCardModel.column_id == col_id).delete()
    db.delete(db_col)
    db.commit()
    return True


# Cards
def get_cards(db: Session, column_id: str) -> list[KanbanCard]:
    cards = db.query(KanbanCardModel).filter(
        KanbanCardModel.column_id == column_id
    ).order_by(KanbanCardModel.position).all()
    
    return [
        KanbanCard(id=c.id, column_id=c.column_id, title=c.title, deadline=c.deadline, position=c.position, task_id=c.task_id, completed=bool(c.completed), completed_at=c.completed_at)
        for c in cards
    ]

def create_card(db: Session, card: KanbanCard) -> KanbanCard:
    db_card = KanbanCardModel(
        id=card.id,
        column_id=card.column_id,
        title=card.title,
        deadline=card.deadline,
        position=card.position,
        task_id=card.task_id,
        completed=1 if card.completed else 0,
        completed_at=card.completed_at
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return card

def update_card(db: Session, card_id: str, updates: dict) -> KanbanCard | None:
    db_card = db.query(KanbanCardModel).filter(KanbanCardModel.id == card_id).first()
    if not db_card:
        return None
    
    for key, value in updates.items():
        if value is not None:
            if key == 'completed':
                value = 1 if value else 0
            setattr(db_card, key, value)
    
    db.commit()
    db.refresh(db_card)
    
    return KanbanCard(
        id=db_card.id,
        column_id=db_card.column_id,
        title=db_card.title,
        deadline=db_card.deadline,
        position=db_card.position,
        task_id=db_card.task_id,
        completed=bool(db_card.completed),
        completed_at=db_card.completed_at
    )

def delete_card(db: Session, card_id: str) -> bool:
    db_card = db.query(KanbanCardModel).filter(KanbanCardModel.id == card_id).first()
    if not db_card:
        return False
    
    db.delete(db_card)
    db.commit()
    return True

def move_card(db: Session, card_id: str, target_column_id: str, position: int) -> KanbanCard | None:
    db_card = db.query(KanbanCardModel).filter(KanbanCardModel.id == card_id).first()
    if not db_card:
        return None
    
    old_column_id = db_card.column_id
    
    # Определяем, была ли колонка завершающей (старая колонка)
    old_column = db.query(KanbanColumnModel).filter(KanbanColumnModel.id == old_column_id).first()
    was_completed = old_column and old_column.is_completed_column == 1
    
    # Определяем, является ли новая колонка завершающей
    target_column = db.query(KanbanColumnModel).filter(KanbanColumnModel.id == target_column_id).first()
    is_now_completed = target_column and target_column.is_completed_column == 1
    
    # Обновляем статус основной задачи, если есть связь
    if db_card.task_id:
        task = db.query(TaskModel).filter(TaskModel.id == db_card.task_id).first()
        if task:
            if is_now_completed and not was_completed:
                task.status = TaskStatus.done
            elif not is_now_completed and was_completed:
                task.status = TaskStatus.pending
    
    # Обновляем completed/completed_at при переходе в/из завершающей колонки
    if is_now_completed and not was_completed:
        db_card.completed = 1
        db_card.completed_at = datetime.utcnow().isoformat()
    elif not is_now_completed and was_completed:
        db_card.completed = 0
        db_card.completed_at = None
    
    db_card.column_id = target_column_id
    db_card.position = position
    
    # Пересчитываем позиции в старой колонке
    if old_column_id != target_column_id:
        old_cards = db.query(KanbanCardModel).filter(
            KanbanCardModel.column_id == old_column_id
        ).order_by(KanbanCardModel.position).all()
        for i, c in enumerate(old_cards):
            c.position = i
    
    # Пересчитываем позиции в новой колонке (включая перемещенную карточку)
    target_cards = db.query(KanbanCardModel).filter(
        KanbanCardModel.column_id == target_column_id
    ).order_by(KanbanCardModel.position).all()
    
    # Упорядочиваем: сначала все кроме перемещенной, затем вставляем на нужную позицию
    reordered = [c for c in target_cards if c.id != card_id]
    reordered.insert(position, db_card)
    for i, c in enumerate(reordered):
        c.position = i
    
    db.commit()
    db.refresh(db_card)
    
    return KanbanCard(
        id=db_card.id,
        column_id=db_card.column_id,
        title=db_card.title,
        deadline=db_card.deadline,
        position=db_card.position,
        task_id=db_card.task_id,
        completed=bool(db_card.completed),
        completed_at=db_card.completed_at
    )
