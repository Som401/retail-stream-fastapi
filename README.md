# Retail Stream API

Cloud Administration course project — a high-throughput retail data API built with **FastAPI**, **Redis**, **PostgreSQL**, and **Kafka**, deployed on **Google Cloud Platform** using a distributed multi-VM architecture.

**Achieved: ~6,000 req/s at <1% error rate** across 3 API VMs behind a GCP HTTP Load Balancer.

---

## Architecture

```
Internet
    │
    ▼
GCP HTTP(S) Load Balancer  (34.95.108.94)
    │
    ├──▶ API VM 1  e2-standard-4  →  nginx → app1 / app2 / app3
    ├──▶ API VM 2  e2-standard-4  →  nginx → app1 / app2 / app3
    └──▶ API VM 3  e2-standard-4  →  nginx → app1 / app2 / app3
                        │
                        ▼ (public static IP)
              Data VM  e2-standard-8
              PostgreSQL │ Redis │ Kafka │ Worker

k6 VM  e2-standard-4  ──▶  GCP LB external IP
```

| Layer | Machine | Role |
|-------|---------|------|
| GCP HTTP LB | managed | distributes traffic across API VMs |
| API VMs × 3 | `e2-standard-4` | nginx → 3 FastAPI containers × 2 workers each |
| Data VM | `e2-standard-8` | PostgreSQL, Redis, Kafka, consumer worker |
| k6 VM | `e2-standard-4` | load generation |

---

## Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI + Uvicorn |
| Caching | Redis (connection pool, orjson, 1h TTL) |
| Database | PostgreSQL + asyncpg (async pool) |
| Messaging | Kafka + AIOKafka |
| Load Balancer | Nginx (per API VM) + GCP HTTP LB |
| Monitoring | Prometheus + Grafana (on Data VM) |
| Load Testing | k6 (constant-arrival-rate) |
| Containerisation | Docker + Docker Compose |
| Infra | GCP Compute Engine, Managed Instance Group |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | liveness check |
| `GET` | `/ready` | readiness (DB + Redis) |
| `GET` | `/products/{stock_code}` | Redis cache-aside → PostgreSQL |
| `POST` | `/orders` | async via Kafka → consumer → PostgreSQL |
| `GET` | `/products/top` | top products by revenue |
| `GET` | `/orders/invoice/{id}` | order lines by invoice |
| `GET` | `/orders/customer/{id}` | order lines by customer |
| `GET` | `/orders/country/{name}` | order lines by country |

---

## Local Development

```bash
# Start all services
docker compose up -d --build

# Load CSV data into PostgreSQL
docker compose run --rm app1 python scripts/load_data.py

# Health check
curl http://localhost/health

# Get a product (cache-aside)
curl http://localhost/products/85048
```

Place `online_retail_all.csv` in the project root before loading data.

---

## GCP Deployment

Full step-by-step guide: **[docs/GCP_SCALED_SETUP.md](docs/GCP_SCALED_SETUP.md)**

### Quick summary (2 GCP accounts)

**Account A — Data VM + k6 VM:**
```bash
# Start data services
docker compose -f docker-compose.data.yaml up -d --build
docker compose -f docker-compose.data.yaml run --rm loader
```

**Account B — API VMs (Managed Instance Group):**
```bash
# Template + MIG (startup script auto-installs Docker + starts API stack)
gcloud compute instance-templates create retail-api-template \
  --machine-type=e2-standard-4 \
  --metadata-from-file startup-script=scripts/startup-api-vm.sh

gcloud compute instance-groups managed create retail-api-mig \
  --template=retail-api-template --size=3 --zone=us-central1-a
```

---

## Load Testing

Run from k6 VM against the LB IP:

```bash
# Stable 6000 req/s test (60 seconds)
TARGET_RPS=6000 k6 run --env BASE_URL=http://LB_IP scripts/stress_test_max_rps.js

# Ramp to find max throughput
k6 run --env BASE_URL=http://LB_IP scripts/stress_test_find_max.js
```

---

## Performance Results

| Target RPS | Actual RPS | Error Rate | p95 Latency |
|-----------|-----------|------------|-------------|
| 6,000 | ~5,983 | 0.003% | 75ms |
| 6,500 | ~6,498 | 29% | 238ms |
| 7,000 | ~6,686 | 40% | 710ms |

**Stable ceiling: 6,000 req/s at <1% errors** with 3 × `e2-standard-4` API VMs.

### Bottleneck identified
At >6k req/s the API containers (not Data VM) are CPU-saturated (~97% per container).
Redis hit rate was near-perfect (`1,234,506 hits / 1 miss`).
Adding more API VMs or accounts scales linearly.

---

## Configuration

All settings via environment variables (prefix `APP_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_POSTGRES_HOST` | `localhost` | Postgres host |
| `APP_REDIS_HOST` | `localhost` | Redis host |
| `APP_KAFKA_BOOTSTRAP_SERVERS` | `localhost:29092` | Kafka brokers |
| `APP_CACHE_TTL_SECONDS` | `3600` | Redis TTL |
| `APP_ENABLE_METRICS` | `true` | Prometheus metrics |
| `UVICORN_WORKERS` | `1` | Workers per container |

---

## Project Files

```
├── app/                        FastAPI application
│   ├── main.py                 Routes + lifespan
│   ├── db.py                   asyncpg pool
│   ├── cache.py                Redis cache-aside
│   ├── kafka_producer.py       Async order publisher
│   ├── kafka_consumer.py       Order consumer worker
│   ├── models.py               Pydantic models
│   └── config.py               Settings (pydantic-settings)
├── nginx/                      Nginx config (static upstream + keepalive)
├── prometheus/                 Prometheus scrape config
├── grafana/                    Dashboards + provisioning
├── scripts/
│   ├── entrypoint.sh           Container entrypoint
│   ├── load_data.py            CSV → PostgreSQL loader
│   ├── startup-api-vm.sh       GCP API VM startup script
│   ├── stress_test_max_rps.js  k6 fixed-rate load test
│   └── stress_test_find_max.js k6 ramp-up test
├── docs/
│   ├── GCP_SCALED_SETUP.md     Full GCP deployment guide
│   └── SCALING_TO_1M_RPS.md    Scaling analysis
├── docker-compose.yaml         Local dev (all-in-one)
├── docker-compose.data.yaml    Data VM stack
└── docker-compose.api.yaml     API VM stack
```
