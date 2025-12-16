import json
import os
from datetime import datetime
from typing import Optional

import aio_pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_NAME = os.getenv("RABBITMQ_QUEUE", "payment-notifications")


async def send_notification(
    client_name: Optional[str],
    order_id: str,
    status: str = "PAID",
    amount: Optional[str] = None,
) -> None:
    """Publica uma notificação simples em RabbitMQ.

    - Usa connection robust
    - Declara fila (durável)
    - Publica JSON (persistent)
    """
    payload = {
        "event": "payment.updated",
        "order_id": order_id,
        "client_name": client_name,
        "status": status,
        "amount": amount,
        "created_at": datetime.utcnow().isoformat(),
    }

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    try:
        channel = await connection.channel()
        await channel.declare_queue(QUEUE_NAME, durable=True)

        message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        # Default exchange publishes direct to queue routing key
        await channel.default_exchange.publish(message, routing_key=QUEUE_NAME)
    finally:
        await connection.close()
