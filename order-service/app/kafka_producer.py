import json
import os
import time
from typing import Any, Dict, Optional

from kafka import KafkaProducer

class OrderEventProducer:
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        retries: int = 5,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = topic or os.getenv("KAFKA_TOPIC", "order-payments")
        self.retries = retries
        self.backoff_seconds = backoff_seconds

        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            acks="all",
            retries=0,  # a gente controla retry aqui
            linger_ms=10,
        )

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
        