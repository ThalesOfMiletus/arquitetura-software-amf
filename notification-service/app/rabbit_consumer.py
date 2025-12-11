# app/rabbit_consumer.py
import os
import json
import asyncio
import aio_pika
from aio_pika.exceptions import AMQPConnectionError

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
NOTIFICATION_QUEUE = os.getenv("NOTIFICATION_QUEUE", "order-notifications")


async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        body = message.body.decode("utf-8")
        data = json.loads(body)
        client_name = data.get("client_name", "Cliente")
        order_id = data.get("order_id", "")
        print(f"{client_name}, seu pedido {order_id} foi PAGO com sucesso e será despachado em breve")


async def consume_notifications():
    # loop de retry até o RabbitMQ ficar disponível
    while True:
        try:
            print("[notification-service] Tentando conectar ao RabbitMQ...")
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            channel = await connection.channel()
            queue = await channel.declare_queue(NOTIFICATION_QUEUE, durable=True)
            await queue.consume(handle_message)
            print("[notification-service] Consumidor de notificações iniciado")
            return connection  # retorna conexão viva
        except AMQPConnectionError:
            print("[notification-service] RabbitMQ indisponível, tentando novamente em 5s...")
            await asyncio.sleep(5)
