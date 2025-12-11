import os
import json
import logging
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
PAYMENT_TOPIC = os.getenv("PAYMENT_TOPIC", "order-payments")

_producer: AIOKafkaProducer | None = None


async def get_producer() -> AIOKafkaProducer:
    """
    Retorna um produtor Kafka singleton.
    """
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
        logger.info("AIOKafkaProducer iniciado em %s", KAFKA_BOOTSTRAP)
    return _producer


async def send_order_payment_event(event: dict):
    """
    Envia evento de pagamento para o tópico configurado.
    Rodar isso em background pra não travar o request principal.
    """
    try:
        producer = await get_producer()
        await producer.send_and_wait(PAYMENT_TOPIC, event)
        logger.info("Evento de pagamento enviado para Kafka: %s", event)
    except Exception as e:
        logger.exception("Erro ao enviar evento para Kafka: %s", e)
