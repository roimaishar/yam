# YAM Swell Forecast Integration Plan

## Requirements Validation

1. **Free Marine API Service**
   - ✅ Open-Meteo Marine API is free with no API key required
   - ✅ No usage limits specified (reasonable usage assumed)
   - ✅ No registration required

2. **Israel Coverage**
   - ✅ Confirmed with test query for Herzliya Marina coordinates (32.1640, 34.7914)
   - ✅ Returns real data for Israeli coastal waters
   - ✅ Swell direction (NW) matches typical Mediterranean patterns

3. **Swell Data Availability**
   - ✅ Provides wave_height, wave_direction, wave_period
   - ✅ Provides swell_wave_height, swell_wave_direction, swell_wave_period
   - ✅ Forecasts for up to 16 days (exceeding our 7-day requirement)
   - ✅ Hourly resolution

## Plan

### Phase 1: Core Forecast Functionality (Complete)
1. ✅ Implement `swell_forecast.py` module with Open-Meteo integration
2. ✅ Add caching to reduce API calls (6-hour cache duration)
3. ✅ Process raw API data into useful daily summaries
4. ✅ Implement fallback to cached data when API is unavailable
5. ✅ Test with Israeli coordinates

### Phase 2: Slot Notification Enhancement (Complete)
1. ✅ Modify `SlackNotifier._send_formatted_notification` to include swell forecasts
2. ✅ Add wave height emojis (🌊, 🌊🌊, 🌊🌊🌊) based on height categories
3. ✅ Include swell period and direction in notification
4. ✅ Add 3-day forecast summary to notifications
5. ✅ Enhance mobile notification format with swell data

### Phase 2: Wind Data Integration (Complete)
1. **Expand API Calls**:
   - Maintain marine API call for wave data
   - Add weather API call for wind data (speed and direction)
   - Use same location coordinates for both calls

2. **Process Wind Data**:
   - Convert wind speeds from m/s to knots (1 m/s ≈ 1.94384 knots)
   - Calculate daily maximum and average wind speeds
   - Determine dominant wind direction for each day

3. **Visual Indicators**:
   - Add wind emoji system based on speed:
     - 🍃 Light wind (< 5 knots)
     - 💨 Moderate wind (5-14 knots)
     - 🌪️ Strong wind (> 14 knots)

4. **Notification Integration**:
   - Update slot forecast format to include wind data
   - Format: Emoji-only indicators `[Wave emoji][Wind emoji]`
   - Examples: `🏝️🍃` (calm sea, light wind), `🌊🌪️` (moderate waves, strong wind)
   - Ensure the data is relevant to the slot's date and time

### Phase 3: Extended Weather Features (Complete)
1. **UV Index Integration**:
   - Added UV index data to forecasts using Open-Meteo API
   - Included daily maximum UV index in forecast data
   - Added numeric UV index representation (UV0-UV11+) before weather emojis
   - Updated the API URL to include `uv_index` in hourly parameters and `uv_index_max` in daily parameters

2. **Visibility Integration**:
   - Added visibility data from Open-Meteo API (measured in meters)
   - Created emoji indicators for visibility conditions:
     - 🌫️ Poor visibility (< 2km) - Challenging navigation conditions
     - 👁️ Good visibility (2-10km) - Adequate for navigation
     - 🔭 Excellent visibility (> 10km) - Clear conditions
   - Processed hourly data to get minimum visibility per slot

3. **Moon Phase Integration**:
   - Implemented calculation-based moon phase determination without external API
   - Added moon phase emoji indicators (🌑, 🌒, 🌓, 🌔, 🌕, 🌖, 🌗, 🌘)
   - Show moon phase only for evening/night slots (after 18:00 or before 06:00)
   - Used a reference new moon date (2000-01-06) for calculations

4. **Notification Format Updates**:
   - Combined all weather indicators in a compact format with no spaces
   - Order: UV Index → Wave → Wind → Visibility → Moon Phase
   - Example: `UV7🏝️🌪️🌫️🌓` (UV index 7, calm waves, strong wind, poor visibility, first quarter moon)

### Phase 4: Wave-based Slot Filtering
1. Modify `filter_slots.py` to support wave condition filtering:
   - Add "max_wave_height" parameter to filter slots
   - Example: Only show slots on days with waves under 1m

2. Update command-line arguments in `main.py`:
   - Add `--show-waves` to display wave conditions with slots
   - Add `--max-wave-height` to filter slots by wave height
   - Example: `python -m app.main monitor --max-wave-height 1.0`

## Implementation Sequence

1. **Implementation Priority**:
   - Phase 4 (User Experience): Higher priority for immediate value
   - Phase 3 (Wave-based Filtering): Secondary for additional user control

2. **Core Files to Modify**:
   - `app/utils/filter_slots.py`: Add wave-based filtering
   - `app/main.py`: Add command-line arguments

3. **Testing Strategy**:
   - Test API reliability over several days
   - Compare with other sources (Israel Meteorological Service website)
   - Test with different wave conditions

4. **Rollout Approach**:
   - Add as non-blocking feature (graceful degradation if API fails)
   - Ensure caching prevents excessive API calls
   - Monitor API reliability over time

## Technical Considerations

1. **API Reliability**:
   - Implement robust error handling
   - Cache forecasts for 6+ hours to reduce dependency on API

2. **Data Processing**:
   - Daily summaries make the forecast more digestible
   - Format wave data to be visually intuitive (emojis, colors)

3. **Integration Strategy**:
   - Add as an enhancement without breaking existing functionality
   - Make wave-related filtering options but keep them optional

## Implementation Notes

### Wave Height Categories
- Calm sea (≤ 0.4m): 🏝️
- Moderate waves (≤ 0.8m): 🌊
- Large waves (> 0.8m): 🌊🌊

### Data Format
Compact swell data format in notifications:
```
🌊 0.5m | 4.5s | NW
```

Where:
- First part shows wave emoji and height in meters
- Second part shows wave period in seconds
- Third part shows dominant swell direction

## Next Steps (Implementation Order)

1. Document new features (Phase 4)
