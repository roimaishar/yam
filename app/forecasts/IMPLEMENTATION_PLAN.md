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

### Phase 3: Wave-based Slot Filtering
1. Modify `filter_slots.py` to support wave condition filtering:
   - Add "max_wave_height" parameter to filter slots
   - Example: Only show slots on days with waves under 1m

2. Update command-line arguments in `main.py`:
   - Add `--show-waves` to display wave conditions with slots
   - Add `--max-wave-height` to filter slots by wave height
   - Example: `python -m app.main monitor --max-wave-height 1.0`

### Phase 4: User Experience Improvements
1. Documentation updates:
   - Add wave forecast feature to README.md
   - Document command-line options for wave conditions
   - Add typical wave conditions for Tel Aviv area

2. Optional enhancements:
   - Add separate webhook for high-wave alerts
   - Create a dedicated command to show just the wave forecast

## Implementation Sequence

1. **Implementation Priority**:
   - Phase 3 (Wave-based Filtering): Higher priority for immediate value
   - Phase 4 (User Experience): Secondary for additional user control

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
- Small waves (≤ 0.4m): 🌊
- Medium waves (≤ 0.8m): 🌊🌊
- Large waves (> 0.8m): 🌊🌊🌊

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

1. Add wave-based filtering options (Phase 3)
2. Document new features (Phase 4)
