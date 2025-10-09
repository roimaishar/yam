# YAM Marine Forecast Integration

This module integrates marine weather forecasts into the YAM application, providing accurate real-time swell and wave data for Herzliya Marina using StormGlass API.

## Features

- **Marine Data**: Wave height, period, and direction forecasts
- **Wind Data**: Wind speed (in knots) and direction forecasts
- **Visibility**: Visual indicators for fog and clear conditions
- **Moon Phase**: Moon phase information for evening/night slots
- **Caching**: 6-hour local cache to reduce API calls
- **Slack Integration**: Weather data incorporated into slot notifications
- **Visual Indicators**: 
  - Wave height emoji indicators (🏝️, 🌊, 🌊🌊)
  - Wind speed emoji indicators (🍃, 💨, 🌪️)
  - Visibility emoji indicators (🌫️, 👁️, 🔭)
  - Moon phase emoji indicators (🌑, 🌒, 🌓, 🌔, 🌕, 🌖, 🌗, 🌘)

## API Provider

The integration uses [StormGlass API](https://stormglass.io/), which offers:

- High-accuracy marine forecasts (1km resolution)
- Exact location data for Herzliya Marina (32.164°N, 34.791°E)
- Multiple model ensemble for better accuracy
- Hourly resolution data
- Wave height, period, direction, swell, wind speed, and visibility
- Rate limit: 10 calls per day (managed automatically)

## Usage Examples

### Get forecast data

```python
from app.forecasts.swell_forecast import get_simplified_forecast

# Get 7-day forecast (default)
forecast = get_simplified_forecast()

# Get 3-day forecast
forecast = get_simplified_forecast(days=3)

# Example output:
# [
#   {
#     "date": "2025-04-06",
#     "display_date": "Sunday, 06 April 2025",
#     "max_wave_height": 0.5,
#     "max_swell_height": 0.5,
#     "avg_wave_period": 4.5,
#     "avg_swell_period": 4.3,
#     "dominant_wave_direction": "NW",
#     "dominant_swell_direction": "NW"
#   },
#   ...
# ]
```

### Get forecast for a specific date

```python
from app.forecasts.swell_forecast import get_forecast_for_date

# Get forecast for specific date
forecast = get_forecast_for_date("2025-04-10")

# Access specific data
swell_height = forecast.get("max_swell_height")
wave_period = forecast.get("avg_wave_period")
```

### Get forecast formatted for a slot

```python
from app.forecasts.swell_forecast import format_slot_forecast

# Format forecast for a slot (handles Hebrew date parsing)
slot = {"date": "שישי, 12 אפריל 2025", "time": "10:00 - 13:00"}
formatted = format_slot_forecast(slot)

# Example output: " 0.7m | 4.8s | NW"
```

## Forecast Range

The system retrieves forecast data for up to 16 days ahead, but only displays forecast emojis for slots within the next 6 days. 
Slots beyond the 6-day forecast window will not display any weather information (no swell, wind, UV, visibility or moon phase emojis).

This approach ensures that only the most reliable forecast data is presented to users, as marine forecasts tend to decrease in accuracy beyond 5-7 days.

## Wave Height Categories

The module uses emoji indicators to quickly visualize wave conditions:

- 🏝️ Calm sea (≤ 0.4m) - Ideal conditions
- 🌊 Moderate waves (≤ 0.8m) - Good conditions
- 🌊🌊 Large waves (> 0.8m) - Challenging conditions

## Wind Speed Categories

Wind speeds are indicated with these emoji indicators:

- 🍃 Light wind (< 5 knots) - May need motor assistance
- 💨 Moderate wind (5-14 knots) - Good sailing conditions
- 🌪️ Strong wind (> 14 knots) - Challenging conditions

## Visibility Categories

Visibility is represented with these emoji indicators:

- 🌫️ Poor visibility (< 2km) - Challenging navigation conditions
- 👁️ Good visibility (2-10km) - Adequate for navigation
- 🔭 Excellent visibility (> 10km) - Clear conditions

## UV Index

UV index is shown as a numeric value prefixed with "UV":
- UV0-UV2: Low exposure risk
- UV3-UV5: Moderate exposure risk
- UV6-UV7: High exposure risk  
- UV8-UV10: Very high exposure risk (displayed in notifications)
- UV11+: Extreme exposure risk (displayed in notifications)

**Note:** UV index is not available from StormGlass API and is not displayed in notifications.

## Moon Phase

Moon phases are shown for evening/night slots only:
- 🌑 New Moon
- 🌒 Waxing Crescent
- 🌓 First Quarter
- 🌔 Waxing Gibbous
- 🌕 Full Moon
- 🌖 Waning Gibbous
- 🌗 Last Quarter
- 🌘 Waning Crescent

## Implementation Details

The marine forecast module:

1. Fetches marine data from StormGlass API for exact Herzliya Marina location
2. Processes and caches the data locally
3. Provides helper functions to format data for notifications
4. Integrates with Slack notifier to display wave conditions
5. Manages API rate limiting (10 calls/day)

Data is cached in `app/data/stormglass_forecast.json` and refreshed every 2.4 hours. API usage is tracked in `app/data/stormglass_usage.json` to respect the daily limit.

## Configuration

The coordinates are set to Herzliya Marina:
- Latitude: 32.1640
- Longitude: 34.7914

StormGlass API key is required and must be set in `.env`:
```
STORM_GLASS_KEY=your_api_key_here
```

**Rate Limiting**: The system automatically manages the 10 calls/day limit by:
- Caching forecast data for 2.4 hours
- Tracking API usage in `app/data/stormglass_usage.json`
- Showing error messages in notifications if limit is reached
