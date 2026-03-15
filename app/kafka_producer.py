"""Kafka producer — publishes order events to the order-events topic."""
import json

from aiokafka import AIOKafkaProducer

from app.config import settings

_producer: AIOKafkaProducer | None = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
    return _producer


async def close_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None


async def publish_order(order: dict) -> None:
    """Publish an order event to Kafka. Non-blocking for the API caller."""
    producer = await get_producer()
    await producer.send_and_wait(settings.kafka_order_topic, order)
