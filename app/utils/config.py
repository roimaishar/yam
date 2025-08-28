import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Use YAM_COOKIES_PATH env var if set, otherwise fall back to default location
DEFAULT_COOKIES_PATH = os.path.join(BASE_DIR, "..", "cookies", "yam_cookies.json")
COOKIES_FILE = os.getenv("YAM_COOKIES_PATH", DEFAULT_COOKIES_PATH)

# Boat monitoring files (existing)
ALL_SLOTS_FILE = os.path.join(DATA_DIR, "all_slots.json")

# Club monitoring files (new)
CLUB_ALL_SLOTS_FILE = os.path.join(DATA_DIR, "club_all_slots.json")
CLUB_PREVIOUS_SLOTS_FILE = os.path.join(DATA_DIR, "club_previous_slots.json")
CLUB_NOTIFIED_SLOTS_FILE = os.path.join(DATA_DIR, "club_notified_slots.json")

def get_urls_to_scrape():
    return [
        "https://yamonline.custhelp.com/app/calendar_slots"
    ]

def get_club_urls_to_scrape():
    return [
        "https://yamonline.custhelp.com/app/calendar_club"
    ]
