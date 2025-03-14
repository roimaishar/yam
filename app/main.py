import sys
import asyncio
from app.scrapers.cookie_scraper import main as scraper_main
from app.scrapers.cookie_scraper import scrape_calendar_slots_for_days
from app.scrapers.booking_scraper import book_slot
from app.utils.extract_data import process_all_calendar_files

def extract_data():
    process_all_calendar_files()

def print_usage():
    print("Usage:")
    print("  python -m app.main                    - Run the default scraper")
    print("  python -m app.main calendar [days]    - Scrape calendar slots for specified days (default: 14)")
    print("  python -m app.main calendar [days] filter [filter_options] - Scrape with filters")
    print("  python -m app.main book <event_id>    - Book a specific slot by event ID")
    print("\nFilter options (key value pairs):")
    print("  boat_name [name]          - Filter by boat name (comma-separated for multiple)")
    print("  min_capacity [number]     - Filter by minimum capacity")
    print("  max_capacity [number]     - Filter by maximum capacity")
    print("  start_time_after [time]   - Filter by start time (e.g., '14:00')")
    print("  start_time_before [time]  - Filter by end time (e.g., '18:00')")
    print("  day_of_week [day]         - Filter by day of week (e.g., 'friday,saturday')")

async def scrape_calendar(days=14, filters=None):
    return await scrape_calendar_slots_for_days(days, filters)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.main [scrape|calendar|extract|book|help]")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "scrape":
        asyncio.run(scraper_main())
    elif command == "calendar":
        days = 14
        filters = {}
        
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                print(f"Invalid number of days: {sys.argv[2]}. Using default: 14 days.")
        
        if len(sys.argv) > 3 and sys.argv[3] == "filter":
            for i in range(4, len(sys.argv), 2):
                if i + 1 < len(sys.argv):
                    key = sys.argv[i]
                    value = sys.argv[i + 1]
                    
                    if ',' in value:
                        filters[key] = value.split(',')
                    else:
                        filters[key] = value
        
        asyncio.run(scrape_calendar(days, filters))
    elif command == "book":
        if len(sys.argv) < 3:
            print("Usage: python -m app.main book <event_id> [--confirm]")
            sys.exit(1)
        
        event_id = sys.argv[2]
        asyncio.run(book_slot(event_id))
    elif command == "extract":
        extract_data()
    elif command == "help":
        print_usage()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: scrape, calendar, extract, book, help")
