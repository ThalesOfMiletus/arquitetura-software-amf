import json
import os
import time
from typing import Any, Dict, Optional

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable


class OrderEventProducer:
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        retries: int = 5,
        backoff_seconds: float = 1.0,
        connect_retries: int = 60,          # ✅ novo
        connect_backoff_seconds: float = 1.0, # ✅ novo
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = topic or os.getenv("KAFKA_TOPIC", "order-payments")
        self.retries = retries
        self.backoff_seconds = backoff_seconds

        # ✅ espera o Kafka ficar disponível antes de criar o producer
        self._wait_for_kafka(
            self.bootstrap_servers,
            retries=connect_retries,
            backoff_seconds=connect_backoff_seconds,
        )

        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            acks="all",
            retries=0,  # a gente controla retry aqui
            linger_ms=10,
        )

    @staticmethod
    def _wait_for_kafka(bootstrap_servers: str, *, retries: int, backoff_seconds: float) -> None:
        last_err: Exception | None = None
        servers = bootstrap_servers.split(",")

        for attempt in range(1, retries + 1):
            try:
                # tenta conectar e fecha; se conectar, tá ok
                p = KafkaProducer(bootstrap_servers=servers)
                p.close()
                print(f"[kafka] conectado em {bootstrap_servers}")
                return
            except NoBrokersAvailable as e:
                last_err = e
                sleep_s = min(backoff_seconds * attempt, 10)
                print(f"[kafka] ainda não pronto ({attempt}/{retries}). retry em {sleep_s:.1f}s...")
                time.sleep(sleep_s)
            except Exception as e:
                last_err = e
                sleep_s = min(backoff_seconds * attempt, 10)
                print(f"[kafka] erro ao conectar ({attempt}/{retries}): {e!r}. retry em {sleep_s:.1f}s...")
                time.sleep(sleep_s)

        raise RuntimeError(f"Kafka não ficou disponível em {bootstrap_servers}. Último erro: {last_err!r}")

    def close(self) -> None:
        try:
            self._producer.flush(timeout=5)
        finally:
            self._producer.close(timeout=5)

    def send(self, payload: Dict[str, Any]) -> None:
        last_err: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                fut = self._producer.send(self.topic, payload)
                fut.get(timeout=10)
                return
            except Exception as e:
                last_err = e
                time.sleep(self.backoff_seconds * attempt)
        if last_err:
            raise last_err
