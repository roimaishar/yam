import requests
from typing import List, Dict, Any
from datetime import datetime
from app.utils.boat_categories import group_slots_by_category, get_webhook_for_category, get_boat_category

class SlackNotifier:
    def __init__(self, webhook_url: str = None, category_webhooks: Dict[str, str] = None):
        self.webhook_url = webhook_url
        self.category_webhooks = category_webhooks or {}
    
    def send_notification(self, message: str, webhook_url: str = None) -> bool:
        target_webhook = webhook_url or self.webhook_url
        
        if not target_webhook:
            print(f"Slack notification not sent (webhook URL not configured): {message}")
            return False
            
        payload = {
            "text": message
        }
        
        try:
            response = requests.post(
                target_webhook,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200 and response.text == "ok":
                print("Slack notification sent successfully")
                return True
            else:
                print(f"Failed to send Slack notification: {response.status_code} {response.text}")
                print(f"Message that would have been sent: {message}")
                return True
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            print(f"Message that would have been sent: {message}")
            return True
    
    def send_slot_notification(self, slots: List[Dict[str, Any]]) -> bool:
        if not slots:
            return False
        
        # Send to default webhook (all slots)
        if self.webhook_url:
            self._send_formatted_notification(slots, self.webhook_url)
        
        # Group slots by boat category
        categorized_slots = group_slots_by_category(slots)
        
        # Send category-specific notifications
        for category in ["katamaran", "monohull"]:
            category_slots = categorized_slots.get(category, [])
            if category_slots:
                webhook = get_webhook_for_category(category)
                if webhook and webhook != self.webhook_url:  # Don't duplicate if same as default
                    self._send_formatted_notification(category_slots, webhook)
        
        return True
    
    def _format_mobile_notification(self, slots: List[Dict[str, Any]]) -> str:
        # Hebrew to English mapping for boat names
        hebrew_to_english = {
            "אסתר": "Esther",
            "ושתי": "Vashti",
            "כרמן החדשה": "Carmen",
            "ליאור": "Lior",
            "מישל": "Michel",
            "נאווה": "Naava",
            "קרפה": "Carpe",
            "רוני": "Roni",
            "רונית": "Ronit",
            "הרמוני": "Harmony",
            "קטמנדו": "Katmandu"
        }
        
        # Day name translations and abbreviations
        hebrew_day_to_english = {
            "ראשון": "Sun",
            "שני": "Mon",
            "שלישי": "Tue",
            "רביעי": "Wed",
            "חמישי": "Thu",
            "שישי": "Fri",
            "שבת": "Sat"
        }
        
        # Organize slots by date, boat type and category
        dates = {}
        categories = {
            "katamaran": {"emoji": "⛵", "name": "Kat", "boats": {}},
            "monohull": {"emoji": "⚓", "name": "Mono", "boats": {}}
        }
        
        # Group slots by date, boat, and category
        for slot in slots:
            # Parse date
            date_str = slot.get("date", "")
            day_name = date_str.split(",")[0].strip() if "," in date_str else date_str
            day_date = date_str.split(",")[1].strip() if "," in date_str else ""
            
            # Extract day and month
            day_num = ""
            month_num = ""
            if day_date:
                parts = day_date.split()
                if len(parts) >= 2:
                    day_num = parts[0]
                    month_map = {"ינואר": "1", "פברואר": "2", "מרץ": "3", "אפריל": "4", "מאי": "5", "יוני": "6",
                                "יולי": "7", "אוגוסט": "8", "ספטמבר": "9", "אוקטובר": "10", "נובמבר": "11", "דצמבר": "12"}
                    month_num = month_map.get(parts[1], "")
            
            # Get English day name
            eng_day = hebrew_day_to_english.get(day_name, day_name)
            
            # Format date as "Day(D/M)"
            date_key = f"{eng_day}({day_num}/{month_num})" if day_num and month_num else eng_day
            if date_key not in dates:
                dates[date_key] = True
            
            # Process boat information
            boat_name = slot.get("service_type", "").split()[0] if slot.get("service_type") else "Unknown"
            english_name = hebrew_to_english.get(boat_name, boat_name)
            category = get_boat_category(boat_name)
            
            if category not in categories:
                continue
                
            time_slot = slot.get("time", "").split(" - ")
            start_time = time_slot[0]
            end_time = time_slot[1] if len(time_slot) > 1 else ""
            
            # Format times to be shorter (10:00 -> 10)
            start_short = start_time.split(":")[0]
            end_short = end_time.split(":")[0] if end_time else ""
            
            # Create boat key with date info
            boat_key = f"{english_name}"
            if boat_key not in categories[category]["boats"]:
                categories[category]["boats"][boat_key] = {}
            
            if eng_day not in categories[category]["boats"][boat_key]:
                categories[category]["boats"][boat_key][eng_day] = []
                
            categories[category]["boats"][boat_key][eng_day].append((start_short, end_short))
        
        # Format the notification
        total_slots = len(slots)
        notification = f"🔔 {total_slots} New Slots! "
        
        # Add dates summary
        if dates:
            notification += "📅 " + ", ".join(dates.keys()) + " "
        
        # Add each category with its boats
        for cat_key, cat_data in categories.items():
            if not cat_data["boats"]:
                continue
                
            notification += f"{cat_data['emoji']} {cat_data['name']}: "
            
            # Add each boat with merged time slots by day
            boat_texts = []
            for boat_name, days in cat_data["boats"].items():
                day_texts = []
                
                for day, time_slots in days.items():
                    # Sort time slots by start time
                    time_slots.sort(key=lambda x: x[0])
                    
                    # Merge consecutive slots
                    merged_slots = []
                    current_range = None
                    
                    for start, end in time_slots:
                        if not current_range:
                            current_range = [start, end]
                        elif start == current_range[1]:
                            # This slot starts right after the previous one ends
                            current_range[1] = end
                        else:
                            # This is a new non-consecutive slot
                            merged_slots.append(f"{current_range[0]}-{current_range[1]}")
                            current_range = [start, end]
                    
                    if current_range:
                        merged_slots.append(f"{current_range[0]}-{current_range[1]}")
                    
                    # Format as "Day time1,time2"
                    day_text = f"{day} {','.join(merged_slots)}"
                    day_texts.append(day_text)
                
                # Format as "BoatName(day1 slot1,slot2; day2 slot1,slot2)"
                boat_text = f"{boat_name}({' '.join(day_texts)})"
                boat_texts.append(boat_text)
            
            notification += ", ".join(boat_texts) + " "
        
        return notification.strip()
    
    def _send_formatted_notification(self, slots: List[Dict[str, Any]], webhook_url: str) -> bool:
        if not webhook_url:
            print(f"Slack notification not sent (webhook URL not configured): {len(slots)} new slots")
            return False
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Limit total slots to 12
        total_slots = len(slots)
        slots_to_show = slots[:12] if total_slots > 12 else slots
        
        # Create a mobile-friendly notification summary
        mobile_notification = self._format_mobile_notification(slots)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚣 {total_slots} New Boat Slots Available! 🚣",
                    "emoji": True
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": f"Found at {now}" + (f" (showing 12 of {total_slots})" if total_slots > 12 else ""),
                        "emoji": True
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        # Group slots by date
        slots_by_date = {}
        for slot in slots_to_show:
            date = slot.get("date", "Unknown")
            if date not in slots_by_date:
                slots_by_date[date] = []
            slots_by_date[date].append(slot)
        
        # Add each date section with its slots
        for date, date_slots in slots_by_date.items():
            # Add date header
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📅 {date}*"
                }
            })
            
            # Check if any slot has a count greater than 1
            has_multiple_slots = any(slot.get("slots", 1) > 1 for slot in date_slots)
            
            # Create a table for this date's slots
            table_text = "```\n"
            if has_multiple_slots:
                table_text += "| Time          | Boat Type     | Slots |\n"
                table_text += "|---------------|---------------|-------|\n"
            else:
                table_text += "| Time          | Boat Type     |\n"
                table_text += "|---------------|---------------|\n"
            
            for slot in date_slots:
                time = slot.get("time", "Unknown")
                boat_type = slot.get("service_type", "Unknown")
                slots_count = slot.get("slots", 1)
                
                if has_multiple_slots:
                    table_text += f"| {time.ljust(13)} | {boat_type.ljust(13)} | {str(slots_count).ljust(5)} |\n"
                else:
                    table_text += f"| {time.ljust(13)} | {boat_type.ljust(13)} |\n"
            
            table_text += "```"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": table_text
                }
            })
            
            blocks.append({
                "type": "divider"
            })
        
        # Add footer with link
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Book now at <https://yamonline.co.il/|YAM Online>"
            }
        })
        
        # Use mobile-friendly text for notification preview
        payload = {
            "text": mobile_notification,
            "blocks": blocks
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200 and response.text == "ok":
                print("New slot notification sent successfully")
                return True
            else:
                print(f"Failed to send slot notification: {response.status_code} {response.text}")
                return True
        except Exception as e:
            print(f"Error sending slot notification: {e}")
            return True


def setup_instructions():
    print("""
=== Slack Webhook Setup Instructions ===

1. Go to https://api.slack.com/apps and click "Create New App"
2. Choose "From scratch" and give your app a name (e.g., "YAM Slot Monitor")
3. Select the workspace where you want to receive notifications
4. In the left sidebar, click on "Incoming Webhooks"
5. Toggle "Activate Incoming Webhooks" to On
6. Click "Add New Webhook to Workspace"
7. Choose the channel where you want to post notifications
8. Copy the Webhook URL that is generated
9. Add the webhook URLs to your .env file

Example .env file with category-specific channels:
```
YAM_USERNAME=your_username
YAM_PASSWORD=your_password

# Main webhook URL (for all boats)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX

# Category-specific webhook URLs
SLACK_WEBHOOK_URL_KATAMARAN=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/YYYYYYYYYYYYYYYYYYYY
SLACK_WEBHOOK_URL_MONOHULL=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/ZZZZZZZZZZZZZZZZZZZZ
```

=== Boat Categories ===

Katamaran boats:
- אסתר (Esther)
- ושתי (Vashti)

Monohull boats:
- כרמן החדשה (New Carmen)
- ליאור (Lior)
- מישל (Michel)
- נאווה (Naava)
- קרפה (Carpe)
- רוני (Roni)
- רונית (Ronit)
- הרמוני (Harmony)
- קטמנדו (Katmandu)
    """)
