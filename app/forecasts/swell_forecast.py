import requests
import json
from datetime import datetime
import os
from pathlib import Path

# Constants
FORECAST_CACHE_FILE = Path(__file__).parent.parent / "data" / "marine_forecast.json"
FORECAST_CACHE_DURATION = 6  # Hours before refreshing forecast

# Israel coastal coordinates (Herzliya Marina)
DEFAULT_LATITUDE = 32.1640
DEFAULT_LONGITUDE = 34.7914

def get_swell_forecast(days=7, latitude=DEFAULT_LATITUDE, longitude=DEFAULT_LONGITUDE):
    """
    Get marine forecast (waves and wind) for the specified number of days
    """
    # Check if we have a recent cached forecast
    if should_use_cached_forecast():
        return load_cached_forecast()
    
    # Limit to 16 days (Open-Meteo maximum)
    days = min(days, 16)
    
    # Construct URL for marine data (swell)
    marine_url = (
        f"https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={latitude}&longitude={longitude}"
        f"&hourly=wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction,swell_wave_period"
        f"&timezone=Asia/Jerusalem"
        f"&forecast_days={days}"
    )
    
    # Construct URL for weather data (wind)
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        f"&hourly=wind_speed_10m,wind_direction_10m"
        f"&timezone=Asia/Jerusalem"
        f"&forecast_days={days}"
    )
    
    try:
        # Get marine data
        marine_response = requests.get(marine_url)
        marine_response.raise_for_status()
        marine_data = marine_response.json()
        
        # Get weather data
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        # Combine and process data
        processed_forecast = process_combined_forecast(marine_data, weather_data)
        
        # Cache the forecast
        save_forecast_to_cache(processed_forecast)
        
        return processed_forecast
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching forecast: {e}")
        
        # If we have a cached forecast (even if expired), return it as fallback
        if os.path.exists(FORECAST_CACHE_FILE):
            return load_cached_forecast()
        
        return None

def process_combined_forecast(marine_data, weather_data):
    """Process and combine marine and weather data"""
    if not marine_data or "hourly" not in marine_data:
        return None
    
    if not weather_data or "hourly" not in weather_data:
        print("Warning: Weather data unavailable, proceeding with marine data only")
    
    # Combine by date
    result = {
        "metadata": {
            "latitude": marine_data.get("latitude"),
            "longitude": marine_data.get("longitude"),
            "timezone": marine_data.get("timezone"),
            "generated_at": datetime.now().isoformat(),
            "source": "Open-Meteo API"
        },
        "daily": process_daily_data(marine_data, weather_data)
    }
    
    return result

def process_daily_data(marine_data, weather_data=None):
    """Process the data into daily summaries"""
    daily_forecasts = {}
    
    # Get time data from marine API
    times = marine_data["hourly"]["time"]
    
    # Prepare dictionaries to hold data by date
    date_data = {}
    
    # Process each hourly data point
    for i, time_str in enumerate(times):
        # Parse date
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        date_str = time_obj.strftime("%Y-%m-%d")
        
        # Create date entry if not exists
        if date_str not in date_data:
            date_data[date_str] = {
                "date": date_str,
                "display_date": time_obj.strftime("%A, %d %B %Y"),
                "wave_heights": [],
                "wave_directions": [],
                "wave_periods": [],
                "swell_heights": [],
                "swell_directions": [],
                "swell_periods": [],
                "wind_speeds": [],
                "wind_directions": []
            }
        
        # Add marine data
        try:
            date_data[date_str]["wave_heights"].append(marine_data["hourly"]["wave_height"][i])
            date_data[date_str]["wave_directions"].append(marine_data["hourly"]["wave_direction"][i])
            date_data[date_str]["wave_periods"].append(marine_data["hourly"]["wave_period"][i])
            date_data[date_str]["swell_heights"].append(marine_data["hourly"]["swell_wave_height"][i])
            date_data[date_str]["swell_directions"].append(marine_data["hourly"]["swell_wave_direction"][i])
            date_data[date_str]["swell_periods"].append(marine_data["hourly"]["swell_wave_period"][i])
        except (IndexError, KeyError) as e:
            print(f"Warning: Missing marine data for {time_str}: {e}")
        
        # Add weather data
        if weather_data and "hourly" in weather_data and i < len(weather_data["hourly"]["time"]):
            try:
                # Convert wind speed from m/s to knots (1 m/s ≈ 1.94384 knots)
                wind_speed_ms = weather_data["hourly"]["wind_speed_10m"][i]
                wind_speed_knots = wind_speed_ms * 1.94384
                date_data[date_str]["wind_speeds"].append(wind_speed_knots)
                
                date_data[date_str]["wind_directions"].append(weather_data["hourly"]["wind_direction_10m"][i])
            except (IndexError, KeyError) as e:
                print(f"Warning: Missing weather data for {time_str}: {e}")
    
    # Calculate daily summaries
    for date_str, data in date_data.items():
        daily_summary = {
            "date": data["date"],
            "display_date": data["display_date"]
        }
        
        # Calculate max and average values for marine data
        if data["wave_heights"]:
            daily_summary["max_wave_height"] = max(data["wave_heights"])
            daily_summary["avg_wave_period"] = sum(data["wave_periods"]) / len(data["wave_periods"])
        
        if data["swell_heights"]:
            daily_summary["max_swell_height"] = max(data["swell_heights"])
            daily_summary["avg_swell_period"] = sum(data["swell_periods"]) / len(data["swell_periods"])
        
        # Calculate dominant directions
        if data["wave_directions"]:
            daily_summary["dominant_wave_direction"] = get_dominant_direction(data["wave_directions"])
        
        if data["swell_directions"]:
            daily_summary["dominant_swell_direction"] = get_dominant_direction(data["swell_directions"])
        
        # Calculate wind data
        if data["wind_speeds"]:
            daily_summary["max_wind_speed_knots"] = max(data["wind_speeds"])
            daily_summary["avg_wind_speed_knots"] = sum(data["wind_speeds"]) / len(data["wind_speeds"])
            daily_summary["dominant_wind_direction"] = get_dominant_direction(data["wind_directions"])
        
        daily_forecasts[date_str] = daily_summary
    
    return daily_forecasts

def get_dominant_direction(directions):
    """Find the most common direction"""
    direction_counts = {}
    for direction in directions:
        cardinal = direction_to_cardinal(direction)
        if cardinal in direction_counts:
            direction_counts[cardinal] += 1
        else:
            direction_counts[cardinal] = 1
    
    if not direction_counts:
        return None
    
    return max(direction_counts.items(), key=lambda x: x[1])[0]

def direction_to_cardinal(degrees):
    """Convert degrees to cardinal direction"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]

def should_use_cached_forecast():
    """Check if we should use the cached forecast"""
    if not os.path.exists(FORECAST_CACHE_FILE):
        return False
    
    try:
        with open(FORECAST_CACHE_FILE, "r") as f:
            data = json.load(f)
        
        # Check when the forecast was generated
        generated_at = datetime.fromisoformat(data["metadata"]["generated_at"])
        age_hours = (datetime.now() - generated_at).total_seconds() / 3600
        
        # Use cache if it's less than FORECAST_CACHE_DURATION hours old
        return age_hours < FORECAST_CACHE_DURATION
    
    except (json.JSONDecodeError, KeyError, ValueError):
        return False

def load_cached_forecast():
    """Load forecast from cache file"""
    try:
        with open(FORECAST_CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cached forecast: {e}")
        return None

def save_forecast_to_cache(forecast_data):
    """Save forecast data to cache file"""
    try:
        os.makedirs(os.path.dirname(FORECAST_CACHE_FILE), exist_ok=True)
        with open(FORECAST_CACHE_FILE, "w") as f:
            json.dump(forecast_data, f, indent=2)
    except Exception as e:
        print(f"Error saving forecast to cache: {e}")

def get_simplified_forecast(days=7):
    """Get a simplified version of the forecast for display"""
    forecast = get_swell_forecast(days=days)
    
    if not forecast or "daily" not in forecast:
        return None
    
    simplified = []
    for date, data in forecast["daily"].items():
        simple_data = {
            "date": date,
            "display_date": data["display_date"],
            "max_wave_height": round(data.get("max_wave_height", 0), 1),
            "max_swell_height": round(data.get("max_swell_height", 0), 1),
            "avg_wave_period": round(data.get("avg_wave_period", 0), 1),
            "avg_swell_period": round(data.get("avg_swell_period", 0), 1),
            "dominant_wave_direction": data.get("dominant_wave_direction"),
            "dominant_swell_direction": data.get("dominant_swell_direction")
        }
        
        # Add wind data if available
        if "max_wind_speed_knots" in data:
            simple_data["max_wind_speed_knots"] = round(data["max_wind_speed_knots"], 1)
            simple_data["avg_wind_speed_knots"] = round(data.get("avg_wind_speed_knots", 0), 1)
            simple_data["dominant_wind_direction"] = data.get("dominant_wind_direction")
        
        simplified.append(simple_data)
    
    # Sort by date
    simplified.sort(key=lambda x: x["date"])
    
    return simplified

def get_swell_emoji(height):
    """Get emoji representation for swell height"""
    if height <= 0.4:
        return "🏝️"  # Calm sea/beach
    elif height <= 0.8:
        return "🌊"  # Medium waves
    else:
        return "🌊🌊"  # Large waves

def get_wind_emoji(speed_knots):
    """Get emoji representation for wind speed in knots"""
    if speed_knots < 5:
        return "🍃"  # Light wind
    elif speed_knots < 14:
        return "💨"  # Moderate wind
    else:
        return "🌪️"  # Strong wind

def get_forecast_for_date(date_str):
    """Get forecast for a specific date (YYYY-MM-DD format)"""
    forecast = get_swell_forecast(days=16)  # Max days to ensure coverage
    
    if not forecast or "daily" not in forecast:
        return None
    
    # Try to find the date in the forecast
    if date_str in forecast["daily"]:
        return forecast["daily"][date_str]
    
    # If the exact date string isn't found, try to match by date only
    for key, data in forecast["daily"].items():
        if key.startswith(date_str):
            return data
    
    return None

def get_forecast_for_slot(slot):
    """Get forecast data relevant to a specific slot"""
    if not slot or "date" not in slot:
        return None
    
    # Extract date from slot
    slot_date = slot.get("date", "")
    
    # Try to parse Hebrew date format (e.g., "שישי, 12 אפריל 2025")
    try:
        # Handle Hebrew month names
        hebrew_month_names = {
            "ינואר": "January",
            "פברואר": "February",
            "מרץ": "March",
            "אפריל": "April",
            "מאי": "May",
            "יוני": "June",
            "יולי": "July",
            "אוגוסט": "August",
            "ספטמבר": "September",
            "אוקטובר": "October",
            "נובמבר": "November",
            "דצמבר": "December"
        }
        
        # Try to parse the date
        if "," in slot_date:
            # Format like "שישי, 12 אפריל 2025"
            day_name, date_part = slot_date.split(",", 1)
            day_name = day_name.strip()
            date_part = date_part.strip()
            
            parts = date_part.split()
            if len(parts) >= 3:  # day, month, year
                day_num = parts[0]
                month_name = parts[1]
                year = parts[2]
                
                # Translate Hebrew month name if needed
                if month_name in hebrew_month_names:
                    month_name = hebrew_month_names[month_name]
                
                # Try to parse the date
                date_obj = datetime.strptime(f"{day_num} {month_name} {year}", "%d %B %Y")
                date_str = date_obj.strftime("%Y-%m-%d")
                
                return get_forecast_for_date(date_str)
    except Exception as e:
        print(f"Error parsing slot date: {e}")
    
    # If we couldn't parse the date, try to get today's forecast
    today = datetime.now().strftime("%Y-%m-%d")
    return get_forecast_for_date(today)

def format_slot_forecast(slot):
    """Format forecast data for a slot in a compact way"""
    forecast = get_forecast_for_slot(slot)
    
    if not forecast:
        return "No forecast available"
    
    # Swell information
    swell_height = round(forecast.get("max_swell_height", 0), 1)
    swell_emoji = get_swell_emoji(swell_height)
    
    # Wind information if available
    if "max_wind_speed_knots" in forecast:
        wind_speed = round(forecast.get("max_wind_speed_knots", 0), 1)
        wind_emoji = get_wind_emoji(wind_speed)
        return f"{swell_emoji}{wind_emoji}"
    
    return f"{swell_emoji}"

def format_wind_forecast(forecast):
    """Format wind forecast data in a compact way"""
    if not forecast or "max_wind_speed_knots" not in forecast:
        return "Wind data unavailable"
    
    wind_speed = round(forecast.get("max_wind_speed_knots", 0), 1)
    wind_direction = forecast.get("dominant_wind_direction", "")
    wind_emoji = get_wind_emoji(wind_speed)
    
    return f"{wind_emoji} {wind_speed}kt | {wind_direction}"

if __name__ == "__main__":
    # Test the function when run directly
    forecast = get_simplified_forecast(days=5)
    
    if forecast:
        print(json.dumps(forecast, indent=2))
        
        # Show first day's forecast with emoji indicators
        day = forecast[0]
        print(f"\nWave forecast for {day['display_date']}:")
        print(f"Swell: {get_swell_emoji(day['max_swell_height'])} {day['max_swell_height']}m ({day['dominant_swell_direction']})")
        
        if "max_wind_speed_knots" in day:
            print(f"Wind: {get_wind_emoji(day['max_wind_speed_knots'])} {day['max_wind_speed_knots']}kt ({day['dominant_wind_direction']})")
        else:
            print("Wind data unavailable")
    else:
        print("Failed to retrieve forecast")
