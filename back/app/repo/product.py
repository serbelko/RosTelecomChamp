# app/repo/product.py

from typing import Dict, Sequence, Set, List
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_products_exist(self, products: Dict[str, str]) -> None:
        """
        products: {product_id: product_name}
        Гарантирует, что все SKU есть в таблице products.
        Если товар уже есть — не трогаем.
        Если нет — вставляем.
        Гонок не боимся: используем ON CONFLICT DO NOTHING.
        """

        if not products:
            return

        # Строим массив словарей для bulk insert
        rows = [
            {
                "id": pid,
                "name": pname or pid,
                "category": None,
                "min_stock": 10,
                "optimal_stock": 100,
            }
            for pid, pname in products.items()
        ]

        stmt = (
            insert(Product)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[Product.id])
        )

        await self.session.execute(stmt)
        # flush чтобы запись попала в транзакцию
        await self.session.flush()
    
    async def list_all(self) -> List[Product]:
        """
        Вернёт все продукты из таблицы products.
        В реальном проекте сюда можно добавить фильтрацию по категориям.
        """
        stmt = select(Product)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
