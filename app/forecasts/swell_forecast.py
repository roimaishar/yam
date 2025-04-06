import requests
import json
from datetime import datetime
import os
from pathlib import Path

# Constants
FORECAST_CACHE_FILE = Path(__file__).parent.parent / "data" / "swell_forecast.json"
FORECAST_CACHE_DURATION = 6  # Hours before refreshing forecast

# Israel coastal coordinates (Herzliya Marina)
DEFAULT_LATITUDE = 32.1640
DEFAULT_LONGITUDE = 34.7914

def get_swell_forecast(days=7, latitude=DEFAULT_LATITUDE, longitude=DEFAULT_LONGITUDE):
    """
    Get swell forecast for the specified number of days
    Uses Open-Meteo Marine Weather API
    
    Args:
        days: Number of days to forecast (max 16)
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary containing daily swell forecasts
    """
    # Check if we have a recent cached forecast
    if should_use_cached_forecast():
        return load_cached_forecast()
    
    # Limit to 16 days (Open-Meteo maximum)
    days = min(days, 16)
    
    # Construct Open-Meteo API URL
    url = (
        f"https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={latitude}&longitude={longitude}"
        f"&hourly=wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction,swell_wave_period"
        f"&timezone=Asia/Jerusalem"
        f"&forecast_days={days}"
    )
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Process the data into a more usable format
        processed_forecast = process_forecast_data(data)
        
        # Cache the forecast
        save_forecast_to_cache(processed_forecast)
        
        return processed_forecast
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching swell forecast: {e}")
        
        # If we have a cached forecast (even if expired), return it as fallback
        if os.path.exists(FORECAST_CACHE_FILE):
            return load_cached_forecast()
        
        return None

def process_forecast_data(data):
    """Process the raw API response into a more usable format"""
    if not data or "hourly" not in data:
        return None
    
    # Extract hourly data
    times = data["hourly"]["time"]
    wave_heights = data["hourly"]["wave_height"]
    wave_directions = data["hourly"]["wave_direction"]
    wave_periods = data["hourly"]["wave_period"]
    swell_heights = data["hourly"]["swell_wave_height"]
    swell_directions = data["hourly"]["swell_wave_direction"]
    swell_periods = data["hourly"]["swell_wave_period"]
    
    # Group by day
    daily_forecasts = {}
    current_date = None
    daily_data = None
    
    for i, time_str in enumerate(times):
        # Parse the time
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        date_str = time_obj.strftime("%Y-%m-%d")
        
        # Start a new day if needed
        if date_str != current_date:
            if current_date and daily_data:
                daily_forecasts[current_date] = daily_data
            
            current_date = date_str
            daily_data = {
                "date": current_date,
                "display_date": time_obj.strftime("%A, %d %B %Y"),
                "hours": [],
                "max_wave_height": 0,
                "max_swell_height": 0,
                "avg_wave_period": 0,
                "avg_swell_period": 0,
                "dominant_wave_direction": None,
                "dominant_swell_direction": None
            }
        
        # Add hourly data
        if daily_data:
            hour_data = {
                "time": time_obj.strftime("%H:%M"),
                "wave_height": wave_heights[i],
                "wave_direction": wave_directions[i],
                "wave_period": wave_periods[i],
                "swell_height": swell_heights[i],
                "swell_direction": swell_directions[i],
                "swell_period": swell_periods[i]
            }
            daily_data["hours"].append(hour_data)
            
            # Update max values
            daily_data["max_wave_height"] = max(daily_data["max_wave_height"], wave_heights[i])
            daily_data["max_swell_height"] = max(daily_data["max_swell_height"], swell_heights[i])
    
    # Don't forget to add the last day
    if current_date and daily_data:
        # Calculate averages and dominant directions
        if daily_data["hours"]:
            # Average periods
            daily_data["avg_wave_period"] = sum(h["wave_period"] for h in daily_data["hours"]) / len(daily_data["hours"])
            daily_data["avg_swell_period"] = sum(h["swell_period"] for h in daily_data["hours"]) / len(daily_data["hours"])
            
            # Find dominant directions (most frequent)
            wave_dirs = {}
            swell_dirs = {}
            for h in daily_data["hours"]:
                wave_dir = direction_to_cardinal(h["wave_direction"])
                swell_dir = direction_to_cardinal(h["swell_direction"])
                wave_dirs[wave_dir] = wave_dirs.get(wave_dir, 0) + 1
                swell_dirs[swell_dir] = swell_dirs.get(swell_dir, 0) + 1
            
            daily_data["dominant_wave_direction"] = max(wave_dirs.items(), key=lambda x: x[1])[0]
            daily_data["dominant_swell_direction"] = max(swell_dirs.items(), key=lambda x: x[1])[0]
        
        daily_forecasts[current_date] = daily_data
    
    # Add metadata
    result = {
        "metadata": {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
            "generated_at": datetime.now().isoformat(),
            "source": "Open-Meteo Marine API"
        },
        "daily": daily_forecasts
    }
    
    return result

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
        # If there's any issue with the cache file, don't use it
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
        # Ensure the data directory exists
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
        simplified.append({
            "date": date,
            "display_date": data["display_date"],
            "max_wave_height": round(data["max_wave_height"], 1),
            "max_swell_height": round(data["max_swell_height"], 1),
            "avg_wave_period": round(data["avg_wave_period"], 1),
            "avg_swell_period": round(data["avg_swell_period"], 1),
            "dominant_wave_direction": data["dominant_wave_direction"],
            "dominant_swell_direction": data["dominant_swell_direction"]
        })
    
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
    
    swell_height = round(forecast.get("max_swell_height", 0), 1)
    swell_period = round(forecast.get("avg_swell_period", 0), 1)
    swell_direction = forecast.get("dominant_swell_direction", "")
    
    swell_emoji = get_swell_emoji(swell_height)
    
    # Format: [emoji] Height m | Period s | Direction
    return f"{swell_emoji} {swell_height}m | {swell_period}s | {swell_direction}"

if __name__ == "__main__":
    # Test the function when run directly
    forecast = get_simplified_forecast(days=5)
    if forecast:
        print(json.dumps(forecast, indent=2))
    else:
        print("Failed to retrieve forecast")
