import asyncio
import json
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaConsumer
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Payment, PaymentStatus
from app.rabbitmq_publisher import send_notification

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "order-payments")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "payment-service")


def _to_decimal_amount(val: Any) -> Decimal:
    """Converte valores (str/float/int/Decimal) para Decimal com 2 casas."""
    if val is None:
        raise ValueError("amount ausente")

    try:
        d = Decimal(str(val))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"amount inválido: {val}") from e

    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _extract_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Compatibilidade com variações de evento
    order_id = payload.get("order_id") or payload.get("id") or payload.get("orderId")
    if not order_id:
        raise ValueError("order_id ausente")

    client_id = payload.get("client_id") or payload.get("clientId")
    client_name = payload.get("client_name") or payload.get("clientName")

    raw_amount = payload.get("total_amount")
    if raw_amount is None:
        raw_amount = payload.get("amount")

    amount = _to_decimal_amount(raw_amount)

    payment_type = payload.get("payment_type")
    if not payment_type and isinstance(payload.get("payment"), dict):
        payment_type = payload["payment"].get("type")

    payment_type = payment_type or "CREDIT_CARD"

    status = payload.get("payment_status") or payload.get("status") or PaymentStatus.PAID
    # Normaliza string
    status = str(status).upper()
    if status not in {"PAID", "FAILED", "PENDING"}:
        status = "PAID"

    return {
        "order_id": str(order_id),
        "client_id": int(client_id) if client_id is not None else None,
        "client_name": str(client_name) if client_name is not None else None,
        "amount": amount,
        "payment_type": str(payment_type),
        "status": status,
    }


def _save_payment(
    *,
    order_id: str,
    client_id: Optional[int],
    client_name: Optional[str],
    amount: Decimal,
    payment_type: str,
    status: str,
) -> Payment:
    """Cria (ou retorna existente) garantindo idempotência por order_id."""
    db = SessionLocal()
    try:
        existing = db.query(Payment).filter(Payment.order_id == order_id).first()
        if existing:
            return existing

        payment = Payment(
            order_id=order_id,
            client_id=client_id,
            client_name=client_name,
            amount=amount,
            payment_type=payment_type,
            status=PaymentStatus(status),
        )
        db.add(payment)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Se outro consumer/processo inseriu antes
            existing = db.query(Payment).filter(Payment.order_id == order_id).first()
            if existing:
                return existing
            raise
        db.refresh(payment)
        return payment
    finally:
        db.close()


async def consume_forever() -> None:
    """Loop principal do consumer (para rodar em background task)."""
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        enable_auto_commit=True,
        value_deserializer=lambda v: v,
    )

    await consumer.start()
    try:
        async for msg in consumer:
            try:
                raw = msg.value.decode("utf-8") if isinstance(msg.value, (bytes, bytearray)) else str(msg.value)
                payload = json.loads(raw)

                fields = _extract_fields(payload)
                payment = _save_payment(**fields)

                # Publica notificação (await!)
                await send_notification(
                    fields.get("client_name"),
                    fields["order_id"],
                    status=str(payment.status.value),
                    amount=str(payment.amount),
                )

            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Evita matar o consumer por uma mensagem ruim
                print(f"[payment-service] Erro processando msg Kafka: {e}")

    finally:
        await consumer.stop()
