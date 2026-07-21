from sqlalchemy.orm import Session
from sqlalchemy import func
from finance_models import (
    TransactionModel, Transaction, TransactionCreate, TransactionUpdate,
    DebtModel, Debt, DebtCreate, DebtUpdate,
    Balance
)
from datetime import date
import uuid


def seed_finances(db: Session):
    """Добавляем демо-данные только если БД пуста"""
    existing = db.query(TransactionModel).first()
    if existing:
        return
    
    demo_txns = [
        TransactionModel(
            id=str(uuid.uuid4()),
            description="Зарплата",
            amount=3000.0,
            transaction_type="income",
            category="work",
            date="2026-06-17"
        ),
        TransactionModel(
            id=str(uuid.uuid4()),
            description="Продукты",
            amount=120.0,
            transaction_type="expense",
            category="food",
            date="2026-06-16"
        ),
        TransactionModel(
            id=str(uuid.uuid4()),
            description="Аренда",
            amount=800.0,
            transaction_type="expense",
            category="housing",
            date="2026-06-15"
        ),
        TransactionModel(
            id=str(uuid.uuid4()),
            description="Фриланс",
            amount=240.0,
            transaction_type="income",
            category="work",
            date="2026-06-14"
        ),
        TransactionModel(
            id=str(uuid.uuid4()),
            description="Бензин",
            amount=60.0,
            transaction_type="expense",
            category="transport",
            date="2026-06-13"
        ),
    ]
    db.add_all(demo_txns)

    demo_debts = [
        DebtModel(
            id=str(uuid.uuid4()),
            name="Максим",
            amount=200.0,
            direction="owe",
            note="За ужин, 10 июня",
            status="active"
        ),
        DebtModel(
            id=str(uuid.uuid4()),
            name="Банк (кредит)",
            amount=1500.0,
            direction="owe",
            note="До 30 июня",
            due_date="2026-06-30",
            status="active"
        ),
    ]
    db.add_all(demo_debts)
    
    db.commit()


# ── Транзакции ──

def get_all_transactions(db: Session) -> list[Transaction]:
    transactions = db.query(TransactionModel).order_by(
        TransactionModel.date.desc()
    ).all()
    
    return [
        Transaction(
            id=t.id,
            description=t.description,
            amount=t.amount,
            transaction_type=t.transaction_type,
            category=t.category,
            date=t.date
        )
        for t in transactions
    ]


def get_transaction(db: Session, txn_id: str) -> Transaction | None:
    t = db.query(TransactionModel).filter(TransactionModel.id == txn_id).first()
    if not t:
        return None
    
    return Transaction(
        id=t.id,
        description=t.description,
        amount=t.amount,
        transaction_type=t.transaction_type,
        category=t.category,
        date=t.date
    )


def create_transaction(db: Session, txn: Transaction) -> Transaction:
    db_txn = TransactionModel(
        id=txn.id,
        description=txn.description,
        amount=txn.amount,
        transaction_type=txn.transaction_type,
        category=txn.category,
        date=txn.date
    )
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return txn


def update_transaction(db: Session, txn_id: str, updates: dict) -> Transaction | None:
    db_txn = db.query(TransactionModel).filter(TransactionModel.id == txn_id).first()
    if not db_txn:
        return None
    
    for key, value in updates.items():
        setattr(db_txn, key, value)
    
    db.commit()
    db.refresh(db_txn)
    
    return Transaction(
        id=db_txn.id,
        description=db_txn.description,
        amount=db_txn.amount,
        transaction_type=db_txn.transaction_type,
        category=db_txn.category,
        date=db_txn.date
    )


def delete_transaction(db: Session, txn_id: str) -> bool:
    db_txn = db.query(TransactionModel).filter(TransactionModel.id == txn_id).first()
    if not db_txn:
        return False
    
    db.delete(db_txn)
    db.commit()
    return True


# ── Долги ──

def get_all_debts(db: Session) -> list[Debt]:
    debts = db.query(DebtModel).all()
    
    return [
        Debt(
            id=d.id,
            name=d.name,
            amount=d.amount,
            direction=d.direction,
            note=d.note,
            due_date=d.due_date,
            status=d.status
        )
        for d in debts
    ]


def get_debt(db: Session, debt_id: str) -> Debt | None:
    d = db.query(DebtModel).filter(DebtModel.id == debt_id).first()
    if not d:
        return None
    
    return Debt(
        id=d.id,
        name=d.name,
        amount=d.amount,
        direction=d.direction,
        note=d.note,
        due_date=d.due_date,
        status=d.status
    )


def create_debt(db: Session, debt: Debt) -> Debt:
    db_debt = DebtModel(
        id=debt.id,
        name=debt.name,
        amount=debt.amount,
        direction=debt.direction,
        note=debt.note,
        due_date=debt.due_date,
        status=debt.status
    )
    db.add(db_debt)
    db.commit()
    db.refresh(db_debt)
    return debt


def update_debt(db: Session, debt_id: str, updates: dict) -> Debt | None:
    db_debt = db.query(DebtModel).filter(DebtModel.id == debt_id).first()
    if not db_debt:
        return None
    
    for key, value in updates.items():
        setattr(db_debt, key, value)
    
    db.commit()
    db.refresh(db_debt)
    
    return Debt(
        id=db_debt.id,
        name=db_debt.name,
        amount=db_debt.amount,
        direction=db_debt.direction,
        note=db_debt.note,
        due_date=db_debt.due_date,
        status=db_debt.status
    )


def delete_debt(db: Session, debt_id: str) -> bool:
    db_debt = db.query(DebtModel).filter(DebtModel.id == debt_id).first()
    if not db_debt:
        return False
    
    db.delete(db_debt)
    db.commit()
    return True


# ── Баланс ──

def get_balance(db: Session) -> Balance:
    total_income = db.query(TransactionModel).filter(
        TransactionModel.transaction_type == "income"
    ).with_entities(
        func.coalesce(func.sum(TransactionModel.amount), 0)
    ).scalar()
    
    total_expense = db.query(TransactionModel).filter(
        TransactionModel.transaction_type == "expense"
    ).with_entities(
        func.coalesce(func.sum(TransactionModel.amount), 0)
    ).scalar()
    
    return Balance(
        total_income=float(total_income),
        total_expense=float(total_expense),
        balance=float(total_income - total_expense)
    )
