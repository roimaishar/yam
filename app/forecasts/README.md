# YAM Swell Forecast Integration

This module integrates marine weather forecasts into the YAM application, providing real-time swell and wave data for Herzliya Marina.

## Features

- **Marine Data**: Wave height, period, and direction forecasts
- **Wind Data**: Wind speed (in knots) and direction forecasts
- **UV Index**: Daily maximum UV index with numeric indicator
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

The integration uses [Open-Meteo Marine Weather API](https://open-meteo.com/en/docs/marine-weather-api), which offers:

- Free access with no API key required
- Global coverage including Israeli coastal waters
- Hourly resolution data for up to 16 days
- Wave height, period, and direction data

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

**Note:** Only UV values of 8 or higher (very high or extreme risk) are shown in the notifications.

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

The swell forecast module:

1. Fetches marine data from Open-Meteo API
2. Processes and caches the data locally
3. Provides helper functions to format data for notifications
4. Integrates with Slack notifier to display wave conditions

Data is cached in the `app/data/swell_forecast.json` file and refreshed every 6 hours to minimize API calls.

## Configuration

The default coordinates are set to Herzliya Marina:
- Latitude: 32.1640
- Longitude: 34.7914

These can be overridden in the `get_swell_forecast()` function if needed.
