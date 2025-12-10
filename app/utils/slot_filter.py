from typing import Dict, List, Tuple
from app.utils.date_utils import (
    parse_hebrew_date, calculate_days_ahead, get_weekday_name,
    parse_slot_start_time, is_time_in_range
)


def apply_weather_filters(filters: Dict, forecast: Dict) -> Tuple[bool, str]:
    """Apply weather-based filters to a slot. Returns (passed, reason)."""
    if not forecast:
        return True, "OK (no forecast data)"
    max_wind = filters.get("max_wind_speed_knots")
    if max_wind is not None:
        actual_wind = forecast.get("max_wind_speed_knots", 0)
        if actual_wind > max_wind:
            return False, f"Wind {actual_wind:.0f}kt > {max_wind}kt max"
    max_wave = filters.get("max_wave_height_meters")
    if max_wave is not None:
        actual_wave = forecast.get("max_wave_height", 0)
        if actual_wave > max_wave:
            return False, f"Waves {actual_wave:.1f}m > {max_wave}m max"
    max_swell = filters.get("max_swell_height_meters")
    if max_swell is not None:
        actual_swell = forecast.get("max_swell_height", 0)
        if actual_swell > max_swell:
            return False, f"Swell {actual_swell:.1f}m > {max_swell}m max"
    min_vis = filters.get("min_visibility_meters")
    if min_vis is not None:
        actual_vis = forecast.get("min_visibility", 20000)
        if actual_vis < min_vis:
            return False, f"Visibility {actual_vis}m < {min_vis}m min"
    return True, "OK"


def apply_extended_filters(slot: Dict, slot_date, allowed_days: Dict) -> Tuple[bool, str]:
    """Apply weekday and time filters to a slot. Returns (passed, reason)."""
    if not allowed_days:
        return True, "OK (no day restrictions)"
    weekday = get_weekday_name(slot_date)
    if weekday not in allowed_days:
        return False, f"{weekday.capitalize()} not in allowed days"
    day_config = allowed_days[weekday]
    if not isinstance(day_config, dict):
        return True, "OK"
    from_time = day_config.get("from")
    to_time = day_config.get("to")
    if from_time is None or to_time is None:
        return True, "OK"
    slot_time = parse_slot_start_time(slot.get("time", ""))
    if slot_time is None:
        return True, "OK (could not parse slot time)"
    if not is_time_in_range(slot_time, from_time, to_time):
        return False, f"{slot_time.strftime('%H:%M')} not in {from_time}-{to_time}"
    return True, "OK"


def should_notify_slot(slot: Dict, config: Dict) -> Tuple[bool, str]:
    """Determine if a slot should trigger notification. Returns (should_notify, reason)."""
    slot_date_str = slot.get("date", "")
    slot_date = parse_hebrew_date(slot_date_str)
    if slot_date is None:
        return True, "OK (could not parse date)"
    days_ahead = calculate_days_ahead(slot_date)
    weather_zone = config.get("weather_zone", {})
    extended_zone = config.get("extended_zone", {})
    min_days = weather_zone.get("min_days_ahead", 0)
    weather_max = weather_zone.get("max_days_ahead", 7)
    extended_max = extended_zone.get("max_days_ahead", 14)
    if days_ahead < min_days:
        return False, f"Too soon ({days_ahead}d < {min_days}d min)"
    if days_ahead <= weather_max:
        filters = weather_zone.get("filters", {})
        if not filters:
            return True, "OK (no weather filters)"
        try:
            from app.forecasts.swell_forecast import get_forecast_for_slot
            forecast = get_forecast_for_slot(slot)
        except Exception as e:
            print(f"Error getting forecast: {e}")
            forecast = None
        return apply_weather_filters(filters, forecast)
    if days_ahead <= extended_max:
        allowed_days = extended_zone.get("allowed_days", {})
        return apply_extended_filters(slot, slot_date, allowed_days)
    return False, f"Too far ({days_ahead}d > {extended_max}d max)"


def filter_slots_by_conditions(slots: List[Dict], config: Dict) -> Tuple[List[Dict], List[str]]:
    """Filter slots based on config conditions. Returns (passed_slots, filter_log)."""
    if not config.get("enabled", False):
        return slots, []
    passed_slots = []
    filter_log = []
    for slot in slots:
        passed, reason = should_notify_slot(slot, config)
        slot_desc = f"{slot.get('date', '?')} {slot.get('time', '?')} {slot.get('service_type', '?')}"
        if passed:
            passed_slots.append(slot)
        else:
            filter_log.append(f"FILTERED: {slot_desc} - {reason}")
    return passed_slots, filter_log
