import json
import os
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path(__file__).parent.parent / "data" / "slot_filters.json"


def get_default_config() -> Dict[str, Any]:
    """Return default config (filtering disabled)."""
    return {
        "enabled": False,
        "weather_zone": {
            "min_days_ahead": 0,
            "max_days_ahead": 7,
            "filters": {}
        },
        "extended_zone": {
            "max_days_ahead": 14,
            "allowed_days": {}
        }
    }


def load_slot_filters() -> Dict[str, Any]:
    """Load slot filters config from file. Returns default config on error."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Slot filter config not found at {CONFIG_FILE}, using defaults (disabled)")
        return get_default_config()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        if not validate_config(config):
            print("Slot filter config validation failed, using defaults (disabled)")
            return get_default_config()
        return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading slot filter config: {e}, using defaults (disabled)")
        return get_default_config()


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate config structure. Returns False if invalid."""
    if not isinstance(config, dict):
        return False
    if "enabled" not in config:
        print("Config missing 'enabled' field")
        return False
    if not isinstance(config.get("enabled"), bool):
        print("Config 'enabled' must be boolean")
        return False
    weather_zone = config.get("weather_zone")
    if weather_zone is not None:
        if not isinstance(weather_zone, dict):
            print("Config 'weather_zone' must be an object")
            return False
        if not isinstance(weather_zone.get("min_days_ahead", 0), (int, float)):
            print("Config 'weather_zone.min_days_ahead' must be a number")
            return False
        if not isinstance(weather_zone.get("max_days_ahead", 7), (int, float)):
            print("Config 'weather_zone.max_days_ahead' must be a number")
            return False
    extended_zone = config.get("extended_zone")
    if extended_zone is not None:
        if not isinstance(extended_zone, dict):
            print("Config 'extended_zone' must be an object")
            return False
        if not isinstance(extended_zone.get("max_days_ahead", 14), (int, float)):
            print("Config 'extended_zone.max_days_ahead' must be a number")
            return False
        allowed_days = extended_zone.get("allowed_days", {})
        if not isinstance(allowed_days, dict):
            print("Config 'extended_zone.allowed_days' must be an object")
            return False
    return True
