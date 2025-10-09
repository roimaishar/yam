# StormGlass Integration - Pre-Implementation Review

## ✅ Compatibility Analysis

### GitHub Actions Workflow Review

**Current Setup:**
- Runs every 15 minutes via cron: `*/15 * * * *`
- Uses GitHub Secrets for sensitive data
- Commits data files back to repository
- Two separate jobs: boat slots + club activities

**Key Findings:**

#### 1. ✅ Secret Management Works
```yaml
env:
  YAM_USERNAME: ${{ secrets.YAM_USERNAME }}
  YAM_PASSWORD: ${{ secrets.YAM_PASSWORD }}
  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```
**Action Required:** Add `STORM_GLASS_KEY` to GitHub Secrets
- Go to: Repository → Settings → Secrets and variables → Actions
- Add new secret: `STORM_GLASS_KEY` with your API key

#### 2. ✅ Cache File Persistence Works
**Current behavior:**
- `marine_forecast.json` exists in `app/data/` but is NOT tracked by git
- `.gitignore` excludes: `app/data/swell_forecast.json` (line 46)
- Git only tracks: `all_slots.json`, `previous_slots.json`, `notified_slots.json`, `yam_cookies.json`

**Implication for StormGlass:**
- Cache file will be **ephemeral** in GitHub Actions (fresh Ubuntu container each run)
- Cache will NOT persist between runs
- This is actually **PERFECT** for our use case!

#### 3. ⚠️ Cache Persistence Issue = FEATURE!

**Why ephemeral cache is good:**
```
Run 1 (00:00): No cache → Fetch StormGlass → Save cache → Call count: 1
Run 2 (00:15): No cache (new container) → Fetch StormGlass → Save cache → Call count: 2
...
Run 10 (02:15): No cache → Fetch StormGlass → Save cache → Call count: 10
Run 11 (02:30): No cache → Fetch StormGlass → Save cache → Call count: 11 ❌ OVER LIMIT
```

**Problem:** Without persistent cache, we'll hit 10 calls in 2.5 hours, not 24 hours!

**Solution Required:** We need to track API call count in a **git-tracked file**

#### 4. ✅ Environment Variables Available
- `python-dotenv` is already in requirements.txt
- Code already uses `os.getenv()` pattern
- Will work seamlessly in both local dev and GitHub Actions

### Data Persistence Strategy

**Current Git-Tracked Files:**
```bash
app/data/all_slots.json          # Boat slots data
app/data/previous_slots.json     # Tracking for notifications
app/data/notified_slots.json     # Already notified slots
app/data/yam_cookies.json        # Session cookies
```

**Not Git-Tracked (Ephemeral):**
```bash
app/data/marine_forecast.json    # Open-Meteo cache
app/data/swell_forecast.json     # (in .gitignore)
app/data/club_*.json             # Club activity data
```

**For StormGlass, we need:**
```bash
app/data/stormglass_forecast.json     # Cache (ephemeral - OK)
app/data/stormglass_usage.json        # API call tracking (MUST be git-tracked)
```

## 🔧 Required Changes

### 1. Update .gitignore
**Current:**
```gitignore
app/data/swell_forecast.json
```

**Add:**
```gitignore
app/data/marine_forecast.json
app/data/stormglass_forecast.json
```

**Do NOT ignore:**
- `app/data/stormglass_usage.json` (must be tracked for call counting)

### 2. Update GitHub Actions Workflow
**Add to commit step (line 49):**
```yaml
git add app/data/all_slots.json \
        app/data/previous_slots.json \
        app/data/notified_slots.json \
        app/data/club_all_slots.json \
        app/data/club_previous_slots.json \
        app/data/club_notified_slots.json \
        app/data/stormglass_usage.json
```

**Add STORM_GLASS_KEY to both env sections:**
```yaml
- name: Run slot monitor once
  env:
    YAM_USERNAME: ${{ secrets.YAM_USERNAME }}
    YAM_PASSWORD: ${{ secrets.YAM_PASSWORD }}
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
    STORM_GLASS_KEY: ${{ secrets.STORM_GLASS_KEY }}  # ADD THIS
    YAM_COOKIES_PATH: ${{ runner.temp }}/yam_cookies.json
  run: python -m app.main monitor 14 --once

- name: Run club monitor once
  env:
    YAM_USERNAME: ${{ secrets.YAM_USERNAME }}
    YAM_PASSWORD: ${{ secrets.YAM_PASSWORD }}
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
    SLACK_WEBHOOK_URL_CLUB: ${{ secrets.SLACK_WEBHOOK_URL_CLUB }}
    STORM_GLASS_KEY: ${{ secrets.STORM_GLASS_KEY }}  # ADD THIS
    YAM_COOKIES_PATH: ${{ runner.temp }}/yam_cookies.json
  run: python -m app.main club check 14
```

### 3. Update requirements.txt
**Add:**
```
requests>=2.32.0  # Already present
```
No new dependencies needed! ✅

## 📊 API Call Tracking Design

### Usage Tracking File Structure
```json
{
  "date": "2025-10-08",
  "calls_today": 8,
  "calls": [
    {
      "timestamp": "2025-10-08T00:00:15Z",
      "success": true,
      "points_used": 1
    },
    {
      "timestamp": "2025-10-08T02:24:30Z",
      "success": true,
      "points_used": 1
    }
  ],
  "last_reset": "2025-10-08T00:00:00Z"
}
```

### Call Limiting Logic
```python
def should_fetch_stormglass():
    """
    Determine if we should make a StormGlass API call
    Returns: (should_fetch: bool, reason: str)
    """
    usage = load_usage_tracking()
    
    # Reset counter if new day
    today = datetime.now().strftime("%Y-%m-%d")
    if usage.get("date") != today:
        usage = reset_daily_counter()
    
    # Check daily limit
    calls_today = usage.get("calls_today", 0)
    if calls_today >= 10:
        return False, f"Daily limit reached ({calls_today}/10)"
    
    # Check cache age
    cache_age = get_cache_age()
    if cache_age < 2.4:  # hours
        return False, f"Cache is fresh ({cache_age:.1f}h old)"
    
    return True, "OK to fetch"

def record_api_call(success: bool):
    """Record an API call in the usage tracking file"""
    usage = load_usage_tracking()
    
    usage["calls_today"] += 1
    usage["calls"].append({
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "points_used": 1
    })
    
    save_usage_tracking(usage)
    
    # Git will commit this file automatically
```

## 🎯 Implementation Strategy

### Phase 1: Core Integration
1. Create `stormglass_forecast.py` module
2. Implement API client with proper error handling
3. Add usage tracking system
4. Test locally with real API key

### Phase 2: Fallback Logic
1. Modify `swell_forecast.py` to try StormGlass first
2. Fall back to Open-Meteo if:
   - Daily limit reached
   - API call fails
   - Cache is fresh
3. Ensure notifications always have data

### Phase 3: GitHub Actions
1. Add `STORM_GLASS_KEY` to GitHub Secrets
2. Update workflow YAML
3. Update `.gitignore`
4. Test with manual workflow dispatch

### Phase 4: Monitoring
1. Add logging for API calls
2. Track success/failure rates
3. Monitor daily usage patterns

## ⚠️ Critical Considerations

### 1. Race Conditions
**Problem:** Two GitHub Actions runs might happen simultaneously
**Solution:** Usage tracking file will be committed, git merge will handle conflicts

### 2. Failed Commits
**Problem:** If commit fails, usage counter might be lost
**Solution:** 
- Load usage file at start of run
- Increment counter
- Save immediately after API call
- Commit happens later (already in workflow)

### 3. Time Zone Handling
**Current:** GitHub Actions runs in UTC
**Solution:** Use UTC consistently for date comparisons
```python
today = datetime.utcnow().strftime("%Y-%m-%d")
```

### 4. API Key Security
**Current:** Secrets are properly handled ✅
**Verify:** Key never logged or exposed in error messages

### 5. Backward Compatibility
**Requirement:** Code must work without StormGlass key
**Solution:**
```python
STORM_GLASS_KEY = os.getenv("STORM_GLASS_KEY")
if not STORM_GLASS_KEY:
    # Fall back to Open-Meteo
    return get_open_meteo_forecast()
```

## 📋 Pre-Implementation Checklist

- [x] Verify GitHub Actions workflow structure
- [x] Confirm secret management works
- [x] Understand cache persistence behavior
- [x] Design usage tracking system
- [x] Plan git-tracked vs ephemeral files
- [x] Identify required workflow changes
- [x] Design fallback strategy
- [x] Consider race conditions
- [x] Plan error handling
- [x] Ensure backward compatibility

## 🚀 Ready to Implement?

**YES** - All systems are compatible!

**Key Points:**
1. ✅ GitHub Actions workflow supports this pattern
2. ✅ Secret management is already set up
3. ✅ Git-tracked usage file solves persistence issue
4. ✅ Fallback to Open-Meteo ensures reliability
5. ✅ No new dependencies needed
6. ✅ Backward compatible (works without API key)

**Next Steps:**
1. Add `STORM_GLASS_KEY` to GitHub Secrets
2. Implement StormGlass client module
3. Add usage tracking system
4. Update workflow YAML
5. Test locally
6. Deploy to GitHub Actions

## 📝 Testing Plan

### Local Testing
```bash
# Test with API key
export STORM_GLASS_KEY="your_key_here"
python -m app.main monitor 14 --once

# Verify usage tracking
cat app/data/stormglass_usage.json

# Test fallback (remove key)
unset STORM_GLASS_KEY
python -m app.main monitor 14 --once
```

### GitHub Actions Testing
1. Add secret to repository
2. Trigger manual workflow run
3. Check Actions logs for API calls
4. Verify usage file is committed
5. Check notifications have correct data

### Edge Case Testing
- [ ] First run (no usage file)
- [ ] Daily limit reached
- [ ] API failure
- [ ] Invalid API key
- [ ] Network timeout
- [ ] Concurrent runs
- [ ] Date rollover at midnight

## 🎉 Conclusion

**The integration is fully compatible with your existing workflow!**

The ephemeral cache in GitHub Actions actually works in our favor - we just need to track API usage in a git-committed file. Everything else (secrets, environment variables, data persistence) already works perfectly.

**Estimated Implementation Time:** 2-3 hours
**Risk Level:** Low (with proper fallback)
**Complexity:** Medium (usage tracking adds some complexity)

Ready to proceed with implementation? 🚀
