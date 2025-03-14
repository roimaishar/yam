import asyncio
import sys
from app.scrapers.cookie_scraper import scrape_calendar_slots_for_days
from app.utils.extract_data import process_all_calendar_files

async def run_scraper():
    # Modified to only run calendar scraper by default
    await scrape_calendar_slots_for_days(14)
    
async def scrape_calendar(days=14):
    await scrape_calendar_slots_for_days(days)
    
def extract_data():
    process_all_calendar_files()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [scrape|calendar|extract]")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "scrape":
        # Now 'scrape' command also runs the calendar scraper
        asyncio.run(run_scraper())
    elif command == "calendar":
        days = 14
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                print(f"Invalid number of days: {sys.argv[2]}. Using default: 14 days.")
        asyncio.run(scrape_calendar(days))
    elif command == "extract":
        extract_data()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: scrape, calendar, extract")
        sys.exit(1)
