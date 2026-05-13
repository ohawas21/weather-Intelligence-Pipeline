# Weather Intelligence Pipeline

An end-to-end data pipeline that ingests live weather data from a public API, stores raw data in Azure Blob Storage as a data lake layer, transforms it into a structured database using SQL aggregations, and uses Claude AI to generate an intelligent daily weather briefing — all deployed automatically via GitHub Actions CI/CD.

---

## What this project does

Every time code is pushed to `main`, or every morning at 6am via a scheduled cron job, the pipeline runs automatically in the cloud:

1. Pulls hourly weather data for **Munich, Berlin, and Hamburg** from the Open-Meteo API (free, no key needed)
2. Saves the raw JSON responses to **Azure Blob Storage** — the raw data lake layer
3. Reads the raw data back, flattens it into clean rows, and stores it in a **SQLite database** — the structured analytics layer
4. Queries the database with **SQL aggregations** (avg temp, max wind, total rain per city)
5. Feeds that structured data to **Claude AI** which writes a professional 3-sentence daily weather briefing
6. The entire process runs inside a **Docker container**, tested and deployed by a **GitHub Actions CI/CD pipeline**

---

## Architecture

```
Open-Meteo API (free)
        ↓
    extract.py
        ↓
Azure Blob Storage          ← raw data lake layer
  raw-weather/
    weather/Munich/2026-05-13.json
    weather/Berlin/2026-05-13.json
    weather/Hamburg/2026-05-13.json
        ↓
    transform.py
        ↓
SQLite database             ← structured analytics layer
  hourly_weather table
  (city, date, hour, temperature, windspeed, precipitation)
        ↓
    ai_briefing.py
        ↓
SQL aggregation query       ← avg temp, max wind, total rain per city
        ↓
Claude AI (claude-haiku)    ← reads structured data, writes briefing
        ↓
Daily weather briefing output
```

**CI/CD pipeline (GitHub Actions):**
```
git push → tests run → full pipeline executes in cloud → done
                ↑
     also runs every morning at 6am automatically (cron)
```

---

## Technologies used

| Technology | Role in this project |
|---|---|
| **Python 3.11** | Core language for all pipeline scripts |
| **Open-Meteo API** | Free weather data source — no API key required |
| **Azure Blob Storage** | Raw data lake — stores JSON responses before transformation |
| **SQLite** | Structured analytics layer — stores clean, queryable rows |
| **Anthropic Claude API** | AI layer — reads structured data and generates daily briefing |
| **Docker** | Containerises the pipeline — runs identically everywhere |
| **GitHub Actions** | CI/CD — runs tests and deploys automatically on every push |
| **pytest** | Automated testing — verifies the API connection before deploying |

---

## Project structure

```
weather-Intelligence-Pipeline/
│
├── pipeline/
│   ├── __init__.py          # makes pipeline a Python package
│   ├── extract.py           # Step 1: fetch from Open-Meteo + save to Azure Blob
│   ├── transform.py         # Step 2: read blob + clean + store in SQLite
│   ├── ai_briefing.py       # Step 3: query SQLite + call Claude + return briefing
│   └── main.py              # runs all three steps in order
│
├── tests/
│   └── test_extract.py      # verifies API returns 24 hours of data
│
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD pipeline definition
│
├── conftest.py              # pytest path configuration
├── Dockerfile               # containerises the app
├── requirements.txt         # Python dependencies
├── .env.example             # template showing which env vars are needed
└── README.md                # this file
```

---

## How the pipeline works — explained in detail

### Step 1 — Extract (`extract.py`)

The Open-Meteo API is called for each city with parameters requesting hourly data:
- `temperature_2m` — air temperature at 2 metres above ground
- `windspeed_10m` — wind speed at 10 metres
- `precipitation` — rainfall in mm

The API returns a JSON object with a `hourly` key containing 24 values per field — one per hour of the day. This raw JSON is saved to Azure Blob Storage with a path like `weather/Munich/2026-05-13.json`.

**Why save raw data first?** This is the ELT pattern — Extract, Load, Transform. You load the raw data into storage before transforming it. The advantage is that if your transformation logic changes later, you can re-process the original data without calling the API again.

### Step 2 — Transform (`transform.py`)

The raw JSON blobs are read back from Azure Blob Storage. Each JSON is flattened from a nested structure into individual rows — one row per hour per city. The rows are inserted into a SQLite table called `hourly_weather` with columns:

```sql
city TEXT, date TEXT, hour INTEGER,
temperature REAL, windspeed REAL, precipitation REAL
```

Before inserting, today's existing rows are deleted — this makes the pipeline safe to re-run multiple times on the same day without creating duplicate data.

**Why SQLite?** For a project of this scale, SQLite is fast, zero-configuration, and requires no running database server. In a production Azure environment, this layer would be Azure SQL Database or Azure Synapse Analytics — the SQL queries would be identical.

### Step 3 — AI Briefing (`ai_briefing.py`)

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

The result is formatted as a structured text summary and sent to Claude as context. The system prompt instructs Claude to act as a professional meteorologist and write exactly 3 sentences. Because Claude receives real, structured numbers — not vague questions — it produces accurate, specific output with zero hallucination.

**This is the RAG-adjacent pattern for structured data:** instead of retrieving documents from a vector database, you retrieve rows from a SQL database and use them as grounded context for the LLM.

### CI/CD Pipeline (`.github/workflows/deploy.yml`)

The GitHub Actions workflow triggers on two events:
- Every push to the `main` branch
- Every day at 6am UTC via a cron schedule: `0 6 * * *`

The pipeline steps:
1. **Checkout** — downloads the latest code
2. **Setup Python** — installs Python 3.11 on the runner
3. **Install dependencies** — runs `pip install -r requirements.txt`
4. **Run tests** — executes `pytest tests/ -v` — if tests fail, the pipeline stops here and nothing is deployed
5. **Run pipeline** — executes `python -m pipeline.main` with secrets injected as environment variables

Secrets (`ANTHROPIC_API_KEY` and `AZURE_STORAGE_CONNECTION_STRING`) are stored in GitHub Secrets — never in code.

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

**3. Set up environment variables**
```bash
cp .env.example .env
```

Open `.env` and fill in:
```
ANTHROPIC_API_KEY=your_claude_api_key
AZURE_STORAGE_CONNECTION_STRING=your_azure_connection_string
```

**4. Run the full pipeline**
```bash
python -m pipeline.main
```

**5. Run tests**
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

STEP 3 — AI Briefing
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

---

## What I learned building this

- **ELT pattern** — why you load raw data first and transform later, and how this gives flexibility when requirements change
- **Azure Blob Storage** — how a data lake stores raw, schema-free data before it is structured
- **SQL aggregations** — using GROUP BY, AVG, MAX, MIN, SUM to summarise 24 rows of hourly data into one meaningful row per city
- **LLM + structured data** — how feeding clean, aggregated numbers to an LLM produces accurate, grounded output with no hallucination
- **Docker** — packaging the pipeline so it runs identically locally and in the cloud
- **GitHub Actions CI/CD** — how a YAML file automates the full test → run cycle on every push, and how secrets are injected safely without appearing in code
- **Cron scheduling** — how `0 6 * * *` triggers the pipeline automatically every morning without any manual action

---

## Author

Omar Hawas — Applied AI student, TH Rosenheim