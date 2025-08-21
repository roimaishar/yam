import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Use YAM_COOKIES_PATH env var if set, otherwise fall back to default location
DEFAULT_COOKIES_PATH = os.path.join(BASE_DIR, "..", "cookies", "yam_cookies.json")
COOKIES_FILE = os.getenv("YAM_COOKIES_PATH", DEFAULT_COOKIES_PATH)

ALL_SLOTS_FILE = os.path.join(DATA_DIR, "all_slots.json")

def get_urls_to_scrape():
    return [
        "https://yamonline.custhelp.com/app/calendar_slots"
    ]
