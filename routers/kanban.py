from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from kanban_models import (
    Board, BoardCreate,
    KanbanColumn, ColumnCreate, ColumnUpdate,
    KanbanCard, CardCreate, CardUpdate, MoveCardRequest
)
from database import get_db
import kanban_db
import uuid

router = APIRouter(prefix="/kanban", tags=["kanban"])


# Boards
@router.get("/boards", response_model=list[Board])
def get_boards(db: Session = Depends(get_db)):
    return kanban_db.get_all_boards(db)

@router.post("/boards", response_model=Board, status_code=201)
def create_board(payload: BoardCreate, db: Session = Depends(get_db)):
    board = Board(id=str(uuid.uuid4()), **payload.model_dump())
    return kanban_db.create_board(db, board)

@router.delete("/boards/{board_id}", status_code=204)
def delete_board(board_id: str, db: Session = Depends(get_db)):
    if not kanban_db.delete_board(db, board_id):
        raise HTTPException(404, "Доска не найдена")


# Columns
@router.get("/boards/{board_id}/columns", response_model=list[KanbanColumn])
def get_columns(board_id: str, db: Session = Depends(get_db)):
    return kanban_db.get_columns(db, board_id)

@router.post("/columns", response_model=KanbanColumn, status_code=201)
def create_column(payload: ColumnCreate, db: Session = Depends(get_db)):
    col = KanbanColumn(id=str(uuid.uuid4()), **payload.model_dump())
    return kanban_db.create_column(db, col)

@router.patch("/columns/{col_id}", response_model=KanbanColumn)
def update_column(col_id: str, payload: ColumnUpdate, db: Session = Depends(get_db)):
    updated = kanban_db.update_column(db, col_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(404, "Колонка не найдена")
    return updated

@router.delete("/columns/{col_id}", status_code=204)
def delete_column(col_id: str, db: Session = Depends(get_db)):
    if not kanban_db.delete_column(db, col_id):
        raise HTTPException(404, "Колонка не найдена")


# Cards
@router.get("/columns/{col_id}/cards", response_model=list[KanbanCard])
def get_cards(col_id: str, db: Session = Depends(get_db)):
    return kanban_db.get_cards(db, col_id)

@router.post("/cards", response_model=KanbanCard, status_code=201)
def create_card(payload: CardCreate, db: Session = Depends(get_db)):
    card = KanbanCard(id=str(uuid.uuid4()), **payload.model_dump())
    return kanban_db.create_card(db, card)

# IMPORTANT: /cards/move must come BEFORE /cards/{card_id} to avoid route conflict
@router.post("/cards/move", response_model=KanbanCard)
def move_card(payload: MoveCardRequest, db: Session = Depends(get_db)):
    moved = kanban_db.move_card(db, payload.card_id, payload.target_column_id, payload.position)
    if not moved:
        raise HTTPException(404, "Карточка не найдена")
    return moved

@router.patch("/cards/{card_id}", response_model=KanbanCard)
def update_card(card_id: str, payload: CardUpdate, db: Session = Depends(get_db)):
    updated = kanban_db.update_card(db, card_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(404, "Карточка не найдена")
    return updated

@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: str, db: Session = Depends(get_db)):
    if not kanban_db.delete_card(db, card_id):
        raise HTTPException(404, "Карточка не найдена")
