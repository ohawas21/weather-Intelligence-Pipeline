import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()

def generate_briefing():
    """Query SQLite for today's data and ask Claude to write a briefing."""
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Query the structured data with SQL aggregations
    conn = sqlite3.connect("weather.db")
    rows = conn.execute("""
        SELECT
            city,
            ROUND(AVG(temperature), 1)    AS avg_temp,
            ROUND(MAX(temperature), 1)    AS max_temp,
            ROUND(MIN(temperature), 1)    AS min_temp,
            ROUND(MAX(windspeed), 1)      AS max_wind,
            ROUND(SUM(precipitation), 2)  AS total_rain
        FROM hourly_weather
        WHERE date = ?
        GROUP BY city
        ORDER BY city
    """, (today,)).fetchall()
    conn.close()

    if not rows:
        return "No weather data found for today."

    # 2. Format data as context for Claude
    data_summary = "\n".join([
        f"- {r[0]}: avg {r[1]}°C, max {r[2]}°C, min {r[3]}°C, "
        f"max wind {r[4]} km/h, total rain {r[5]}mm"
        for r in rows
    ])

    print("  Data sent to Claude:")
    print(data_summary)
    print()

    # 3. Call Claude
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system="You are a professional meteorologist writing a concise daily weather briefing for German cities. Be specific with the numbers. Write exactly 3 sentences.",
        messages=[
            {
                "role": "user",
                "content": f"Write a daily weather briefing for {today} based on this data:\n\n{data_summary}"
            }
        ]
    )

    briefing = response.content[0].text
    return briefing


if __name__ == "__main__":
    print("Generating AI weather briefing...")
    print()
    briefing = generate_briefing()
    print("Claude's briefing:")
    print("-" * 50)
    print(briefing)
    print("-" * 50)