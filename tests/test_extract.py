from pipeline.extract import fetch_weather

def test_fetch_weather():
    """Test that the API returns data for Munich."""
    data = fetch_weather("Munich", 48.14, 11.58)
    assert "hourly" in data
    assert "temperature_2m" in data["hourly"]
    assert len(data["hourly"]["temperature_2m"]) == 24
    print("Test passed — API returns 24 hours of data")