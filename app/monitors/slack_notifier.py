import requests
from typing import List, Dict, Any
from app.utils.boat_categories import group_slots_by_category, get_webhook_for_category

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
        # Format the notification
        total_slots = len(slots)
        notification = f"🚣 {total_slots} New Boat Slots Available! 🚣"
        
        # Show message about limiting displayed slots if needed
        shown_slots = min(len(slots), 12)  # Show up to 12 slots
        if len(slots) > shown_slots:
            notification += f" (showing {shown_slots} of {len(slots)})"
        
        # Group slots by date for cleaner presentation
        slots_by_date = {}
        
        from app.forecasts.swell_forecast import format_slot_forecast
        
        for slot in slots[:shown_slots]:  # Only process slots we'll show
            date_key = slot.get("date", "Unknown")
            if date_key not in slots_by_date:
                slots_by_date[date_key] = []
            
            # Format the slot info
            slot_info = f"{slot.get('time', '')}: {slot.get('service_type', '')}"
            
            # Add forecast emoji if available
            forecast_emoji = format_slot_forecast(slot)
            if forecast_emoji:
                slot_info += f" {forecast_emoji}"
                
            slots_by_date[date_key].append(slot_info)
        
        # Add slots by date
        notification += "\n\n"
        for date, slot_infos in slots_by_date.items():
            # Convert Hebrew date to English if needed
            if "," in date:
                parts = date.split(",", 1)
                day_name = parts[0].strip()
                
                # Map Hebrew day names to English if needed
                hebrew_day_to_english = {
                    "ראשון": "Sunday",
                    "שני": "Monday",
                    "שלישי": "Tuesday",
                    "רביעי": "Wednesday",
                    "חמישי": "Thursday",
                    "שישי": "Friday",
                    "שבת": "Saturday"
                }
                
                if day_name in hebrew_day_to_english:
                    date = date.replace(day_name, hebrew_day_to_english[day_name])
            
            notification += f"{date}:\n"
            for slot_info in slot_infos:
                notification += f"- {slot_info}\n"
            
            notification += "\n"
        
        return notification.strip()
    
    def _send_formatted_notification(self, slots: List[Dict[str, Any]], webhook_url: str) -> bool:
        if not webhook_url:
            print(f"Slack notification not sent (webhook URL not configured): {len(slots)} new slots")
            return False
        
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
                        "text": f"(showing 12 of {total_slots})" if total_slots > 12 else " ",
                        "emoji": True
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        # Import swell forecast functions
        from app.forecasts.swell_forecast import format_slot_forecast
        
        # Group slots by date
        slots_by_date = {}
        for slot in slots_to_show:
            date = slot.get("date", "Unknown")
            if date not in slots_by_date:
                slots_by_date[date] = []
            slots_by_date[date].append(slot)
        
        # Add each date section with its slots
        for date, date_slots in slots_by_date.items():
            # Get swell forecast for this date using the first slot
            swell_info = format_slot_forecast(date_slots[0])
            
            # Add date header with swell info
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📅 {date}*  |  *🌊 Swell:* {swell_info}"
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
                
                # Add forecast emoji if available
                forecast_emoji = format_slot_forecast(slot)
                if forecast_emoji:
                    boat_type += f" {forecast_emoji}"
                
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
        
        # Add forecast general info for Herzliya
        try:
            from app.forecasts.swell_forecast import get_simplified_forecast
            forecast = get_simplified_forecast(days=3)  # Next 3 days
            
            if forecast:
                forecast_text = "*🌊 Herzliya Marina Forecast*\n"
                
                for day in forecast:
                    swell_height = day.get("max_swell_height", 0)
                    swell_period = day.get("avg_swell_period", 0)
                    direction = day.get("dominant_swell_direction", "")
                    
                    # Get emoji based on wave height
                    from app.forecasts.swell_forecast import get_swell_emoji
                    emoji = get_swell_emoji(swell_height)
                    
                    date_parts = day.get("display_date", "").split(", ")
                    short_date = date_parts[1] if len(date_parts) > 1 else date_parts[0]
                    
                    forecast_text += f"• {short_date}: {emoji} Swell: {swell_height}m | Period: {swell_period}s | {direction}\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": forecast_text
                    }
                })
                
                blocks.append({
                    "type": "divider"
                })
        except Exception as e:
            print(f"Error adding forecast to notification: {e}")
        
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
