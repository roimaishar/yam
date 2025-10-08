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

# Moon phase reference date (known new moon)
REFERENCE_NEW_MOON = datetime(2000, 1, 6).date()
LUNAR_CYCLE_DAYS = 29.53  # Length of synodic month

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
    
    # Construct URL for weather data (wind, UV, visibility)
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        f"&hourly=wind_speed_10m,wind_direction_10m,uv_index,visibility,is_day"
        f"&daily=sunrise,sunset,uv_index_max"
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
    """Process the combined marine and weather data into a simplified daily summary"""
    # Initialize date mapping for data
    date_data_map = {}
    
    # Extract daily data
    daily_data = {}
    if "daily" in weather_data:
        daily_time = weather_data["daily"].get("time", [])
        daily_uv_max = weather_data["daily"].get("uv_index_max", [])
        daily_sunrise = weather_data["daily"].get("sunrise", [])
        daily_sunset = weather_data["daily"].get("sunset", [])
        
        for i in range(len(daily_time)):
            if i < len(daily_time):
                date_str = daily_time[i]
                daily_data[date_str] = {
                    "uv_index_max": daily_uv_max[i] if i < len(daily_uv_max) else None,
                    "sunrise": daily_sunrise[i] if i < len(daily_sunrise) else None,
                    "sunset": daily_sunset[i] if i < len(daily_sunset) else None
                }
    
    # Process marine hourly data first
    if "hourly" in marine_data:
        hourly_time = marine_data["hourly"].get("time", [])
        hourly_wave_height = marine_data["hourly"].get("wave_height", [])
        hourly_swell_height = marine_data["hourly"].get("swell_wave_height", [])
        hourly_wave_period = marine_data["hourly"].get("wave_period", [])
        hourly_swell_period = marine_data["hourly"].get("swell_wave_period", [])
        hourly_wave_direction = marine_data["hourly"].get("wave_direction", [])
        hourly_swell_direction = marine_data["hourly"].get("swell_wave_direction", [])
        
        # Initialize each unique date with default values
        for time_str in hourly_time:
            # Extract date part from ISO timestamp
            date_str = time_str.split("T")[0]
            
            if date_str not in date_data_map:
                # Display date in a readable format
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    display_date = date_obj.strftime("%A, %d %B %Y")
                except ValueError:
                    display_date = date_str
                
                # Calculate moon phase for this date
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                moon_emoji, moon_phase = calculate_moon_phase(date_obj)
                
                date_data_map[date_str] = {
                    "date": date_str,
                    "display_date": display_date,
                    "max_wave_height": 0.0,
                    "max_swell_height": 0.0,
                    "avg_wave_period": 0.0,
                    "avg_swell_period": 0.0,
                    "dominant_wave_direction": None,
                    "dominant_swell_direction": None,
                    "max_wind_speed_knots": 0.0,
                    "avg_wind_speed_knots": 0.0,
                    "dominant_wind_direction": None,
                    "max_uv_index": daily_data.get(date_str, {}).get("uv_index_max", None),
                    "min_visibility": 20000,
                    "moon_emoji": moon_emoji,
                    "moon_phase": moon_phase,
                    "sunrise": daily_data.get(date_str, {}).get("sunrise", None),
                    "sunset": daily_data.get(date_str, {}).get("sunset", None),
                    "wave_heights": [],
                    "swell_heights": [],
                    "wave_periods": [],
                    "swell_periods": [],
                    "wave_directions": [],
                    "swell_directions": []
                }
        
        # Now populate the marine data arrays
        for i, time_str in enumerate(hourly_time):
            date_str = time_str.split("T")[0]
            
            if date_str in date_data_map:
                if i < len(hourly_wave_height) and hourly_wave_height[i] is not None:
                    date_data_map[date_str]["wave_heights"].append(hourly_wave_height[i])
                if i < len(hourly_swell_height) and hourly_swell_height[i] is not None:
                    date_data_map[date_str]["swell_heights"].append(hourly_swell_height[i])
                if i < len(hourly_wave_period) and hourly_wave_period[i] is not None:
                    date_data_map[date_str]["wave_periods"].append(hourly_wave_period[i])
                if i < len(hourly_swell_period) and hourly_swell_period[i] is not None:
                    date_data_map[date_str]["swell_periods"].append(hourly_swell_period[i])
                if i < len(hourly_wave_direction) and hourly_wave_direction[i] is not None:
                    date_data_map[date_str]["wave_directions"].append(hourly_wave_direction[i])
                if i < len(hourly_swell_direction) and hourly_swell_direction[i] is not None:
                    date_data_map[date_str]["swell_directions"].append(hourly_swell_direction[i])
        
        # Calculate aggregates for marine data
        for date_str in date_data_map:
            if date_data_map[date_str]["wave_heights"]:
                date_data_map[date_str]["max_wave_height"] = max(date_data_map[date_str]["wave_heights"])
            if date_data_map[date_str]["swell_heights"]:
                date_data_map[date_str]["max_swell_height"] = max(date_data_map[date_str]["swell_heights"])
            if date_data_map[date_str]["wave_periods"]:
                date_data_map[date_str]["avg_wave_period"] = sum(date_data_map[date_str]["wave_periods"]) / len(date_data_map[date_str]["wave_periods"])
            if date_data_map[date_str]["swell_periods"]:
                date_data_map[date_str]["avg_swell_period"] = sum(date_data_map[date_str]["swell_periods"]) / len(date_data_map[date_str]["swell_periods"])
            if date_data_map[date_str]["wave_directions"]:
                date_data_map[date_str]["dominant_wave_direction"] = get_dominant_direction(date_data_map[date_str]["wave_directions"])
            if date_data_map[date_str]["swell_directions"]:
                date_data_map[date_str]["dominant_swell_direction"] = get_dominant_direction(date_data_map[date_str]["swell_directions"])
    
    # Process weather hourly data
    if "hourly" in weather_data:
        hourly_time = weather_data["hourly"].get("time", [])
        hourly_wind_speed = weather_data["hourly"].get("wind_speed_10m", [])
        hourly_wind_direction = weather_data["hourly"].get("wind_direction_10m", [])
        hourly_uv_index = weather_data["hourly"].get("uv_index", [])
        hourly_visibility = weather_data["hourly"].get("visibility", [])
        
        # Process the hourly data by date
        date_indices_map = {}
        
        for i, time_str in enumerate(hourly_time):
            date_str = time_str.split("T")[0]
            
            if date_str not in date_indices_map:
                date_indices_map[date_str] = []
            
            date_indices_map[date_str].append(i)
        
        # Calculate the aggregated values for each date
        for date_str, indices in date_indices_map.items():
            if date_str in date_data_map:
                # Wind data
                date_wind_speeds = [hourly_wind_speed[i] for i in indices if i < len(hourly_wind_speed)]
                date_wind_directions = [hourly_wind_direction[i] for i in indices if i < len(hourly_wind_direction)]
                
                # Convert m/s to knots (1 m/s ≈ 1.94384 knots)
                knots_conversion = 1.94384
                date_wind_speeds_knots = [speed * knots_conversion for speed in date_wind_speeds]
                
                if date_wind_speeds_knots:
                    date_data_map[date_str]["max_wind_speed_knots"] = max(date_wind_speeds_knots)
                    date_data_map[date_str]["avg_wind_speed_knots"] = sum(date_wind_speeds_knots) / len(date_wind_speeds_knots)
                
                if date_wind_directions:
                    date_data_map[date_str]["dominant_wind_direction"] = get_dominant_direction(date_wind_directions)
                
                # UV index data (use hourly only if daily max isn't available)
                if date_data_map[date_str]["max_uv_index"] is None and hourly_uv_index:
                    date_uv_indices = [hourly_uv_index[i] for i in indices if i < len(hourly_uv_index)]
                    if date_uv_indices:
                        date_data_map[date_str]["max_uv_index"] = max(date_uv_indices)
                
                # Visibility data
                date_visibility = [hourly_visibility[i] for i in indices if i < len(hourly_visibility)]
                if date_visibility:
                    date_data_map[date_str]["min_visibility"] = min(date_visibility)
    
    # Calculate daily summaries
    daily_forecasts = {}
    for date_str, data in date_data_map.items():
        daily_summary = {
            "date": data["date"],
            "display_date": data["display_date"],
            "max_wave_height": data["max_wave_height"],
            "max_swell_height": data["max_swell_height"],
            "avg_wave_period": data["avg_wave_period"],
            "avg_swell_period": data["avg_swell_period"],
            "dominant_wave_direction": data["dominant_wave_direction"],
            "dominant_swell_direction": data["dominant_swell_direction"],
            "max_wind_speed_knots": data["max_wind_speed_knots"],
            "avg_wind_speed_knots": data["avg_wind_speed_knots"],
            "dominant_wind_direction": data["dominant_wind_direction"],
            "max_uv_index": data["max_uv_index"],
            "min_visibility": data["min_visibility"],
            "moon_emoji": data["moon_emoji"],
            "moon_phase": data["moon_phase"],
            "sunrise": data["sunrise"],
            "sunset": data["sunset"]
        }
        
        daily_forecasts[date_str] = daily_summary
    
    return {
        "metadata": {
            "latitude": marine_data.get("latitude"),
            "longitude": marine_data.get("longitude"),
            "timezone": marine_data.get("timezone"),
            "generated_at": datetime.now().isoformat(),
            "source": "Open-Meteo API"
        },
        "daily": daily_forecasts
    }

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

def calculate_moon_phase(date):
    """Calculate approximate moon phase based on date"""
    # Days since reference new moon
    days_since = (date - REFERENCE_NEW_MOON).days
    
    # Position in cycle (0 to 1)
    position = (days_since % LUNAR_CYCLE_DAYS) / LUNAR_CYCLE_DAYS
    
    # Return emoji and phase
    if position < 0.125:
        return "🌑", "New Moon"
    elif position < 0.25:
        return "🌒", "Waxing Crescent"
    elif position < 0.375:
        return "🌓", "First Quarter"
    elif position < 0.5:
        return "🌔", "Waxing Gibbous"
    elif position < 0.625:
        return "🌕", "Full Moon"
    elif position < 0.75:
        return "🌖", "Waning Gibbous"
    elif position < 0.875:
        return "🌗", "Last Quarter"
    else:
        return "🌘", "Waning Crescent"

def get_visibility_emoji(visibility_meters):
    """Return visibility emoji based on meters of visibility"""
    if visibility_meters < 2000:
        return "🌫️"  # Poor visibility
    elif visibility_meters < 10000:
        return "👁️"  # Good visibility
    else:
        return "🔭"  # Excellent visibility

def format_uv_index(uv_index):
    """Format UV index for display"""
    if uv_index is not None:
        return f"UV{int(uv_index)}"
    return ""

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
    # Try StormGlass first (no fallback to Open-Meteo)
    from app.forecasts.stormglass_forecast import get_stormglass_forecast
    
    forecast, error = get_stormglass_forecast(days=days)
    
    if not forecast or "daily" not in forecast:
        return None, error
    
    # Clear any previous error if we have data
    if forecast:
        error = None
    
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
        
        # Add UV index if available
        if "max_uv_index" in data:
            simple_data["max_uv_index"] = data["max_uv_index"]
        
        # Add visibility if available
        if "min_visibility" in data:
            simple_data["min_visibility"] = data["min_visibility"]
        
        # Add moon phase if available
        if "moon_emoji" in data:
            simple_data["moon_emoji"] = data["moon_emoji"]
            simple_data["moon_phase"] = data["moon_phase"]
        
        simplified.append(simple_data)
    
    # Sort by date
    simplified.sort(key=lambda x: x["date"])
    
    return simplified, error

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
    
    try:
        # Try to parse Hebrew date format (e.g., "שישי, 12 אפריל 2025")
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
                
                forecast = get_forecast_for_date(date_str)
                if forecast:
                    return forecast
    except Exception as e:
        print(f"Error parsing slot date: {e}")
    
    # If we couldn't parse the date, try to get today's forecast
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        return get_forecast_for_date(today)
    except Exception as e:
        print(f"Error getting today's forecast: {e}")
        # Return a minimal fallback forecast to prevent UI issues
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "display_date": datetime.now().strftime("%A, %d %B %Y"),
            "max_wave_height": 0.0,
            "avg_wave_period": 0.0,
            "max_swell_height": 0.0,
            "avg_swell_period": 0.0,
            "dominant_wave_direction": "N",
            "dominant_swell_direction": "N"
        }

def format_slot_forecast(slot):
    """Format forecast data for a slot in a compact way"""
    try:
        # Calculate if the slot date is within 6 days from today
        is_within_forecast_range = False
        try:
            # Extract date from slot
            slot_date = slot.get("date", "")
            
            # Try to parse Hebrew date format (e.g., "שישי, 12 אפריל 2025")
            if "," in slot_date:
                # Handle Hebrew month names
                hebrew_month_names = {
                    "ינואר": "January", "פברואר": "February", "מרץ": "March",
                    "אפריל": "April", "מאי": "May", "יוני": "June",
                    "יולי": "July", "אוגוסט": "August", "ספטמבר": "September",
                    "אוקטובר": "October", "נובמבר": "November", "דצמבר": "December"
                }
                
                day_name, date_part = slot_date.split(",", 1)
                date_part = date_part.strip()
                
                parts = date_part.split()
                if len(parts) >= 3:  # day, month, year
                    day_num = parts[0]
                    month_name = parts[1]
                    year = parts[2]
                    
                    # Translate Hebrew month name if needed
                    if month_name in hebrew_month_names:
                        month_name = hebrew_month_names[month_name]
                    
                    # Parse the date
                    slot_date_obj = datetime.strptime(f"{day_num} {month_name} {year}", "%d %B %Y").date()
                    today_date = datetime.now().date()
                    
                    # Check if the slot is within 6 days from today
                    delta = (slot_date_obj - today_date).days
                    is_within_forecast_range = 0 <= delta <= 6
        except Exception:
            # If we can't parse the date, assume it's in range to be safe
            is_within_forecast_range = True
        
        # If not within forecast range (>6 days ahead), return empty string
        if not is_within_forecast_range:
            return ""
            
        forecast = get_forecast_for_slot(slot)
        
        if not forecast:
            return ""  # Empty string for no forecast
        
        # Get time of day for this slot to determine if we show moon phase
        is_evening = False
        if "time" in slot:
            slot_time = slot["time"]
            # Check if slot starts in evening/night (after sunset)
            if "-" in slot_time:
                start_time = slot_time.split("-")[0].strip()
                try:
                    hour = int(start_time.split(":")[0])
                    is_evening = hour >= 18 or hour < 6  # Assume evening/night hours
                except (ValueError, IndexError):
                    pass
        
        # Swell information
        swell_height = round(forecast.get("max_swell_height", 0), 1)
        swell_emoji = get_swell_emoji(swell_height)
        
        # Wind information if available
        wind_emoji = ""
        if "max_wind_speed_knots" in forecast:
            wind_speed = round(forecast.get("max_wind_speed_knots", 0), 1)
            wind_emoji = get_wind_emoji(wind_speed)
        
        # UV index (only show if 8 or higher)
        uv_text = ""
        if "max_uv_index" in forecast:
            uv_index = forecast.get("max_uv_index")
            if uv_index is not None and uv_index >= 8:
                uv_text = format_uv_index(uv_index)
        
        # Visibility emoji
        visibility_emoji = ""
        if "min_visibility" in forecast:
            visibility_emoji = get_visibility_emoji(forecast.get("min_visibility", 20000))
        
        # Moon phase emoji, only shown for evening slots
        moon_emoji = ""
        if is_evening and "moon_emoji" in forecast:
            moon_emoji = forecast.get("moon_emoji", "")
        
        # Combine all components without spaces
        # New order: swell → wind → UV (if ≥8) → visibility → moon
        return f"{swell_emoji}{wind_emoji}{uv_text}{visibility_emoji}{moon_emoji}"
    except Exception as e:
        print(f"Error formatting slot forecast: {e}")
        return ""  # Return empty string on error

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
