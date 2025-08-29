import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from app.scrapers.club_scraper import scrape_club_activities_for_days
from app.monitors.slack_notifier import SlackNotifier
from app.utils.config import CLUB_ALL_SLOTS_FILE, CLUB_PREVIOUS_SLOTS_FILE, CLUB_NOTIFIED_SLOTS_FILE

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
                    self.previous_activities = json.load(f)
                except json.JSONDecodeError:
                    print("Error loading previous club activities file. Starting fresh.")
        
        # Load notified activities if available
        self.notified_activities_file = Path(CLUB_NOTIFIED_SLOTS_FILE)
        if self.notified_activities_file.exists():
            with open(self.notified_activities_file, "r", encoding="utf-8") as f:
                try:
                    self.notified_activities = set(json.load(f))
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
            activity_key = f"{activity['date']}_{activity['event_id']}"
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
        
        # Create club-specific notification message
        total_activities = len(activities)
        notification = f"🎯 {total_activities} New Club Activities Available! 🎯"
        
        # Group activities by date for cleaner presentation
        activities_by_date = {}
        
        # Activity type emojis
        activity_emojis = {
            "הסמכה": "🎓",          # Certification
            "סדנא": "🔧",           # Workshop  
            "הפלגת חברים": "⛵",    # Member Sailing
            "מודרכת מועדון": "🧭",  # Club Guided
            "הפלגת מוביל": "🏁"     # Lead Sailing
        }
        
        for activity in activities[:10]:  # Show up to 10 activities
            date_key = activity.get("date", "Unknown")
            if date_key not in activities_by_date:
                activities_by_date[date_key] = []
            
            # Format the activity info
            activity_type = activity.get('activity_type', '')
            activity_name = activity.get('activity_name', '')
            boat_name = activity.get('boat_name', '')
            time = activity.get('time', '')
            
            # Get appropriate emoji
            emoji = activity_emojis.get(activity_type, "🚣")
            
            # Create activity info string
            activity_info = f"{time}: {emoji} {activity_type}"
            if activity_name and activity_name != activity_type:
                activity_info += f" - {activity_name}"
            if boat_name:
                activity_info += f" ({boat_name})"
            
            activities_by_date[date_key].append(activity_info)
        
        # Build notification message
        notification += "\n\n"
        for date, activity_infos in activities_by_date.items():
            # Convert Hebrew date format to English
            english_date = self.convert_hebrew_date_to_english(date)
            notification += f"📅 {english_date}:\n"
            for activity_info in activity_infos:
                notification += f"• {activity_info}\n"
            notification += "\n"
        
        # Add footer
        notification += "🔗 Register at https://yamonline.custhelp.com/app/calendar_club"
        
        # Send notification
        webhook_url = self.club_webhook_url or self.slack_webhook_url
        return self.notifier.send_notification(notification.strip(), webhook_url)
    
    def convert_hebrew_date_to_english(self, hebrew_date):
        """Convert Hebrew date format to English."""
        if not isinstance(hebrew_date, str):
            return str(hebrew_date)
        
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
