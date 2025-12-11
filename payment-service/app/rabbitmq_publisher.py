# app/rabbit_publisher.py
import os
import json
import aio_pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
NOTIFICATION_QUEUE = os.getenv("NOTIFICATION_QUEUE", "order-notifications")

_connection = None
_channel = None
_queue = None


async def get_channel():
    global _connection, _channel, _queue
    if _connection is None:
        _connection = await aio_pika.connect_robust(RABBITMQ_URL)
        _channel = await _connection.channel()
        _queue = await _channel.declare_queue(NOTIFICATION_QUEUE, durable=True)
    return _channel, _queue


async def send_notification(client_name: str, order_id: str):
    channel, queue = await get_channel()

    body = json.dumps(
        {
            "client_name": client_name,
            "order_id": order_id,
        }
    ).encode("utf-8")

    message = aio_pika.Message(body=body)
    await channel.default_exchange.publish(message, routing_key=queue.name)
    print(f"[payment-service] Notificação enviada para RabbitMQ: {client_name} / {order_id}")
