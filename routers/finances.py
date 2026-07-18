from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from finance_models import (
    Transaction, TransactionCreate, TransactionUpdate,
    Debt, DebtCreate, DebtUpdate,
    Balance
)
from database import get_db
import finance_db
import uuid

router = APIRouter(prefix="/finances", tags=["finances"])


# ── Баланс ──

@router.get("/balance/", response_model=Balance)
def get_balance(db: Session = Depends(get_db)):
    return finance_db.get_balance(db)


# ── Транзакции ──

@router.get("/transactions/", response_model=list[Transaction])
def get_transactions(db: Session = Depends(get_db)):
    return finance_db.get_all_transactions(db)


@router.post("/transactions/", response_model=Transaction, status_code=201)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    txn = Transaction(id=str(uuid.uuid4()), **payload.model_dump())
    return finance_db.create_transaction(db, txn)


@router.put("/transactions/{txn_id}", response_model=Transaction)
def update_transaction(txn_id: str, payload: TransactionUpdate, db: Session = Depends(get_db)):
    updated = finance_db.update_transaction(db, txn_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")
    return updated


@router.delete("/transactions/{txn_id}", status_code=204)
def delete_transaction(txn_id: str, db: Session = Depends(get_db)):
    if not finance_db.delete_transaction(db, txn_id):
        raise HTTPException(status_code=404, detail="Транзакция не найдена")


# ── Долги ──

@router.get("/debts/", response_model=list[Debt])
def get_debts(db: Session = Depends(get_db)):
    return finance_db.get_all_debts(db)


@router.post("/debts/", response_model=Debt, status_code=201)
def create_debt(payload: DebtCreate, db: Session = Depends(get_db)):
    debt = Debt(id=str(uuid.uuid4()), **payload.model_dump())
    return finance_db.create_debt(db, debt)


@router.put("/debts/{debt_id}", response_model=Debt)
def update_debt(debt_id: str, payload: DebtUpdate, db: Session = Depends(get_db)):
    updated = finance_db.update_debt(db, debt_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Долг не найден")
    return updated


@router.delete("/debts/{debt_id}", status_code=204)
def delete_debt(debt_id: str, db: Session = Depends(get_db)):
    if not finance_db.delete_debt(db, debt_id):
        raise HTTPException(status_code=404, detail="Долг не найден")
