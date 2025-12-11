import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from app.scrapers.club_scraper import scrape_club_activities_for_days
from app.monitors.slack_notifier import SlackNotifier
from app.utils.config import CLUB_PREVIOUS_SLOTS_FILE, CLUB_NOTIFIED_SLOTS_FILE

class ClubMonitor:
    """Monitor for club activity availability changes."""
    
    def __init__(self, slack_webhook_url=None, days=14, interval_minutes=30, filters=None):
        self.days = days
        self.interval_seconds = interval_minutes * 60
        self.filters = filters or {}
        self.previous_activities = {}
        self.notified_activities = set()
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Slack setup - reuse existing SlackNotifier
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.club_webhook_url = os.getenv("SLACK_WEBHOOK_URL_CLUB")
        
        # Use club-specific webhook if available, otherwise fall back to general webhook
        primary_webhook = self.club_webhook_url or self.slack_webhook_url
        self.notifier = SlackNotifier(primary_webhook)
        
        # Load previous activities if available
        self.previous_activities_file = Path(CLUB_PREVIOUS_SLOTS_FILE)
        if self.previous_activities_file.exists():
            with open(self.previous_activities_file, "r", encoding="utf-8") as f:
                try:
                    loaded = json.load(f)
                    self.previous_activities = self._ensure_activity_dict(loaded)
                except json.JSONDecodeError:
                    print("Error loading previous club activities file. Starting fresh.")
        
        # Load notified activities if available
        self.notified_activities_file = Path(CLUB_NOTIFIED_SLOTS_FILE)
        if self.notified_activities_file.exists():
            with open(self.notified_activities_file, "r", encoding="utf-8") as f:
                try:
                    loaded_notified = json.load(f)
                    if isinstance(loaded_notified, list):
                        self.notified_activities = set(loaded_notified)
                    elif isinstance(loaded_notified, dict):
                        keys = [self._get_activity_key(item) for item in loaded_notified.values()]
                        self.notified_activities = {key for key in keys if key}
                except json.JSONDecodeError:
                    print("Error loading notified club activities file. Starting fresh.")
    
    async def start_monitoring(self):
        """Start continuous monitoring for club activity changes."""
        print(f"Starting club activity monitoring every {self.interval_seconds // 60} minutes for {self.days} days ahead")
        if self.filters:
            filter_desc = ", ".join(f"{k}: {v}" for k, v in self.filters.items())
            print(f"Using filters: {filter_desc}")
        
        if self.slack_webhook_url or self.club_webhook_url:
            self.notifier.send_notification("YAM Club Activity Monitor started. Monitoring for newly available activities...")
        else:
            print("Slack webhook URL not configured. Notifications will not be sent.")
            print("To enable Slack notifications, set SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL_CLUB in your .env file")
        
        while True:
            try:
                await self.check_for_new_activities()
                print(f"Next check in {self.interval_seconds // 60} minutes. Waiting...")
                await asyncio.sleep(self.interval_seconds)
            except Exception as e:
                print(f"Error during club monitoring: {e}")
                print("Retrying in 5 minutes...")
                await asyncio.sleep(300)
    
    async def check_for_new_activities(self):
        """Check for newly available club activities."""
        print(f"Checking for new club activities at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        current_activities = await scrape_club_activities_for_days(self.days, self.filters)
        if not current_activities:
            print("Failed to retrieve current club activities")
            return
        
        new_activities = []
        
        # Convert current activities to a dict for easy comparison (track ALL activities, not just available ones)
        current_activities_dict = {}
        for activity in current_activities:
            activity_key = self._get_activity_key(activity)
            if not activity_key:
                continue
            current_activities_dict[activity_key] = activity
        
        # Only notify if we have previous data to compare against
        if self.previous_activities:
            # Find activities that became available (were not available before, now are available)
            for activity_key, activity in current_activities_dict.items():
                if activity.get('is_available', False):  # Current activity is available
                    if activity_key in self.previous_activities:
                        # Activity existed before - check if it became available
                        prev_activity = self.previous_activities[activity_key]
                        if not prev_activity.get('is_available', False) and activity_key not in self.notified_activities:
                            new_activities.append(activity)
                            self.notified_activities.add(activity_key)
                            print(f"Activity became available: {activity.get('activity_type', 'Unknown')} - {activity.get('time', 'Unknown')}")
                    else:
                        # Completely new activity that is available
                        if activity_key not in self.notified_activities:
                            new_activities.append(activity)
                            self.notified_activities.add(activity_key)
                            print(f"New available activity: {activity.get('activity_type', 'Unknown')} - {activity.get('time', 'Unknown')}")
        else:
            print("First run - establishing baseline. No notifications will be sent.")
            print(f"Found {len([a for a in current_activities if a.get('is_available', False)])} available activities to track.")
        
        # Update previous activities (track ALL activities for next comparison)
        self.previous_activities = current_activities_dict
        
        # Save previous activities to file
        with open(self.previous_activities_file, "w", encoding="utf-8") as f:
            json.dump(self.previous_activities, f, ensure_ascii=False, indent=2)
        
        # Save notified activities to file
        with open(self.notified_activities_file, "w", encoding="utf-8") as f:
            json.dump(list(self.notified_activities), f, ensure_ascii=False, indent=2)
        
        if new_activities:
            print(f"Found {len(new_activities)} new available club activities!")
            await self.notify_new_activities(new_activities)
        else:
            print("No new club activities found")
    
    async def notify_new_activities(self, new_activities):
        """Send notifications for new club activities."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        notification_file = self.data_dir / f"new_club_activities_{timestamp}.json"
        
        with open(notification_file, "w", encoding="utf-8") as f:
            json.dump(new_activities, f, ensure_ascii=False, indent=2)
        
        print(f"New club activities saved to {notification_file}")
        
        # Print notification to console
        print("\n=== NEW AVAILABLE CLUB ACTIVITIES ===")
        for activity in new_activities:
            activity_info = f"Date: {activity['date']}, Time: {activity.get('time', 'Unknown')}"
            activity_info += f", Type: {activity.get('activity_type', 'Unknown')}"
            activity_info += f", Boat: {activity.get('boat_name', 'Unknown')}"
            if activity.get('activity_name'):
                activity_info += f", Activity: {activity.get('activity_name')}"
            print(activity_info)
        print("=====================================\n")
        
        # Send Slack notification using enhanced method
        await self.send_club_slack_notification(new_activities)
    
    async def send_club_slack_notification(self, activities):
        """Send club-specific Slack notification."""
        if not activities:
            return False
        
        if not (self.slack_webhook_url or self.club_webhook_url):
            print("No webhook URL configured for club notifications")
            return False
        
        # Activity type emojis
        activity_emojis = {
            "הסמכה": "🎓",          # Certification
            "סדנא": "🔧",           # Workshop  
            "הפלגת חברים": "⛵",    # Member Sailing
            "מודרכת מועדון": "🧭",  # Club Guided
            "הפלגת מוביל": "🏁"     # Lead Sailing
        }
        
        total = len(activities)
        lines = [f"🎯 {total} Club Activities\n"]
        
        for activity in activities[:10]:
            date_str = activity.get("date", "")
            short_date = self._format_short_date(date_str)
            time = activity.get('time', '')
            activity_type = activity.get('activity_type', '')
            activity_name = activity.get('activity_name', '')
            boat_name = activity.get('boat_name', '')
            emoji = activity_emojis.get(activity_type, "🚣")
            
            # Build compact line: "Fri 12 Dec: 12:00-15:00 🎓 *Activity Name* (Boat)"
            line = f"{short_date}: {time} {emoji}"
            name_to_show = activity_name if activity_name else activity_type
            if name_to_show:
                line += f" *{name_to_show}*"
            if boat_name:
                line += f" ({boat_name})"
            lines.append(line)
        
        notification = "\n".join(lines)
        webhook_url = self.club_webhook_url or self.slack_webhook_url
        return self.notifier.send_notification(notification, webhook_url)
    
    def _format_short_date(self, date_str):
        """Convert date to short format like 'Fri 12 Dec'."""
        if not date_str:
            return ""
        
        hebrew_day_short = {
            "ראשון": "Sun", "שני": "Mon", "שלישי": "Tue",
            "רביעי": "Wed", "חמישי": "Thu", "שישי": "Fri", "שבת": "Sat"
        }
        hebrew_month_short = {
            "ינואר": "Jan", "פברואר": "Feb", "מרץ": "Mar", "אפריל": "Apr",
            "מאי": "May", "יוני": "Jun", "יולי": "Jul", "אוגוסט": "Aug",
            "ספטמבר": "Sep", "אוקטובר": "Oct", "נובמבר": "Nov", "דצמבר": "Dec"
        }
        
        try:
            if "," in date_str:
                day_name, date_part = date_str.split(",", 1)
                day_name = day_name.strip()
                date_part = date_part.strip()
                parts = date_part.split()
                if len(parts) >= 2:
                    day_num = parts[0]
                    month = parts[1]
                    short_day = hebrew_day_short.get(day_name, day_name[:3])
                    short_month = hebrew_month_short.get(month, month[:3])
                    return f"{short_day} {day_num} {short_month}"
        except Exception:
            pass
        return date_str[:15]
    
    def convert_hebrew_date_to_english(self, hebrew_date):
        """Convert Hebrew date format to English."""
        if not isinstance(hebrew_date, str):
            return str(hebrew_date)
        try:
            date_obj = datetime.fromisoformat(hebrew_date)
            return date_obj.strftime("%A, %d %B %Y")
        except ValueError:
            pass
        
        # Hebrew to English day names
        hebrew_day_to_english = {
            "ראשון": "Sunday", "שני": "Monday", "שלישי": "Tuesday",
            "רביעי": "Wednesday", "חמישי": "Thursday", "שישי": "Friday", "שבת": "Saturday"
        }
        
        # Hebrew to English month names
        hebrew_month_to_english = {
            "ינואר": "January", "פברואר": "February", "מרץ": "March", "אפריל": "April",
            "מאי": "May", "יוני": "June", "יולי": "July", "אוגוסט": "August",
            "ספטמבר": "September", "אוקטובר": "October", "נובמבר": "November", "דצמבר": "December"
        }
        
        english_date = hebrew_date
        
        # Replace Hebrew day names with English
        for hebrew_day, english_day in hebrew_day_to_english.items():
            english_date = english_date.replace(hebrew_day, english_day)
        
        # Replace Hebrew month names with English
        for hebrew_month, english_month in hebrew_month_to_english.items():
            english_date = english_date.replace(hebrew_month, english_month)
        
        return english_date

    def _get_activity_key(self, activity):
        if not isinstance(activity, dict):
            return None
        key = activity.get("activity_id")
        if key:
            return key
        date_iso = activity.get("date_iso") or activity.get("date")
        event_id = activity.get("event_id") or activity.get("registration_event_id")
        if date_iso and event_id:
            return f"{date_iso}_{event_id}"
        if event_id:
            return str(event_id)
        return None

    def _ensure_activity_dict(self, loaded):
        if isinstance(loaded, dict):
            return {key: value for key, value in loaded.items() if isinstance(value, dict)}
        if isinstance(loaded, list):
            result = {}
            for item in loaded:
                key = self._get_activity_key(item)
                if key and isinstance(item, dict):
                    result[key] = item
            return result
        return {}

async def main():
    """Main function for testing club monitor independently."""
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    days = 14
    interval = 30  # minutes
    
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
    
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL") or os.getenv("SLACK_WEBHOOK_URL_CLUB")
    
    if not slack_webhook_url:
        print("Warning: Slack notifications are not configured.")
        print("To enable Slack notifications, add SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL_CLUB to your .env file.")
    
    # Check if this is a one-time check
    if "--once" in sys.argv:
        print(f"Running club monitor once for {days} days ahead")
        monitor = ClubMonitor(slack_webhook_url, days, interval)
        await monitor.check_for_new_activities()
    else:
        print(f"Starting club monitoring for {days} days ahead, checking every {interval} minutes")
        monitor = ClubMonitor(slack_webhook_url, days, interval)
        await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
