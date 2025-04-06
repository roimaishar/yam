import requests

# Check marine API parameters
url = "https://marine-api.open-meteo.com/v1/marine?latitude=32.1640&longitude=34.7914&hourly=wave_height,wave_direction,wave_period&timezone=Asia/Jerusalem"
response = requests.get(url)
data = response.json()

print("API Response Structure:")
print(list(data.keys()))

if "hourly" in data:
    print("\nHourly parameters:")
    print(list(data["hourly"].keys()))

# Check if we can access wind data from the regular weather API
print("\nTrying regular weather API for wind data...")
url2 = "https://api.open-meteo.com/v1/forecast?latitude=32.1640&longitude=34.7914&hourly=temperature_2m,wind_speed_10m,wind_direction_10m&timezone=Asia/Jerusalem"
response2 = requests.get(url2)
data2 = response2.json()

print("Weather API Response Structure:")
print(list(data2.keys()))

if "hourly" in data2:
    print("\nHourly weather parameters:")
    print(list(data2["hourly"].keys()))
    
    # Show sample wind data
    print("\nSample wind data (first 3 hours):")
    for i in range(3):
        time = data2["hourly"]["time"][i]
        speed = data2["hourly"]["wind_speed_10m"][i]
        direction = data2["hourly"]["wind_direction_10m"][i]
        speed_knots = round(speed * 1.94384, 1)  # Convert m/s to knots
        print(f"Time: {time}, Speed: {speed} m/s ({speed_knots} knots), Direction: {direction}°")
