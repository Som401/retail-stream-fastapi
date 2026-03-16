"""Application configuration (env vars with defaults for local dev)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from environment (e.g. docker-compose)."""

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "retail"
    postgres_password: str = "retail"
    postgres_db: str = "retail"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl_seconds: int = 300  # 5 minutes

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_order_topic: str = "order-events"

    # Observability
    enable_metrics: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config = {"env_prefix": "APP_", "extra": "ignore"}


settings = Settings()
