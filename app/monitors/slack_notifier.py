import requests
from typing import List, Dict, Any
from datetime import datetime

class SlackNotifier:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
    
    def send_notification(self, message: str) -> bool:
        if not self.webhook_url:
            print(f"Slack notification not sent (webhook URL not configured): {message}")
            return False
            
        payload = {
            "text": message
        }
        
        try:
            response = requests.post(
                self.webhook_url,
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
        if not self.webhook_url:
            print(f"Slack notification not sent (webhook URL not configured): {len(slots)} new slots")
            return False
        
        if not slots:
            return False
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Limit total slots to 12
        total_slots = len(slots)
        slots_to_show = slots[:12] if total_slots > 12 else slots
        
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
            
            # Create a table for this date's slots
            table_text = "```\n"
            table_text += "| Time          | Boat Type     |\n"
            table_text += "|---------------|---------------|\n"
            
            for slot in date_slots:
                time = slot.get("time", "Unknown")
                boat_type = slot.get("service_type", "Unknown")
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
        
        payload = {
            "blocks": blocks
        }
        
        try:
            response = requests.post(
                self.webhook_url,
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
9. Add this URL to your .env file as SLACK_WEBHOOK_URL=your_webhook_url

Example .env file:
```
YAM_USERNAME=your_username
YAM_PASSWORD=your_password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX
```
    """)
