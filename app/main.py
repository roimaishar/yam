import asyncio
import sys
import argparse
from app.scrapers.cookie_scraper import scrape_calendar_slots_for_days
from app.monitors.slot_monitor import SlotMonitor

async def run_scraper():
    await scrape_calendar_slots_for_days(14)
    
async def scrape_calendar(days=14):
    await scrape_calendar_slots_for_days(days)

async def run_monitor(days, interval, filters=None):
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        print("Warning: Slack notifications are not configured.")
        print("To enable Slack notifications, add SLACK_WEBHOOK_URL to your .env file.")
        print("Run 'python -m app.main monitor --setup' for setup instructions.")
    
    monitor = SlotMonitor(slack_webhook_url, days, interval, filters)
    await monitor.start_monitoring()

def parse_arguments():
    parser = argparse.ArgumentParser(description='YAM Online Calendar Scraper')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Scrape command
    subparsers.add_parser('scrape', help='Run the calendar scraper with default settings (14 days)')
    
    # Calendar command with more options
    calendar_parser = subparsers.add_parser('calendar', help='Run the calendar scraper with specified parameters')
    calendar_parser.add_argument('days', type=int, nargs='?', default=14, help='Number of days to scrape')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start monitoring for new available slots')
    monitor_parser.add_argument('days', type=int, nargs='?', default=14, help='Number of days to monitor')
    monitor_parser.add_argument('--interval', type=int, default=30, help='Check interval in minutes (default: 30)')
    monitor_parser.add_argument('--time-range', type=str, help='Time range filter (e.g., "9:00-17:00")')
    monitor_parser.add_argument('--service-type', type=str, help='Filter by boat type')
    monitor_parser.add_argument('--setup', action='store_true', help='Show Slack webhook setup instructions')
    
    args = parser.parse_args()
    
    # Default to 'scrape' if no command is provided
    if not args.command:
        args.command = 'scrape'
    
    return args

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python -m app.main [scrape|calendar|monitor] [options]")
        print("For more information, use --help")
        sys.exit(1)
    
    args = parse_arguments()
    
    if args.command == "scrape":
        asyncio.run(run_scraper())
    
    elif args.command == "calendar":
        days = args.days
        asyncio.run(scrape_calendar(days))
    
    elif args.command == "monitor":
        # Handle monitor setup command
        if hasattr(args, 'setup') and args.setup:
            from app.monitors.slack_notifier import setup_instructions
            setup_instructions()
            sys.exit(0)
        
        # Prepare filters
        filters = {}
        if hasattr(args, 'time_range') and args.time_range:
            filters['time_range'] = args.time_range
        if hasattr(args, 'service_type') and args.service_type:
            filters['service_type'] = args.service_type
        
        # Start monitoring
        days = args.days if hasattr(args, 'days') else 14
        interval = args.interval if hasattr(args, 'interval') else 30
        
        print(f"Starting monitoring for {days} days ahead, checking every {interval} minutes")
        if filters:
            print(f"Using filters: {filters}")
        
        # Use our run_monitor function
        asyncio.run(run_monitor(days, interval, filters))
    
    else:
        print(f"Unknown command: {args.command}")
        print("Available commands: scrape, calendar, monitor")
        sys.exit(1)
