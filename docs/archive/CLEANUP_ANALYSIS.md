# Project Cleanup Analysis

## Files to Keep (Essential)

### Core Application
- `README.md` - Main documentation (NEEDS UPDATE)
- `requirements.txt` - Dependencies
- `run_scraper.sh` - Convenience script
- `.gitignore` - Git configuration
- `.env` - Environment variables (gitignored)

### Application Code
- `app/` - All application code (keep)
  - `main.py` - Entry point
  - `forecasts/` - Forecast modules
  - `monitors/` - Monitoring modules
  - `scrapers/` - Scraping modules
  - `utils/` - Utility modules
  - `data/` - Data files (some tracked, some not)

### GitHub Actions
- `.github/workflows/scraper.yml` - CI/CD workflow

## Files to REMOVE (Redundant/Temporary)

### Test Files (Created During Development)
- `test_ci_cookie_scraper.py` - CI testing
- `test_compact_notification.py` - Notification testing
- `test_enhanced_notification.py` - Notification testing
- `test_final_notification.py` - Notification testing
- `test_forecast_emojis.py` - Forecast testing
- `test_forecast_fix.py` - Bug fix testing
- `test_forecast_range.py` - Forecast testing
- `test_no_emoji_calm_sea.py` - Emoji testing
- `test_notification.py` - Notification testing
- `test_uv_format.py` - UV format testing

### Diagnostic Scripts (Debugging Tools)
- `check_api.py` - API checking
- `check_marine_forecast.py` - Marine forecast checking
- `check_weather_api.py` - Weather API checking
- `ci_browser_test.py` - Browser testing
- `diagnose_forecast.py` - Forecast diagnosis
- `validate_forecast_accuracy.py` - Accuracy validation
- `example_notifications.py` - Notification examples
- `show_notification.py` - Notification display

### Temporary Data Files
- `fixed_forecast.json` - Old forecast data
- `marine_api_raw.json` - Raw API response
- `weather_api_raw.json` - Raw API response
- `open_meteo_sample.json` - Sample data
- `notification_example.txt` - Example text
- `out` - Output file

### Documentation (Redundant/Outdated)
- `FORECAST_BUG_FIX.md` - Bug fix documentation (historical, can archive)
- `WEATHER_FORECAST_ANALYSIS.md` - Analysis (historical, can archive)
- `STORMGLASS_INTEGRATION_PLAN.md` - Implementation plan (historical)
- `STORMGLASS_IMPLEMENTATION_SUMMARY.md` - Summary (historical)

## Documentation Updates Needed

### README.md
**Current Issues:**
- Still mentions Open-Meteo as the forecast source
- Doesn't mention StormGlass
- Forecast accuracy section needs update
- Coordinates information outdated

**Updates Needed:**
1. Update forecast provider from Open-Meteo to StormGlass
2. Mention 10 calls/day limit
3. Update coordinates to show correct Herzliya Marina location
4. Add STORM_GLASS_KEY to environment variables section
5. Update GitHub Secrets section

### app/forecasts/README.md
**Current Issues:**
- Describes Open-Meteo API
- Doesn't mention StormGlass
- API provider section outdated

**Updates Needed:**
1. Update API provider to StormGlass
2. Mention rate limiting (10 calls/day)
3. Update accuracy information
4. Note that UV index is not available from StormGlass

## Recommended Actions

### Phase 1: Documentation Updates
1. Update README.md with StormGlass information
2. Update app/forecasts/README.md
3. Keep historical docs but move to `docs/archive/` folder

### Phase 2: File Cleanup
1. Remove all test_*.py files (15 files)
2. Remove all check_*.py and diagnostic files (7 files)
3. Remove temporary data files (6 files)
4. Remove example/output files (3 files)

### Phase 3: Archive Historical Docs
1. Create `docs/archive/` folder
2. Move historical documentation there
3. Keep them for reference but out of root

### Phase 4: Testing & Deployment
1. Test scraper locally
2. Verify forecast works
3. Commit changes
4. Push and verify GitHub Actions

## Total Files to Remove: 31 files
## Total Files to Archive: 4 docs
## Total Files to Update: 2 docs
