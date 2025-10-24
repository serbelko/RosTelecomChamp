from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    Date,
    DECIMAL,
    TIMESTAMP,
    ForeignKey,
    func,
    DateTime,
    types
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)

from sqlalchemy_serializer import SerializerMixin 


class Base(DeclarativeBase):
    pass

class Users(Base, SerializerMixin):
    __tablename__ = 'users'
    
    id: Mapped[uuid.UUID] = mapped_column(types.UUID, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Robots(Base, SerializerMixin):
    __tablename__ = 'robots'

    id: Mapped[uuid.UUID] = mapped_column(types.UUID, primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    battery_level: Mapped[int] = mapped_column(Integer)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    current_zone: Mapped[str] = mapped_column(String(10))
    current_row: Mapped[int] = mapped_column(Integer)
    current_shelf: Mapped[int] = mapped_column(Integer)

class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    min_stock: Mapped[int] = mapped_column(Integer, default=10)
    optimal_stock: Mapped[int] = mapped_column(Integer, default=100)

    # связи
    inventory_records: Mapped[List[InventoryHistory]] = relationship(
        back_populates="product"
    )
    predictions: Mapped[List[AiPrediction]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<Product(id='{self.id}', name='{self.name}')>"


class InventoryHistory(Base):
    __tablename__ = "inventory_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    robot_id: Mapped[Optional[str]] = mapped_column(ForeignKey("robots.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[str] = mapped_column(String(10), nullable=False)
    row_number: Mapped[Optional[int]] = mapped_column(Integer)
    shelf_number: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(String(50))
    scanned_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )

    product: Mapped[Product] = relationship(back_populates="inventory_records")

    def __repr__(self) -> str:
        return f"<InventoryHistory(id={self.id}, product_id='{self.product_id}', status='{self.status}')>"


class AiPrediction(Base):
    __tablename__ = "ai_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_until_stockout: Mapped[Optional[int]] = mapped_column(Integer)
    recommended_order: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_score: Mapped[Optional[float]] = mapped_column(DECIMAL(3, 2))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )

    product: Mapped[Product] = relationship(back_populates="predictions")

    def __repr__(self) -> str:
        return (
            f"<AiPrediction(product_id='{self.product_id}', "
            f"days_until_stockout={self.days_until_stockout}, "
            f"confidence={self.confidence_score})>"
        )