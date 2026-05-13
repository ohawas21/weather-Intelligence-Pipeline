import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

def transform_and_store():
    """Read raw JSON from Azure Blob, clean it, store in SQLite."""
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    client = BlobServiceClient.from_connection_string(connection_string)

    conn = sqlite3.connect("weather.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hourly_weather (
            city        TEXT,
            date        TEXT,
            hour        INTEGER,
            temperature REAL,
            windspeed   REAL,
            precipitation REAL
        )
    """)

    today = datetime.now().strftime("%Y-%m-%d")
    cities = ["Munich", "Berlin", "Hamburg"]

    for city in cities:
        blob_name = f"weather/{city}/{today}.json"
        blob_client = client.get_blob_client(
            container="raw-weather",
            blob=blob_name
        )
        raw = blob_client.download_blob().readall()
        data = json.loads(raw)
        hourly = data["hourly"]

        # Delete today's rows first so we can re-run safely
        conn.execute(
            "DELETE FROM hourly_weather WHERE city=? AND date=?",
            (city, today)
        )

        for i, time in enumerate(hourly["time"]):
            conn.execute(
                "INSERT INTO hourly_weather VALUES (?,?,?,?,?,?)",
                (
                    city,
                    today,
                    i,
                    hourly["temperature_2m"][i],
                    hourly["windspeed_10m"][i],
                    hourly["precipitation"][i]
                )
            )
        print(f"  ✓ Transformed {city} → {len(hourly['time'])} rows")

    conn.commit()
    conn.close()
    print("Transform complete.\n")


if __name__ == "__main__":
    print("Transforming weather data...")
    transform_and_store()