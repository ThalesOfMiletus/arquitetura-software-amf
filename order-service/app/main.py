import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_database, get_orders_collection
from app.kafka_producer import OrderEventProducer

producer = OrderEventProducer()


# -----------------------
# Schemas (simples e diretos)
# -----------------------
class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=0)

class PaymentIn(BaseModel):
    method: str
    card_last4: Optional[str] = None

class OrderCreate(BaseModel):
    client_id: int
    client_name: str
    items: List[OrderItemIn] = Field(min_length=1)
    payment: PaymentIn

class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: int
    client_name: str
    items: List[Dict[str, Any]]
    total_amount: str
    status: str
    created_at: datetime


# -----------------------
# Helpers
# -----------------------
def _money2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _to_mongo_safe(value: Any) -> Any:
    """
    Mongo (BSON) não aceita Decimal. Aqui convertemos recursivamente.
    - Decimal -> str (mais seguro pra dinheiro do que float)
    - dict/list -> recursivo
    """
    if isinstance(value, Decimal):
        return str(_money2(value))
    if isinstance(value, list):
        return [_to_mongo_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_mongo_safe(v) for k, v in value.items()}
    return value

def _normalize_order_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza o documento vindo do Mongo para resposta JSON:
    - _id -> id (str)
    """
    if not doc:
        return doc
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


# -----------------------
# App
# -----------------------
app = FastAPI(title="order-service", version="1.0.0")

db = get_database()
orders_collection = get_orders_collection(db)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, background_tasks: BackgroundTasks):
    # 1) calcula total com Decimal (sem float)
    total = Decimal("0.00")
    items: List[Dict[str, Any]] = []

    for it in payload.items:
        line_total = _money2(Decimal(str(it.price)) * it.quantity)
        total += line_total

        # IMPORTANTe: não guardar Decimal no Mongo -> salva como string
        items.append(
            {
                "product_id": it.product_id,
                "quantity": it.quantity,
                "price": str(_money2(Decimal(str(it.price)))),
            }
        )

    total = _money2(total)

    # 2) monta doc do pedido
    order_doc: Dict[str, Any] = {
        "client_id": payload.client_id,
        "client_name": payload.client_name,
        "items": items,
        "total_amount": str(total),
        "status": "CREATED",
        "created_at": datetime.utcnow(),
    }

    # 3) garante BSON-safe (caso algum Decimal escape)
    order_doc = _to_mongo_safe(order_doc)

    # 4) salva
    result = orders_collection.insert_one(order_doc)
    order_id = str(result.inserted_id)

    # 5) dispara evento pro Kafka (pra payment-service consumir)
    event = {
        "order_id": order_id,
        "client_id": payload.client_id,
        "client_name": payload.client_name,
        "total_amount": str(total),  # padrão
        "amount": str(total),        # compat (se teu consumer aceitar)
        "payment": payload.payment.model_dump(),
        "created_at": order_doc["created_at"].isoformat(),
        "status": "CREATED",
    }
    background_tasks.add_task(producer.send, event)

    # 6) resposta
    return OrderOut(
        id=order_id,
        client_id=payload.client_id,
        client_name=payload.client_name,
        items=items,
        total_amount=str(total),
        status="CREATED",
        created_at=order_doc["created_at"],
    )


@app.get("/orders")
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    docs = list(orders_collection.find().skip(skip).limit(limit))
    return [_normalize_order_doc(d) for d in docs]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="order_id inválido")

    doc = orders_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    return _normalize_order_doc(doc)
