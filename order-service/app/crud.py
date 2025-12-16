from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from pymongo.collection import Collection
from pymongo import DESCENDING

def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    # total_amount pode ser string/float; normalize pra string pra depois virar Decimal no schema
    if "total_amount" in doc and not isinstance(doc["total_amount"], str):
        doc["total_amount"] = str(doc["total_amount"])
    return doc

def create_order(
    orders: Collection,
    *,
    client_id: int,
    client_name: Optional[str],
    items: List[Dict[str, Any]],
    total_amount: Decimal,
) -> Dict[str, Any]:
    doc = {
        "client_id": client_id,
        "client_name": client_name,
        "items": items,
        "total_amount": str(total_amount),
        "status": "CREATED",
        "created_at": datetime.utcnow(),
    }
    res = orders.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize(doc)

def list_orders(orders: Collection, *, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
    cursor = orders.find().sort("created_at", DESCENDING).skip(skip).limit(limit)
    return [_serialize(d) for d in cursor]

def get_order(orders: Collection, order_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(order_id)
    except Exception:
        return None
    doc = orders.find_one({"_id": oid})
    return _serialize(doc) if doc else None
