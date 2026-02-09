from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String, Integer, DateTime

class OrderStatus(str, Enum):
    NEW = "NEW"
    REJECTED = "REJECTED"
    AWAITING_PRICE = "AWAITING_PRICE"
    PRICE_SENT = "PRICE_SENT"
    PRICE_ACCEPTED = "PRICE_ACCEPTED"
    PRICE_REJECTED = "PRICE_REJECTED"
    COMPLETED = "COMPLETED"

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # SQLModel doesn't support `index=True` together with `sa_column=...`.
    # Put the index flag on the SQLAlchemy Column instead.
    token: str = Field(sa_column=Column(String(64), unique=True, nullable=False, index=True))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

    customer_name: str = Field(sa_column=Column(String(200), nullable=False))
    customer_email: str = Field(sa_column=Column(String(320), nullable=False))
    description: str = Field(sa_column=Column(String(4000), nullable=False))
    model_link: Optional[str] = Field(default=None, sa_column=Column(String(2000), nullable=True))

    # Store relative path like "uploads/<token>/<filename>"
    image_path: Optional[str] = Field(default=None, sa_column=Column(String(2000), nullable=True))

    status: OrderStatus = Field(default=OrderStatus.NEW, sa_column=Column(String(32), nullable=False))

    admin_note: Optional[str] = Field(default=None, sa_column=Column(String(2000), nullable=True))

    price_cents: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    currency: str = Field(default="EUR", sa_column=Column(String(8), nullable=False))

    customer_decision_note: Optional[str] = Field(default=None, sa_column=Column(String(2000), nullable=True))
