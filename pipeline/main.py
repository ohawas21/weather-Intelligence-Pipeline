import os
from dotenv import load_dotenv
from pipeline.extract import run_extract
from pipeline.transform import transform_and_store
from pipeline.ai_briefing import generate_briefing
from pipeline.azure_sql_loader import load_to_azure_sql

load_dotenv()

if __name__ == "__main__":
    print("=" * 50)
    print("  WEATHER INTELLIGENCE PIPELINE")
    print("=" * 50)
    print()

    print("STEP 1 — Extract")
    run_extract()

    print("STEP 2 — Transform")
    print("Transforming weather data...")
    transform_and_store()

    print("STEP 3 — Load to Azure SQL")
    print("Loading into Azure SQL...")
    load_to_azure_sql()
    print()

    print("STEP 4 — AI Briefing")
    print("Generating AI weather briefing...")
    print()
    briefing = generate_briefing()

    print("Today's briefing:")
    print("-" * 50)
    print(briefing)
    print("-" * 50)
    print()
    print("Pipeline complete.")