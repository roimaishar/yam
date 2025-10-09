import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Constants
STORMGLASS_CACHE_FILE = Path(__file__).parent.parent / "data" / "stormglass_forecast.json"
STORMGLASS_USAGE_FILE = Path(__file__).parent.parent / "data" / "stormglass_usage.json"
STORMGLASS_CACHE_DURATION = 2.4  # Hours (10 calls per day = 24h / 10)
STORMGLASS_MAX_CALLS_PER_DAY = 10

# Herzliya Marina coordinates
HERZLIYA_LAT = 32.1640
HERZLIYA_LNG = 34.7914

def get_stormglass_forecast(days=7):
    """
    Get marine forecast from StormGlass API with usage tracking
    Returns: (forecast_data, error_message)
    """
    api_key = os.getenv("STORM_GLASS_KEY")
    
    if not api_key:
        return None, "⚠️ StormGlass API key not configured"
    
    # Check if we should fetch (respects daily limit and cache)
    should_fetch, reason = should_fetch_stormglass()
    
    if not should_fetch:
        # Try to use cached data
        cached = load_stormglass_cache()
        if cached and is_cache_valid(cached):
            return cached, None
        return None, f"⚠️ {reason}"
    
    # Fetch from StormGlass API
    try:
        end_time = datetime.utcnow() + timedelta(days=days)
        
        params = {
            'lat': HERZLIYA_LAT,
            'lng': HERZLIYA_LNG,
            'params': ','.join([
                'waveHeight',
                'wavePeriod', 
                'waveDirection',
                'swellHeight',
                'swellPeriod',
                'swellDirection',
                'windSpeed',
                'windDirection',
                'visibility'
            ]),
            'start': datetime.utcnow().isoformat(),
            'end': end_time.isoformat()
        }
        
        headers = {
            'Authorization': api_key
        }
        
        response = requests.get(
            'https://api.stormglass.io/v2/weather/point',
            params=params,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Process and cache the data
        processed = process_stormglass_data(data)
        save_stormglass_cache(processed)
        
        # Record successful API call
        record_api_call(success=True)
        
        return processed, None
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"⚠️ StormGlass API error: {e.response.status_code}"
        record_api_call(success=False)
        return None, error_msg
        
    except requests.exceptions.Timeout:
        error_msg = "⚠️ StormGlass API timeout"
        record_api_call(success=False)
        return None, error_msg
        
    except Exception as e:
        error_msg = f"⚠️ StormGlass error: {str(e)[:50]}"
        record_api_call(success=False)
        return None, error_msg

def process_stormglass_data(api_data):
    """Process StormGlass API response into our format"""
    daily_data = {}
    
    if 'hours' not in api_data:
        return None
    
    # Group hourly data by date
    for hour_data in api_data['hours']:
        timestamp = hour_data['time']
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d')
        
        if date_str not in daily_data:
            daily_data[date_str] = {
                'wave_heights': [],
                'swell_heights': [],
                'wave_periods': [],
                'swell_periods': [],
                'wave_directions': [],
                'swell_directions': [],
                'wind_speeds': [],
                'wind_directions': [],
                'visibilities': []
            }
        
        # Extract values (StormGlass returns dict with sources, we take first value)
        def get_value(data, key):
            if key in data and data[key]:
                if isinstance(data[key], dict):
                    # Get first available source value
                    for source_key in data[key]:
                        if data[key][source_key] is not None:
                            return data[key][source_key]
                return data[key]
            return None
        
        wave_height = get_value(hour_data, 'waveHeight')
        if wave_height is not None:
            daily_data[date_str]['wave_heights'].append(wave_height)
        
        swell_height = get_value(hour_data, 'swellHeight')
        if swell_height is not None:
            daily_data[date_str]['swell_heights'].append(swell_height)
        
        wave_period = get_value(hour_data, 'wavePeriod')
        if wave_period is not None:
            daily_data[date_str]['wave_periods'].append(wave_period)
        
        swell_period = get_value(hour_data, 'swellPeriod')
        if swell_period is not None:
            daily_data[date_str]['swell_periods'].append(swell_period)
        
        wave_dir = get_value(hour_data, 'waveDirection')
        if wave_dir is not None:
            daily_data[date_str]['wave_directions'].append(wave_dir)
        
        swell_dir = get_value(hour_data, 'swellDirection')
        if swell_dir is not None:
            daily_data[date_str]['swell_directions'].append(swell_dir)
        
        wind_speed = get_value(hour_data, 'windSpeed')
        if wind_speed is not None:
            daily_data[date_str]['wind_speeds'].append(wind_speed)
        
        wind_dir = get_value(hour_data, 'windDirection')
        if wind_dir is not None:
            daily_data[date_str]['wind_directions'].append(wind_dir)
        
        visibility = get_value(hour_data, 'visibility')
        if visibility is not None:
            daily_data[date_str]['visibilities'].append(visibility)
    
    # Calculate daily aggregates
    from app.forecasts.swell_forecast import (
        get_dominant_direction, 
        calculate_moon_phase
    )
    
    daily_forecasts = {}
    for date_str, data in daily_data.items():
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        moon_emoji, moon_phase = calculate_moon_phase(date_obj)
        
        daily_forecasts[date_str] = {
            'date': date_str,
            'display_date': date_obj.strftime('%A, %d %B %Y'),
            'max_wave_height': max(data['wave_heights']) if data['wave_heights'] else 0.0,
            'max_swell_height': max(data['swell_heights']) if data['swell_heights'] else 0.0,
            'avg_wave_period': sum(data['wave_periods']) / len(data['wave_periods']) if data['wave_periods'] else 0.0,
            'avg_swell_period': sum(data['swell_periods']) / len(data['swell_periods']) if data['swell_periods'] else 0.0,
            'dominant_wave_direction': get_dominant_direction(data['wave_directions']) if data['wave_directions'] else None,
            'dominant_swell_direction': get_dominant_direction(data['swell_directions']) if data['swell_directions'] else None,
            'max_wind_speed_knots': max(data['wind_speeds']) * 1.94384 if data['wind_speeds'] else 0.0,  # m/s to knots
            'avg_wind_speed_knots': (sum(data['wind_speeds']) / len(data['wind_speeds'])) * 1.94384 if data['wind_speeds'] else 0.0,
            'dominant_wind_direction': get_dominant_direction(data['wind_directions']) if data['wind_directions'] else None,
            'max_uv_index': None,  # UV data not available from StormGlass weather endpoint
            'min_visibility': min(data['visibilities']) * 1000 if data['visibilities'] else 20000,  # km to meters
            'moon_emoji': moon_emoji,
            'moon_phase': moon_phase,
            'sunrise': None,
            'sunset': None
        }
    
    return {
        'metadata': {
            'latitude': HERZLIYA_LAT,
            'longitude': HERZLIYA_LNG,
            'timezone': 'Asia/Jerusalem',
            'generated_at': datetime.now().isoformat(),
            'source': 'StormGlass API'
        },
        'daily': daily_forecasts
    }

def should_fetch_stormglass():
    """
    Check if we should make a StormGlass API call
    Returns: (should_fetch: bool, reason: str)
    """
    # Check cache age first
    if os.path.exists(STORMGLASS_CACHE_FILE):
        try:
            with open(STORMGLASS_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            generated_at = datetime.fromisoformat(cache_data['metadata']['generated_at'])
            age_hours = (datetime.now() - generated_at).total_seconds() / 3600
            
            if age_hours < STORMGLASS_CACHE_DURATION:
                return False, f"Cache fresh ({age_hours:.1f}h old)"
        except Exception:
            pass
    
    # Check daily limit
    usage = load_usage_tracking()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    if usage.get('date') != today:
        # New day, reset counter
        return True, "New day, OK to fetch"
    
    calls_today = usage.get('calls_today', 0)
    if calls_today >= STORMGLASS_MAX_CALLS_PER_DAY:
        return False, f"Daily limit reached ({calls_today}/{STORMGLASS_MAX_CALLS_PER_DAY})"
    
    return True, "OK to fetch"

def load_usage_tracking():
    """Load API usage tracking data"""
    if not os.path.exists(STORMGLASS_USAGE_FILE):
        return {
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'calls_today': 0,
            'calls': []
        }
    
    try:
        with open(STORMGLASS_USAGE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'calls_today': 0,
            'calls': []
        }

def save_usage_tracking(usage_data):
    """Save API usage tracking data"""
    os.makedirs(os.path.dirname(STORMGLASS_USAGE_FILE), exist_ok=True)
    with open(STORMGLASS_USAGE_FILE, 'w') as f:
        json.dump(usage_data, f, indent=2)

def record_api_call(success: bool):
    """Record an API call in the usage tracking file"""
    usage = load_usage_tracking()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Reset if new day
    if usage.get('date') != today:
        usage = {
            'date': today,
            'calls_today': 0,
            'calls': []
        }
    
    usage['calls_today'] += 1
    usage['calls'].append({
        'timestamp': datetime.utcnow().isoformat(),
        'success': success
    })
    
    save_usage_tracking(usage)

def load_stormglass_cache():
    """Load cached StormGlass forecast"""
    if not os.path.exists(STORMGLASS_CACHE_FILE):
        return None
    
    try:
        with open(STORMGLASS_CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def save_stormglass_cache(forecast_data):
    """Save StormGlass forecast to cache"""
    os.makedirs(os.path.dirname(STORMGLASS_CACHE_FILE), exist_ok=True)
    with open(STORMGLASS_CACHE_FILE, 'w') as f:
        json.dump(forecast_data, f, indent=2)

def is_cache_valid(cache_data):
    """Check if cached data is still valid"""
    try:
        generated_at = datetime.fromisoformat(cache_data['metadata']['generated_at'])
        age_hours = (datetime.now() - generated_at).total_seconds() / 3600
        return age_hours < 6  # Use cache up to 6 hours as fallback
    except Exception:
        return False
