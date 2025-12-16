# app/kafka_producer.py
import os
import json
import asyncio
import logging
from typing import Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
PAYMENT_TOPIC = os.getenv("PAYMENT_TOPIC", "order-payments")

PRODUCER_START_MAX_ATTEMPTS = int(os.getenv("KAFKA_START_MAX_ATTEMPTS", "10"))
PRODUCER_START_BASE_DELAY = float(os.getenv("KAFKA_START_BASE_DELAY", "1.0"))
SEND_TIMEOUT_SECONDS = float(os.getenv("KAFKA_SEND_TIMEOUT_SECONDS", "5.0"))

_producer: Optional[AIOKafkaProducer] = None
_lock = asyncio.Lock()


async def _start_producer_with_retry(producer: AIOKafkaProducer) -> None:
    last_exc: Exception | None = None

    for attempt in range(1, PRODUCER_START_MAX_ATTEMPTS + 1):
        try:
            await producer.start()
            logger.info("Kafka producer iniciado em %s", KAFKA_BOOTSTRAP)
            return
        except Exception as e:
            last_exc = e
            delay = min(PRODUCER_START_BASE_DELAY * attempt, 10.0)
            logger.warning(
                "Kafka indisponível (tentativa %s/%s): %s | retry em %.1fs",
                attempt, PRODUCER_START_MAX_ATTEMPTS, repr(e), delay
            )
            await asyncio.sleep(delay)

    raise RuntimeError(
        f"Kafka não ficou disponível após {PRODUCER_START_MAX_ATTEMPTS} tentativas"
    ) from last_exc


async def get_producer() -> AIOKafkaProducer:
    global _producer

    async with _lock:
        if _producer is not None:
            return _producer

        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            # configs compatíveis (e seguras)
            acks="all",
            request_timeout_ms=5000,
            linger_ms=5,
        )

        await _start_producer_with_retry(producer)
        _producer = producer
        return _producer


async def send_order_payment_event(event: dict) -> None:
    producer = await get_producer()

    try:
        await asyncio.wait_for(
            producer.send_and_wait(PAYMENT_TOPIC, event),
            timeout=SEND_TIMEOUT_SECONDS
        )
        logger.info("Evento enviado para Kafka (topic=%s): %s", PAYMENT_TOPIC, event)

    except asyncio.TimeoutError:
        logger.error("Timeout ao enviar evento para Kafka (topic=%s): %s", PAYMENT_TOPIC, event)

    except KafkaError as e:
        logger.exception("Erro Kafka ao enviar evento (topic=%s): %s | event=%s", PAYMENT_TOPIC, e, event)

    except Exception as e:
        logger.exception("Erro inesperado ao enviar evento: %s | event=%s", e, event)


async def close_producer() -> None:
    global _producer

    async with _lock:
        if _producer is not None:
            try:
                await _producer.stop()
                logger.info("Kafka producer finalizado")
            finally:
                _producer = None
