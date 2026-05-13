# Weather Intelligence Pipeline

An end-to-end data pipeline that ingests live weather data from a public API, stores raw data in **Azure Blob Storage** as a data lake layer, transforms it into a structured **SQLite** database, loads it into **Azure SQL Database** as the cloud analytics layer, and uses **Claude AI** to generate an intelligent daily weather briefing — all deployed automatically via **GitHub Actions CI/CD**.

---

## What this project does

Every time code is pushed to `main`, or every morning at 6am via a scheduled cron job, the pipeline runs automatically in the cloud:

1. Pulls hourly weather data for **Munich, Berlin, and Hamburg** from the Open-Meteo API (free, no key needed)
2. Saves the raw JSON responses to **Azure Blob Storage** — the raw data lake layer
3. Reads the raw data back, flattens it into clean rows, and stores it in a **SQLite database** — the local structured layer
4. Loads the same clean rows into **Azure SQL Database** — the cloud-persisted structured analytics layer
5. Queries the database with **SQL aggregations** (avg temp, max wind, total rain per city)
6. Feeds that structured data to **Claude AI** which writes a professional 3-sentence daily weather briefing
7. The entire process runs inside a **Docker container**, tested and deployed by a **GitHub Actions CI/CD pipeline**

---

## Architecture

```
Open-Meteo API (free — no key needed)
        ↓
    extract.py
        ↓
Azure Blob Storage                   ← raw data lake layer
  raw-weather/
    weather/Munich/2026-05-13.json
    weather/Berlin/2026-05-13.json
    weather/Hamburg/2026-05-13.json
        ↓
    transform.py
        ↓
SQLite database                      ← local structured layer
  hourly_weather table
  (city, date, hour, temperature, windspeed, precipitation)
        ↓
    azure_sql_loader.py
        ↓
Azure SQL Database                   ← cloud structured analytics layer
  hourly_weather table               (same schema — 72 rows per day)
        ↓
    ai_briefing.py
        ↓
SQL aggregation query                ← avg temp, max wind, total rain per city
        ↓
Claude AI (claude-haiku-4-5)         ← reads structured data, writes briefing
        ↓
Daily weather briefing output
```

**CI/CD pipeline (GitHub Actions):**
```
git push → ODBC driver installed → pip install → tests run → full pipeline executes → done
                ↑
     also triggers every morning at 6am automatically (cron: 0 6 * * *)
```

---

## Technologies used

| Technology | Role in this project |
|---|---|
| **Python 3.11** | Core language for all pipeline scripts |
| **Open-Meteo API** | Free weather data source — no API key required |
| **Azure Blob Storage** | Raw data lake — stores JSON responses before transformation |
| **SQLite** | Local structured layer — fast, zero-config, stores clean queryable rows |
| **Azure SQL Database** | Cloud structured analytics layer — persistent, production-grade SQL |
| **Anthropic Claude API** | AI layer — reads structured data and generates daily briefing |
| **pyodbc + ODBC Driver 18** | Python driver for connecting to Azure SQL from Linux/Mac |
| **Docker** | Containerises the pipeline — runs identically everywhere |
| **GitHub Actions** | CI/CD — installs ODBC driver, runs tests, deploys on every push |
| **pytest** | Automated testing — verifies the API connection before deploying |

---

## Project structure

```
weather-Intelligence-Pipeline/
│
├── pipeline/
│   ├── __init__.py           # makes pipeline a Python package
│   ├── extract.py            # Step 1: fetch from Open-Meteo + save to Azure Blob
│   ├── transform.py          # Step 2: read blob + clean + store in SQLite
│   ├── azure_sql_loader.py   # Step 3: read SQLite + load into Azure SQL Database
│   ├── ai_briefing.py        # Step 4: query SQLite + call Claude + return briefing
│   └── main.py               # runs all four steps in order
│
├── tests/
│   └── test_extract.py       # verifies API returns 24 hours of data
│
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI/CD pipeline — installs ODBC driver + runs pipeline
│
├── conftest.py               # pytest path configuration
├── Dockerfile                # containerises the app
├── requirements.txt          # Python dependencies
├── .env.example              # template showing which env vars are needed
└── README.md                 # this file
```

---

## How the pipeline works — explained in detail

### Step 1 — Extract (`extract.py`)

The Open-Meteo API is called for each city with parameters requesting hourly data:
- `temperature_2m` — air temperature at 2 metres above ground
- `windspeed_10m` — wind speed at 10 metres
- `precipitation` — rainfall in mm

The API returns a JSON object with a `hourly` key containing 24 values per field — one per hour of the day. This raw JSON is saved to Azure Blob Storage with a path like `weather/Munich/2026-05-13.json`.

**Why save raw data first?** This is the ELT pattern — Extract, Load, Transform. You load the raw data into storage before transforming it. If your transformation logic changes later, you can re-process the original data without calling the API again.

### Step 2 — Transform (`transform.py`)

The raw JSON blobs are read back from Azure Blob Storage. Each JSON is flattened from a nested structure into individual rows — one row per hour per city. The rows are inserted into a SQLite table called `hourly_weather`:

```sql
city TEXT, date TEXT, hour INTEGER,
temperature REAL, windspeed REAL, precipitation REAL
```

Before inserting, today's existing rows are deleted — this makes the pipeline safe to re-run multiple times on the same day without creating duplicate data.

### Step 3 — Azure SQL Loader (`azure_sql_loader.py`)

The same 72 clean rows are read from SQLite and loaded into **Azure SQL Database** — a fully managed cloud SQL server running in Microsoft Azure. This step creates the table automatically if it does not exist:

```sql
CREATE TABLE hourly_weather (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    city          NVARCHAR(50),
    date          DATE,
    hour          INT,
    temperature   FLOAT,
    windspeed     FLOAT,
    precipitation FLOAT,
    loaded_at     DATETIME DEFAULT GETDATE()
)
```

The connection uses `pyodbc` with **ODBC Driver 18 for SQL Server**. The `loaded_at` column is automatically set by Azure SQL on every insert, providing a full audit trail of when data was loaded.

**Why both SQLite and Azure SQL?** SQLite is the fast local processing layer — zero configuration, works anywhere. Azure SQL is the persistent cloud layer — accessible from anywhere, production-grade, and the standard in Azure data engineering roles.

### Step 4 — AI Briefing (`ai_briefing.py`)

The structured data is queried with SQL aggregations:

```sql
SELECT
    city,
    ROUND(AVG(temperature), 1) AS avg_temp,
    ROUND(MAX(temperature), 1) AS max_temp,
    ROUND(MIN(temperature), 1) AS min_temp,
    ROUND(MAX(windspeed), 1)   AS max_wind,
    ROUND(SUM(precipitation), 2) AS total_rain
FROM hourly_weather
WHERE date = ?
GROUP BY city
ORDER BY city
```

The result — 3 rows of aggregated city data — is formatted as structured context and sent to Claude. The system prompt instructs Claude to act as a professional meteorologist and write exactly 3 sentences. Because Claude receives real, structured numbers it produces accurate output with zero hallucination.

**This is the RAG-adjacent pattern for structured data:** instead of retrieving documents from a vector database, you retrieve rows from a SQL database and use them as grounded context for the LLM.

### CI/CD Pipeline (`.github/workflows/deploy.yml`)

The GitHub Actions workflow triggers on two events:
- Every push to the `main` branch
- Every day at 6am UTC via a cron schedule: `0 6 * * *`

The pipeline steps:
1. **Checkout** — downloads the latest code
2. **Setup Python 3.11** — installs Python on the runner
3. **Install ODBC Driver 18** — installs Microsoft's SQL Server ODBC driver on Ubuntu (required for pyodbc to connect to Azure SQL)
4. **Install Python dependencies** — runs `pip install -r requirements.txt pytest`
5. **Run tests** — executes `pytest tests/ -v` — if tests fail, the pipeline stops here
6. **Run pipeline** — executes `python -m pipeline.main` with all secrets injected as environment variables

All secrets are stored in GitHub Secrets — never in code.

---

## Azure resources used

| Resource | Azure service | Purpose |
|---|---|---|
| `weatherpipelinedata` | Azure Blob Storage | Raw data lake — stores JSON files |
| `raw-weather` | Blob Container | Container holding weather JSON blobs |
| `weatherpipeline-oh-2026` | Azure SQL Server | Managed SQL server instance |
| `free-sql-db-9245787` | Azure SQL Database | Cloud structured analytics layer |
| `weather-pipeline-rg` | Resource Group | Organises all Azure resources together |

---

## How to run locally

**1. Clone the repo**
```bash
git clone https://github.com/ohawas21/weather-Intelligence-Pipeline.git
cd weather-Intelligence-Pipeline
```

**2. Create virtual environment and install dependencies**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Install ODBC Driver (Mac)**
```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew install msodbcsql18
```

**4. Set up environment variables**
```bash
cp .env.example .env
```

Open `.env` and fill in:
```
ANTHROPIC_API_KEY=your_claude_api_key
AZURE_STORAGE_CONNECTION_STRING=your_azure_connection_string
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USERNAME=your-admin-username
AZURE_SQL_PASSWORD=your-password
```

**5. Run the full pipeline**
```bash
python -m pipeline.main
```

**6. Run tests**
```bash
pytest tests/ -v
```

---

## Example output

```
==================================================
  WEATHER INTELLIGENCE PIPELINE
==================================================

STEP 1 — Extract
Extracting weather data...
  ✓ Saved Munich → weather/Munich/2026-05-13.json
  ✓ Saved Berlin → weather/Berlin/2026-05-13.json
  ✓ Saved Hamburg → weather/Hamburg/2026-05-13.json
Extract complete.

STEP 2 — Transform
Transforming weather data...
  ✓ Transformed Munich → 24 rows
  ✓ Transformed Berlin → 24 rows
  ✓ Transformed Hamburg → 24 rows
Transform complete.

STEP 3 — Load to Azure SQL
Loading into Azure SQL...
  Read 72 rows from SQLite
  ✓ Table ready in Azure SQL
  ✓ Loaded 72 rows into Azure SQL

STEP 4 — AI Briefing
Generating AI weather briefing...

  Data sent to Claude:
  - Berlin: avg 9.4°C, max 13.7°C, min 6.3°C, max wind 15.8 km/h, total rain 3.2mm
  - Hamburg: avg 9.8°C, max 13.2°C, min 6.7°C, max wind 17.9 km/h, total rain 1.6mm
  - Munich: avg 9.9°C, max 14.1°C, min 4.1°C, max wind 20.2 km/h, total rain 0.6mm

Today's briefing:
--------------------------------------------------
Berlin zeigt heute Temperaturen zwischen 6,3°C und 13,7°C mit moderaten
Winden bis 15,8 km/h und leichten Niederschlägen von 3,2 mm. Hamburg
bleibt mit 9,8°C Mittelwert minimal wärmer bei maximal 13,2°C, während
stärkere Winde von 17,9 km/h erwartet werden. München präsentiert sich
als trockenster Standort mit nur 0,6 mm Niederschlag und einer
morgendlichen Kälte von 4,1°C.
--------------------------------------------------

Pipeline complete.
```

---

## Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key from console.anthropic.com |
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string from Azure Storage Account → Access keys |
| `AZURE_SQL_SERVER` | Azure SQL server address e.g. `yourserver.database.windows.net` |
| `AZURE_SQL_DATABASE` | Database name e.g. `free-sql-db-9245787` |
| `AZURE_SQL_USERNAME` | SQL admin username set during server creation |
| `AZURE_SQL_PASSWORD` | SQL admin password set during server creation |

---

## What I learned building this

- **ELT pattern** — why you load raw data first and transform later, and how this gives flexibility when requirements change
- **Azure Blob Storage** — how a data lake stores raw, schema-free data before it is structured — equivalent of AWS S3 or Google Cloud Storage
- **Azure SQL Database** — how to provision a cloud SQL server, configure firewall rules, connect via pyodbc, and load structured data from Python
- **ODBC Driver** — what it is and why it is needed to connect Python to Microsoft SQL Server on both Mac and Linux (Ubuntu in CI/CD)
- **SQL aggregations** — using GROUP BY, AVG, MAX, MIN, SUM to summarise 24 rows of hourly data into one meaningful row per city
- **LLM + structured data** — how feeding clean, aggregated numbers to an LLM produces accurate, grounded output with no hallucination
- **Docker** — packaging the pipeline so it runs identically locally and in the cloud
- **GitHub Actions CI/CD** — how a YAML file automates the full install → test → run cycle on every push, including installing system-level dependencies like the ODBC driver
- **Cron scheduling** — how `0 6 * * *` triggers the pipeline automatically every morning without any manual action
- **Firewall rules** — how Azure SQL firewall works, why you need to whitelist IP ranges, and how to allow GitHub Actions to connect

---

## Author

Omar Hawas — Applied AI student, TH Rosenheim