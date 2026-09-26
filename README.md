# JourneyIQ

> **Customer Journey Mapping and Channel Attribution Analysis for Digital Campaigns**

JourneyIQ helps marketing and data teams answer questions like:

- Which channels actually drive conversions?
- What does a customer's path to purchase look like?
- Which campaigns deliver the best return on spend?

---

## Stage 2 — Campaign Data + Conversions + PostgreSQL Loading (current)

Stage 1 established the schema. Stage 2 adds:
- `campaigns.csv` with 18 realistic paid campaigns
- `conversions.csv` with purchase records for ~35% of customers who checked out
- `backend/scripts/load_data.py` — upsert-safe CSV loader into PostgreSQL
- `database/validation.sql` — 12 data quality checks
- `backend/scripts/validate_csvs.py` — offline validation (no Postgres needed)

---

## Stage 1 — Data Foundation

### Architecture

```
JourneyIQ/
├── backend/
│   ├── app/
│   │   ├── __init__.py      # Python package marker
│   │   ├── main.py          # FastAPI app + /api/health endpoint
│   │   ├── config.py        # Centralised settings (loaded from .env)
│   │   └── database.py      # SQLAlchemy engine + session factory
│   ├── scripts/
│   │   └── generate_data.py # Synthetic customer journey generator
│   ├── requirements.txt
│   └── .env.example
│
├── database/
│   └── schema.sql           # PostgreSQL DDL (tables, indexes, constraints)
│
├── data/
│   ├── customers.csv        # Generated — 500 customers
│   └── customer_events.csv  # Generated — 3,000–5,000 events
│
└── README.md
```

### Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API framework | FastAPI | Fast, auto-documented, async-ready |
| Database | PostgreSQL 14+ | Robust relational DB for analytical queries |
| ORM / connection | SQLAlchemy 2 | Connection pooling, Python-native queries |
| DB driver | psycopg2-binary | PostgreSQL adapter for Python |
| Config | python-dotenv | Loads `.env` file into `os.environ` |
| Data generation | Pandas + NumPy + Faker | Realistic synthetic data |

---

## Setup Guide

### 1. Create the PostgreSQL database

Open `psql` (or pgAdmin) and run:

```sql
CREATE DATABASE journeyiq;
```

Then apply the schema:

```bash
psql -U postgres -d journeyiq -f database/schema.sql
```

This creates four tables: `customers`, `campaigns`, `events`, `conversions`.

---

### 2. Create a Python virtual environment

```bash
# From the project root (JourneyIQ/)
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Mac / Linux)
source venv/bin/activate
```

---

### 3. Install requirements

```bash
pip install -r backend/requirements.txt
```

---

### 4. Configure environment variables

```bash
# Copy the template
cp backend/.env.example backend/.env

# Edit backend/.env and set your real PostgreSQL password
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/journeyiq
```

---

### 5. Run the synthetic data generator

```bash
# From the project root (JourneyIQ/)
python backend/scripts/generate_data.py
```

This creates:
- `data/customers.csv`   — 500 customer records
- `data/customer_events.csv` — 3,000–5,000 journey events

---

### 6. Start the API server

```bash
# From the project root (JourneyIQ/)
# Windows PowerShell:
$env:PYTHONPATH="backend"; venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000

# Mac / Linux:
PYTHONPATH=backend uvicorn backend.app.main:app --reload --port 8000
```

> **Why `PYTHONPATH=backend`?**  
> The `app` package lives inside `backend/`. Setting `PYTHONPATH` tells Python to treat
> `backend/` as a root so `from app.config import settings` resolves correctly.

- Health check: http://localhost:8000/api/health
- Interactive docs: http://localhost:8000/docs

---

## Database Tables

### `customers`
Each row is one unique customer. Columns: `customer_id`, `first_seen`, `country`, `device`, `customer_segment`.  
Used as the anchor: all events and conversions link back here via `customer_id`.

Marketing campaigns that generate paid traffic. Columns: `campaign_id`, `name`, `channel`, `start_date`, `end_date`, `budget`, `spend`.
Paid channels only: Instagram, Facebook, Google Search, Google Display, YouTube, Email.
Organic Search, Direct, Referral, and SMS have no associated campaign.

### `events`
Every customer touchpoint — the heart of the system. Columns: `customer_id`, `timestamp`, `session_id`, `channel`, `campaign_id`, `event_type`, `page`, `product_id`, `device`.  
Event types: `impression → click → page_view → product_view → add_to_cart → checkout`.  
`campaign_id` is `NULL` for organic/direct channels.

### `conversions`
Completed purchases. Columns: `customer_id`, `timestamp`, `order_id`, `product_id`, `revenue`.
Populated in Stage 2. Attribution models JOIN this with `events` to answer "which channel gets credit?"

---

## Stage 2 Setup

### 7. Run the data loader (after PostgreSQL is set up)

```powershell
# Windows PowerShell — from JourneyIQ/
$env:PYTHONPATH="backend"; venv\Scripts\python.exe backend\scripts\load_data.py
```

This loads all four CSVs into PostgreSQL using upsert logic (safe to re-run).

### 8. Run offline CSV validation (no PostgreSQL needed)

```powershell
venv\Scripts\python.exe backend\scripts\validate_csvs.py
```

### 9. Run database validation queries

```bash
psql -U postgres -d journeyiq -f database/validation.sql
```

---

---

## Deployment Guide

> **Note:** This section documents deployment preparation and target architecture for JourneyIQ. Deployment accounts and live cloud infrastructure will be provisioned in Stage 9B.

### Architecture

```
                    INTERNET
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
          Vercel           Render / Railway
      (React + Vite)           (FastAPI)
             │                   │
             └─────────┬─────────┘
                       │
                       ▼
                 PostgreSQL
             (Managed Cloud DB)
```

- **Frontend:** Deployed to **Vercel** as a static Single Page Application (SPA) with client-side routing.
- **Backend:** Deployed to **Render** (or **Railway**) as a containerized/native Python ASGI web service.
- **Database:** Managed **PostgreSQL** instance with connection pooling.

---

### Environment Variables

#### Frontend (Vercel)
Configured via Vercel Project Settings > Environment Variables:

| Variable | Description | Example (Safe Placeholder) |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Public origin of the deployed backend API | `https://api.journeyiq.example.com` |

> **Security Note:** `VITE_*` variables are embedded into client-side JavaScript. Never store secrets, private tokens, or database credentials in frontend environment variables.

#### Backend (Render / Railway)
Configured via platform service environment settings:

| Variable | Requirement | Description | Example (Safe Placeholder) |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Required | Runtime mode (`production`, `development`) | `production` |
| `DATABASE_URL` | Required | Standard PostgreSQL connection URL | `postgresql://<user>:<password>@<host>:<port>/<dbname>?sslmode=require` |
| `CORS_ORIGINS` | Required | Comma-separated allowed frontend origins | `https://<your-frontend>.vercel.app` |
| `ALLOWED_HOSTS` | Required | Comma-separated allowed Host header names | `<your-backend>.onrender.com` |
| `DEBUG` | Optional | Set to `false` in production | `false` |
| `DB_POOL_SIZE` | Optional | Database connection pool capacity | `5` |
| `DB_MAX_OVERFLOW` | Optional | Maximum overflow connections | `10` |
| `DB_POOL_TIMEOUT` | Optional | Pool connection timeout in seconds | `30` |

---

### Database Initialization Order

When deploying to a fresh PostgreSQL instance, execute steps in this strict dependency order to respect all foreign keys and constraints:

1. **Create PostgreSQL Database:** Provision the cloud database instance.
2. **Apply Schema DDL:** Run `database/schema.sql` to establish enums, tables, and indexes (`customers`, `campaigns`, `events`, `conversions`).
3. **Load Customers:** Ingest customer cohort records (`customer_id` primary key anchor).
4. **Load Campaigns:** Ingest marketing campaigns (`campaign_id` primary key anchor).
5. **Load Events:** Ingest customer journey events (FK to `customers` and `campaigns`).
6. **Load Conversions:** Ingest conversion and purchase records (FK to `customers`).
7. **Run Validation:** Execute database integrity checks (`database/validation.sql` or `validate_csvs.py`).

> In production, ingestion can be performed using `backend/scripts/load_data.py` pointing to the target `DATABASE_URL`. The loader utilizes idempotent `ON CONFLICT DO NOTHING` upsert logic.

---

### Build & Startup Commands

#### Backend
- **Install dependencies:** `pip install -r backend/requirements.txt`
- **Production ASGI startup:**
  ```bash
  uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
  ```
  *(Compatible with Render, Railway, Docker, or native Linux environments. The application dynamically binds to the `$PORT` provided by the host environment).*

#### Frontend
- **Install dependencies:** `npm install`
- **Production build:**
  ```bash
  npm run build
  ```
  *(Executes `tsc -b` and `vite build`, outputting optimized assets to `dist/`).*

---

### Health & Readiness Probes

The FastAPI backend exposes two dedicated operational endpoints:

- **Liveness Probe:** `GET /api/health`
  - Returns `{"status": "ok", "service": "journeyiq-api"}` (HTTP 200).
  - Used by Render/Railway health check monitors to ensure the process is responsive.
- **Readiness Probe:** `GET /api/ready`
  - Actively validates PostgreSQL database connection (`SELECT 1`).
  - Returns `{"status": "ready", "database": "connected"}` (HTTP 200) when ready, or HTTP 503 if the database is unreachable without leaking internal connection details.

