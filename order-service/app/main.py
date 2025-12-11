from fastapi import FastAPI, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime

from bson import ObjectId

from .database import orders_collection
from .schemas import OrderCreate, OrderResponse
from .kafka_producer import send_order_payment_event

app = FastAPI(
    title="order-service",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


def _doc_to_order_response(doc) -> OrderResponse:
    """
    Converte um documento Mongo em OrderResponse.
    """
    return OrderResponse(
        id=str(doc["_id"]),
        client_id=doc["client_id"],
        client_name=doc["client_name"],
        items=doc["items"],
        total_amount=doc["total_amount"],
        status=doc["status"],
        created_at=doc["created_at"],
        payment=doc["payment"],
    )


@app.post("/orders", response_model=OrderResponse)
async def create_order(order_in: OrderCreate, background_tasks: BackgroundTasks):
    """
    Cria um pedido:
    - calcula total
    - salva no Mongo
    - dispara evento pro Kafka em background
    """
    # 1) calcula total
    total_amount = sum(item.quantity * item.price for item in order_in.items)

    # 2) monta documento
    now = datetime.utcnow()
    order_doc = {
        "client_id": order_in.client_id,
        "client_name": order_in.client_name,
        "items": [item.model_dump() for item in order_in.items],
        "total_amount": float(total_amount),
        "status": "PENDING",
        "created_at": now,
        "payment": order_in.payment.model_dump(),
    }

    # 3) insere no Mongo
    result = await orders_collection.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id

    # 4) prepara evento pro Kafka
    event_payload = {
        "order_id": str(result.inserted_id),
        "client_id": order_doc["client_id"],
        "client_name": order_doc["client_name"],
        "total_amount": order_doc["total_amount"],
        "payment": order_doc["payment"],
        "items": order_doc["items"],
        "status": order_doc["status"],
        "created_at": order_doc["created_at"].isoformat(),
    }

    # 5) dispara envio pro Kafka em background (não bloqueia a resposta)
    background_tasks.add_task(send_order_payment_event, event_payload)

    # 6) retorna o pedido
    return _doc_to_order_response(order_doc)


@app.get("/orders", response_model=List[OrderResponse])
async def list_orders():
    """
    Lista todos os pedidos.
    """
    cursor = orders_collection.find({})
    results: List[OrderResponse] = []
    async for doc in cursor:
        results.append(_doc_to_order_response(doc))
    return results


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """
    Busca pedido pelo ID (string de ObjectId).
    """
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")

    doc = await orders_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return _doc_to_order_response(doc)
