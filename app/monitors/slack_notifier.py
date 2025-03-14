import json
import requests
from typing import List, Dict, Any

class SlackNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url
    
    def send_notification(self, message: str) -> bool:
        if not self.webhook_url:
            print(f"Slack notification not sent (webhook URL not configured): {message}")
            return False
            
        payload = {
            "text": message
        }
        
        try:
            with requests.Session() as session:
                response = session.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    print("Slack notification sent successfully")
                    return True
                else:
                    print(f"Failed to send Slack notification: {response.status_code} {response.text}")
                    return False
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False
    
    def send_slot_notification(self, slots: List[Dict[str, Any]]) -> bool:
        if not self.webhook_url:
            print("Slack webhook URL not configured. Notification not sent.")
            return False
            
        if not slots:
            return True
        
        message = "🚨 *New boat slots available!* 🚨\n\n"
        
        for slot in slots:
            date = slot.get("date", "Unknown date")
            time = slot.get("time", "Unknown time")
            service = slot.get("service_type", "Unknown service")
            
            message += f"*{date}*\n"
            message += f"• Time: {time}\n"
            message += f"• Boat: {service}\n\n"
        
        message += "🔗 <https://yam-online.com/calendar|Book now>"
        
        return self.send_notification(message)


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
