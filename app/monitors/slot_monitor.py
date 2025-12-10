import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from app.scrapers.cookie_scraper import scrape_calendar_slots_for_days
from app.monitors.slack_notifier import SlackNotifier, setup_instructions
from app.utils.merge_slots import merge_consecutive_slots, format_merged_slots_for_notification
from app.utils.slot_filter_config import load_slot_filters
from app.utils.slot_filter import filter_slots_by_conditions

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
        
        # Category-specific webhooks
        category_webhooks = {
            "katamaran": os.getenv("SLACK_WEBHOOK_URL_KATAMARAN"),
            "monohull": os.getenv("SLACK_WEBHOOK_URL_MONOHULL")
        }
        
        self.notifier = SlackNotifier(self.slack_webhook_url, category_webhooks)
        
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
            
            # Filter out slots from the last day (14th day)
            if self.days > 1:
                # Calculate the date of the last day
                last_day = datetime.now() + timedelta(days=self.days-1)
                last_day_formatted = last_day.strftime("%Y-%m-%d")
                
                # Filter slots to exclude the last day
                filtered_new_slots = []
                excluded_count = 0
                
                for slot in new_slots:
                    slot_date = slot.get("date", "")
                    
                    # Check if this is from the last day by trying to parse the date
                    try:
                        # Parse Hebrew date format (e.g., "שישי, 12 אפריל 2025")
                        hebrew_month_names = {
                            "ינואר": "January", "פברואר": "February", "מרץ": "March",
                            "אפריל": "April", "מאי": "May", "יוני": "June",
                            "יולי": "July", "אוגוסט": "August", "ספטמבר": "September",
                            "אוקטובר": "October", "נובמבר": "November", "דצמבר": "December"
                        }
                        
                        if "," in slot_date:
                            day_name, date_part = slot_date.split(",", 1)
                            date_part = date_part.strip()
                            
                            parts = date_part.split()
                            if len(parts) >= 3:  # day, month, year
                                day_num = parts[0]
                                month_name = parts[1]
                                year = parts[2]
                                
                                # Translate Hebrew month name if needed
                                if month_name in hebrew_month_names:
                                    month_name = hebrew_month_names[month_name]
                                
                                # Parse the date
                                date_obj = datetime.strptime(f"{day_num} {month_name} {year}", "%d %B %Y")
                                slot_date_formatted = date_obj.strftime("%Y-%m-%d")
                                
                                # Skip if it's the last day
                                if slot_date_formatted == last_day_formatted:
                                    excluded_count += 1
                                    continue
                    except Exception:
                        # If we can't parse the date, include the slot to be safe
                        pass
                    
                    filtered_new_slots.append(slot)
                
                if excluded_count > 0:
                    print(f"Excluded {excluded_count} slots from the {self.days}th day from notifications")
                
                await self.notify_new_slots(filtered_new_slots)
            else:
                await self.notify_new_slots(new_slots)
        else:
            print("No new slots found")
    
    async def notify_new_slots(self, new_slots):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        notification_file = self.data_dir / f"new_slots_{timestamp}.json"
        
        with open(notification_file, "w", encoding="utf-8") as f:
            json.dump(new_slots, f, ensure_ascii=False, indent=2)
        
        print(f"New slots saved to {notification_file}")
        
        # Apply slot filters (weather + days ahead)
        slot_filter_config = load_slot_filters()
        filtered_slots, filter_log = filter_slots_by_conditions(new_slots, slot_filter_config)
        if filter_log:
            print("\n=== SLOT FILTERING ===")
            for entry in filter_log:
                print(entry)
            print(f"Passed: {len(filtered_slots)}/{len(new_slots)} slots")
            print("======================\n")
        
        if not filtered_slots:
            print("All slots were filtered out. No notification sent.")
            return
        
        # Merge consecutive slots for the same boat
        merged_slots = merge_consecutive_slots(filtered_slots)
        formatted_slots = format_merged_slots_for_notification(merged_slots)
        
        # Print notification to console
        print("\n=== NEW AVAILABLE SLOTS ===")
        for slot in formatted_slots:
            slot_info = f"Date: {slot['date']}, Time: {slot['time']}, Boat: {slot.get('service_type', 'Unknown')}"
            if 'slots' in slot and slot['slots'] > 1:
                slot_info += f", Slots: {slot['slots']}"
            print(slot_info)
        print("===========================\n")
        
        # Send Slack notification
        self.notifier.send_slot_notification(formatted_slots)


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
