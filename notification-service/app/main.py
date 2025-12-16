import asyncio
import json
import os
from datetime import datetime

import aio_pika


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
NOTIFICATION_QUEUE = os.getenv("NOTIFICATION_QUEUE", "order-notifications")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


async def run_consumer() -> None:
    # connect_robust reconecta automaticamente
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        # evita sobrecarga: processa 10 por vez
        await channel.set_qos(prefetch_count=10)

        queue = await channel.declare_queue(NOTIFICATION_QUEUE, durable=True)

        print(f"[notification-service] conectado em {RABBITMQ_URL} | fila='{queue.name}'")
        print("[notification-service] aguardando notificações... (CTRL+C para sair)")

        async with queue.iterator() as qiter:
            async for message in qiter:
                async with message.process(requeue=False):
                    try:
                        payload = json.loads(message.body.decode("utf-8"))
                    except Exception:
                        payload = {"raw": message.body.decode("utf-8", errors="replace")}

                    client_name = payload.get("client_name", "?")
                    order_id = payload.get("order_id", "?")

                    # Como o payment-service publica isso após persistir PAID,
                    # todo evento aqui representa "pagamento concluído".
                    print(f"[{_ts()}] ✅ Pagamento concluído | cliente='{client_name}' | pedido='{order_id}' | payload={payload}")


async def main() -> None:
    # loop simples de resiliência: caso algo dê errado, tenta novamente
    backoff = 1
    while True:
        try:
            await run_consumer()
            backoff = 1
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[notification-service] erro: {e!r}. Tentando reconectar em {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[notification-service] encerrado.")
