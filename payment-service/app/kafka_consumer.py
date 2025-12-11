import os
import json
import asyncio
import logging
from datetime import datetime

from aiokafka import AIOKafkaConsumer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Payment
from .rabbitmq_publisher import send_notification as publish_notification

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
PAYMENT_TOPIC = os.getenv("PAYMENT_TOPIC", "order-payments")


async def process_event(event: dict):
    """
    Recebe o evento do order-service e cria um Payment + envia notificação.
    """
    logger.info("[payment-service] Processando evento: %s", event)

    order_id = event.get("order_id")
    client_id = event.get("client_id")
    client_name = event.get("client_name")
    total_amount = event.get("total_amount") or event.get("amount")

    payment_info = event.get("payment") or {}
    method = payment_info.get("method")
    card_last_digits = payment_info.get("card_last_digits")

    if not order_id or client_id is None or client_name is None or total_amount is None:
        logger.error("[payment-service] Evento inválido, campos faltando: %s", event)
        return

    db: Session = SessionLocal()
    try:
        payment = Payment(
            order_id=order_id,
            client_id=client_id,
            client_name=client_name,
            amount=float(total_amount),
            method=method or "unknown",
            card_last_digits=card_last_digits,
            status="PAID",
            created_at=datetime.utcnow(),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        msg = f"{client_name}, seu pedido {order_id} foi PAGO com sucesso e será despachado em breve"
        publish_notification(msg)
        logger.info(
            "[payment-service] Payment criado id=%s e notificação enviada",
            payment.id,
        )

    except Exception as e:
        db.rollback()
        logger.exception("[payment-service] Erro ao salvar pagamento: %s", e)
    finally:
        db.close()


async def consume_payments():
    """
    Consumer Kafka que fica ouvindo o tópico de pagamentos.
    """
    logger.info(
        "[payment-service] Iniciando consumidor Kafka em %s, tópico %s",
        KAFKA_BOOTSTRAP,
        PAYMENT_TOPIC,
    )

    consumer = AIOKafkaConsumer(
        PAYMENT_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )

    await consumer.start()
    try:
        async for msg in consumer:
            event = msg.value
            await process_event(event)
    finally:
        await consumer.stop()
        logger.info("[payment-service] Consumer Kafka parado")
