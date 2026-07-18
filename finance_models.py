from __future__ import annotations
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Float, Text, Enum as SQLEnum
from database import Base
from typing import Optional, Literal
from enum import Enum
import uuid


# ── SQLAlchemy ORM модели ──

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class TransactionCategory(str, Enum):
    work = "work"
    food = "food"
    housing = "housing"
    transport = "transport"
    health = "health"
    education = "education"
    entertainment = "entertainment"
    other = "other"


class TransactionModel(Base):
    """SQLAlchemy ORM модель для транзакций"""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    description = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    category = Column(SQLEnum(TransactionCategory), nullable=False)
    date = Column(String(10), nullable=False)  # ISO YYYY-MM-DD


class DebtDirection(str, Enum):
    owe = "owe"      # я должен
    owed = "owed"    # мне должны


class DebtStatus(str, Enum):
    active = "active"
    paid = "paid"


class DebtModel(Base):
    """SQLAlchemy ORM модель для долгов"""
    __tablename__ = "debts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    direction = Column(SQLEnum(DebtDirection), nullable=False)
    note = Column(Text, nullable=True)
    due_date = Column(String(10), nullable=True)  # ISO YYYY-MM-DD
    status = Column(SQLEnum(DebtStatus), default=DebtStatus.active)


# ── Pydantic схемы для API ──

# Переиспользуем ORM Enums для Pydantic
TransactionTypePydantic = TransactionType
TransactionCategoryPydantic = TransactionCategory


class TransactionBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    category: TransactionCategory
    date: str  # ISO YYYY-MM-DD


class Transaction(TransactionBase):
    id: str

    class Config:
        from_attributes = True


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[TransactionType] = None
    category: Optional[TransactionCategory] = None
    date: Optional[str] = None


# Переиспользуем ORM Enums для Pydantic
DebtDirectionPydantic = DebtDirection
DebtStatusPydantic = DebtStatus


class DebtBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    direction: DebtDirection
    note: Optional[str] = None
    due_date: Optional[str] = None  # ISO YYYY-MM-DD
    status: DebtStatus = DebtStatus.active


class Debt(DebtBase):
    id: str

    class Config:
        from_attributes = True


class DebtCreate(DebtBase):
    pass


class DebtUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    direction: Optional[DebtDirection] = None
    note: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[DebtStatus] = None


class Balance(BaseModel):
    total_income: float
    total_expense: float
    balance: float
