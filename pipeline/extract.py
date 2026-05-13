import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

CITIES = {
    "Munich":  {"lat": 48.14, "lon": 11.58},
    "Berlin":  {"lat": 52.52, "lon": 13.40},
    "Hamburg": {"lat": 53.55, "lon": 10.00},
}

def fetch_weather(city, lat, lon):
    """Call Open-Meteo API — free, no key needed."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,windspeed_10m,precipitation",
        "forecast_days": 1
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def save_to_blob(data, city):
    """Save raw JSON to Azure Blob Storage."""
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING not set")

    client = BlobServiceClient.from_connection_string(connection_string)
    today = datetime.now().strftime("%Y-%m-%d")
    blob_name = f"weather/{city}/{today}.json"

    blob_client = client.get_blob_client(
        container="raw-weather",
        blob=blob_name
    )
    blob_client.upload_blob(json.dumps(data), overwrite=True)
    print(f"  ✓ Saved {city} → {blob_name}")


def run_extract():
    """Extract weather data for all cities and save to blob."""
    print("Extracting weather data...")
    for city, coords in CITIES.items():
        data = fetch_weather(city, coords["lat"], coords["lon"])
        save_to_blob(data, city)
    print("Extract complete.\n")


if __name__ == "__main__":
    run_extract()