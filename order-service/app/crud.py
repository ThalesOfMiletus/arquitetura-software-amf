# app/crud.py
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from . import schemas

COLLECTION_NAME = "orders"


def _calc_total(items: List[schemas.OrderItem]) -> Decimal:
    total = Decimal("0.00")
    for item in items:
        total += Decimal(str(item.price)) * item.quantity
    return total


async def create_order(db, payload: schemas.OrderCreate) -> dict:
    total_amount = _calc_total(payload.items)
    order_id = str(uuid4())
    now = datetime.utcnow()

    items_serialized = []
    for item in payload.items:
        items_serialized.append(
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": float(item.price),
            }
        )

    order_doc = {
        "id": order_id,
        "client_id": payload.client_id,
        "client_name": payload.client_name,        # <- aqui
        "items": items_serialized,
        "total_amount": float(total_amount),
        "status": "PENDING",
        "created_at": now,
        "payment": payload.payment.model_dump(),
    }

    await db[COLLECTION_NAME].insert_one(order_doc)
    order_doc.pop("_id", None)
    return order_doc


async def list_orders(db) -> List[dict]:
    cursor = db[COLLECTION_NAME].find({})
    orders = []
    async for doc in cursor:
        doc.pop("_id", None)
        orders.append(doc)
    return orders


async def get_order(db, order_id: str) -> Optional[dict]:
    doc = await db[COLLECTION_NAME].find_one({"id": order_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return doc
