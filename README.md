# Retail Stream API

Backend for the Cloud Administration course project: data service over a retail database with **Redis cache-aside** for product reads.

---

## Where things run (important)

| Part | Where it runs |
|------|----------------|
| **PostgreSQL** | In a Docker container |
| **Redis** | In a Docker container |
| **API (FastAPI)** | Either on your machine **or** in a Docker container (you choose below) |
| **Load data script** | Same place as the API (so it can reach Postgres) |
| **Tests (curl / test script)** | On your machine (they just call `http://localhost:8000`) |

You can either run **only Postgres + Redis in Docker** and run the API on your machine, or run **everything in Docker** (API + load + tests from your machine). Both are below.

**Quick test (all in Docker):**  
`docker compose up -d --build` → `docker compose run --rm app python scripts/load_data.py` → `bash scripts/test_api.sh`

---

## How to test — choose one way

### Option 1: Everything inside Docker (recommended if you want “all in containers”)

All commands below are run **on your machine** in the project folder; Docker runs the API and DBs **inside** containers.

```bash
# 1. Start all services (Postgres, Redis, API)
docker compose up -d --build

# 2. Load the CSV into Postgres (runs inside the app container, uses DB in postgres container)
docker compose run --rm app python scripts/load_data.py

# 3. Test the API (from your machine; the API is already running in the app container)
bash scripts/test_api.sh
```

- **Health:** http://localhost:8000/health  
- **Ready:** http://localhost:8000/ready  
- **Product:** http://localhost:8000/products/85048  
- **Docs:** http://localhost:8000/docs  

Make sure `online_retail_all.csv` is in the project root; it is mounted into the container for the load script.

---

### Option 2: Only Postgres + Redis in Docker (API on your machine)

Postgres and Redis run in Docker. The API, load script, and tests run **on your machine**.

```bash
# 1. Start only Postgres and Redis
docker compose up -d postgres redis

# 2. On your machine: venv, install deps, load data
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/load_data.py

# 3. Start the API on your machine
uvicorn app.main:app --reload

# 4. In another terminal (same machine): run tests
bash scripts/test_api.sh
```

Then open http://localhost:8000/docs or use the curl commands from the table below.

---

## Test commands (use once the API is running)

| What | Command |
|------|--------|
| Smoke test script | `bash scripts/test_api.sh` |
| Health | `curl http://localhost:8000/health` |
| Ready (DB + Redis) | `curl http://localhost:8000/ready` |
| Get product | `curl http://localhost:8000/products/85048` |
| Docs in browser | http://localhost:8000/docs |

Call `/products/85048` twice: first time from DB, second time from Redis (cache hit).

---

## Project plan

See **[PROJECT_PLAN.md](PROJECT_PLAN.md)** for phased implementation (Phase 1 = backend + Redis for professor demo; later phases = workload, Kafka, metrics, presentation).

## Architecture and data flow

- **architecture.txt** – components (FastAPI, PostgreSQL, Redis, Kafka, Prometheus, etc.).  
- **data-flow.txt** – sequence: GET product (cache-aside), POST order (Kafka, later phase).

## Config (optional)

Override with environment variables (prefix `APP_`):

- `APP_POSTGRES_HOST`, `APP_POSTGRES_PORT`, `APP_POSTGRES_USER`, `APP_POSTGRES_PASSWORD`, `APP_POSTGRES_DB`
- `APP_REDIS_HOST`, `APP_REDIS_PORT`, `APP_CACHE_TTL_SECONDS`

Default: `localhost`, user `retail`, password `retail`, DB `retail`, Redis port 6379, cache TTL 300 s.

## CI/CD (Auto-deploy to GCP)

This repo includes a GitHub Actions workflow that deploys to your GCP VM on every push to `main`.

- Workflow file: `.github/workflows/deploy-gcp.yml`
- VM deploy script: `scripts/deploy_on_vm.sh`
- Setup guide: `docs/CI_CD_GCP.md`
- 
