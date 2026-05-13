import os
from dotenv import load_dotenv
from pipeline.extract import run_extract
from pipeline.transform import transform_and_store
from pipeline.ai_briefing import generate_briefing

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

    print("STEP 3 — AI Briefing")
    print("Generating AI weather briefing...")
    print()
    briefing = generate_briefing()

    print("Today's briefing:")
    print("-" * 50)
    print(briefing)
    print("-" * 50)
    print()
    print("Pipeline complete.")