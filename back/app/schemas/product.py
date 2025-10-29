from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Product(BaseModel):
    id: str
    name: str
    category: str
    min_stick: int
    optimal_stock: int


class ProductBase(BaseModel):
    id: str = Field(..., description="Артикул / SKU, PK в БД")
    name: str = Field(..., description="Название товара")
    category: Optional[str] = Field(None, description="Категория товара")
    min_stock: int = Field(..., description="Минимальный безопасный остаток")
    optimal_stock: int = Field(..., description="Целевой запас")


class ProductCreate(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    min_stock: int = 10
    optimal_stock: int = 100


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    min_stock: Optional[int] = None
    optimal_stock: Optional[int] = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
