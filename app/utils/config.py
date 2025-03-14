import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIES_FILE = os.path.join(DATA_DIR, "yam_cookies.json")
ALL_SLOTS_FILE = os.path.join(DATA_DIR, "all_slots.json")
ALL_CALENDAR_HTML_FILE = os.path.join(DATA_DIR, "all_calendar_html.json")
ALL_EXTRACTED_DATA_FILE = os.path.join(DATA_DIR, "all_extracted_data.json")

def get_urls_to_scrape():
    return [
        "https://yamonline.custhelp.com/app/calendar_slots"
    ]
