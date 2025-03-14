import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from app.scrapers.cookie_scraper import scrape_calendar_slots_for_days
from app.monitors.slack_notifier import SlackNotifier, setup_instructions

class SlotMonitor:
    def __init__(self, slack_webhook_url=None, days=14, interval_minutes=30, filters=None):
        self.days = days
        self.interval_seconds = interval_minutes * 60
        self.filters = filters or {}
        self.previous_slots = {}
        self.notified_slots = set()
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Slack setup
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.notifier = SlackNotifier(self.slack_webhook_url)
        
        # Load previous slots if available
        self.previous_slots_file = self.data_dir / "previous_slots.json"
        if self.previous_slots_file.exists():
            with open(self.previous_slots_file, "r", encoding="utf-8") as f:
                try:
                    self.previous_slots = json.load(f)
                except json.JSONDecodeError:
                    print("Error loading previous slots file. Starting fresh.")
        
        # Load notified slots if available
        self.notified_slots_file = self.data_dir / "notified_slots.json"
        if self.notified_slots_file.exists():
            with open(self.notified_slots_file, "r", encoding="utf-8") as f:
                try:
                    self.notified_slots = set(json.load(f))
                except json.JSONDecodeError:
                    print("Error loading notified slots file. Starting fresh.")
    
    async def start_monitoring(self):
        print(f"Starting slot monitoring every {self.interval_seconds // 60} minutes for {self.days} days ahead")
        if self.filters:
            filter_desc = ", ".join(f"{k}: {v}" for k, v in self.filters.items())
            print(f"Using filters: {filter_desc}")
        
        if self.slack_webhook_url:
            self.notifier.send_notification("YAM Slot Monitor started. Monitoring for new available slots...")
        else:
            print("Slack webhook URL not configured. Notifications will not be sent.")
            print("To enable Slack notifications, run 'python -m app.main monitor setup'")
        
        while True:
            try:
                await self.check_for_new_slots()
                print(f"Next check in {self.interval_seconds // 60} minutes. Waiting...")
                await asyncio.sleep(self.interval_seconds)
            except Exception as e:
                print(f"Error during monitoring: {e}")
                print("Retrying in 5 minutes...")
                await asyncio.sleep(300)
    
    async def check_for_new_slots(self):
        print(f"Checking for new slots at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        current_slots = await scrape_calendar_slots_for_days(self.days, self.filters)
        if not current_slots:
            print("Failed to retrieve current slots")
            return
        
        new_slots = []
        
        # Convert current slots to a dict for easy comparison
        current_slots_dict = {}
        for slot in current_slots:
            if slot.get('is_available', False):  # Only track available slots
                slot_key = f"{slot['date']}_{slot['event_id']}"
                current_slots_dict[slot_key] = slot
        
        # Find new slots (not in previous slots)
        for slot_key, slot in current_slots_dict.items():
            if slot_key not in self.previous_slots and slot_key not in self.notified_slots:
                new_slots.append(slot)
                self.notified_slots.add(slot_key)
        
        # Find slots that became available
        for slot_key, prev_slot in self.previous_slots.items():
            if slot_key in current_slots_dict and slot_key not in self.notified_slots:
                if not prev_slot.get('is_available', False) and current_slots_dict[slot_key].get('is_available', False):
                    new_slots.append(current_slots_dict[slot_key])
                    self.notified_slots.add(slot_key)
        
        # Update previous slots
        self.previous_slots = current_slots_dict
        
        # Save previous slots to file
        with open(self.previous_slots_file, "w", encoding="utf-8") as f:
            json.dump(self.previous_slots, f, ensure_ascii=False, indent=2)
        
        # Save notified slots to file
        with open(self.notified_slots_file, "w", encoding="utf-8") as f:
            json.dump(list(self.notified_slots), f, ensure_ascii=False, indent=2)
        
        if new_slots:
            print(f"Found {len(new_slots)} new available slots!")
            await self.notify_new_slots(new_slots)
        else:
            print("No new slots found")
    
    async def notify_new_slots(self, new_slots):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        notification_file = self.data_dir / f"new_slots_{timestamp}.json"
        
        with open(notification_file, "w", encoding="utf-8") as f:
            json.dump(new_slots, f, ensure_ascii=False, indent=2)
        
        print(f"New slots saved to {notification_file}")
        
        # Print notification to console
        print("\n=== NEW AVAILABLE SLOTS ===")
        for slot in new_slots:
            print(f"Date: {slot['date']}, Time: {slot['time']}, Boat: {slot.get('boat_name', 'Unknown')}, Capacity: {slot.get('capacity', 'Unknown')}")
        print("===========================\n")
        
        # Send Slack notification
        self.notifier.send_slot_notification(new_slots)


async def main():
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Check for setup command
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        print("Starting Slack webhook setup...")
        setup_instructions()
        return
    
    # Regular monitoring
    days = 14
    interval = 30  # minutes
    filters = {}
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number of days: {sys.argv[1]}. Using default: 14 days.")
    
    if len(sys.argv) > 2:
        try:
            interval = int(sys.argv[2])
        except ValueError:
            print(f"Invalid interval: {sys.argv[2]}. Using default: 30 minutes.")
    
    # Parse filters if provided
    if len(sys.argv) > 3 and sys.argv[3] == "filter":
        for i in range(4, len(sys.argv), 2):
            if i + 1 < len(sys.argv):
                key = sys.argv[i]
                value = sys.argv[i + 1]
                
                # Handle list values (comma-separated)
                if ',' in value:
                    filters[key] = value.split(',')
                else:
                    filters[key] = value
    
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        print("Warning: Slack notifications are not configured.")
        print("To enable Slack notifications, add SLACK_WEBHOOK_URL to your .env file.")
        print("Run 'python -m app.main monitor setup' for setup instructions.")
    
    monitor = SlotMonitor(slack_webhook_url, days, interval, filters)
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
