import json
import os
import requests
from datetime import datetime

class SlackNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        
    def send_notification(self, message, blocks=None):
        if not self.webhook_url:
            print("Slack webhook URL not configured. Skipping notification.")
            return False
        
        payload = {
            "text": message
        }
        
        if blocks:
            payload["blocks"] = blocks
            
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            print(f"Slack notification sent successfully: {response.status_code}")
            return True
        except Exception as e:
            print(f"Failed to send Slack notification: {e}")
            return False
    
    def send_slot_notification(self, slots):
        if not slots:
            return False
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 {len(slots)} New YAM Slots Available!",
                    "emoji": True
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": f"Found at {timestamp}",
                        "emoji": True
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        for i, slot in enumerate(slots, 1):
            date = slot.get('date', 'Unknown date')
            time = slot.get('time', 'Unknown time')
            boat = slot.get('boat_name', 'Unknown boat')
            capacity = slot.get('capacity', 'Unknown capacity')
            event_id = slot.get('event_id', 'Unknown ID')
            
            slot_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Slot {i}*\n"
                           f"📅 *Date:* {date}\n"
                           f"⏰ *Time:* {time}\n"
                           f"🚤 *Boat:* {boat}\n"
                           f"👥 *Capacity:* {capacity}\n"
                           f"🆔 *Event ID:* {event_id}\n"
                }
            }
            
            booking_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "To book this slot, run:"
                }
            }
            
            command_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"`python -m app.main book {event_id}`"
                }
            }
            
            blocks.extend([slot_block, booking_block, command_block])
            
            if i < len(slots):
                blocks.append({"type": "divider"})
        
        message = f"{len(slots)} new YAM slots available!"
        return self.send_notification(message, blocks)


def setup_instructions():
    print("\n=== Slack Webhook Setup Instructions ===")
    print("1. Go to https://api.slack.com/apps and click 'Create New App'")
    print("2. Choose 'From scratch' and give your app a name (e.g., 'YAM Monitor')")
    print("3. Select the workspace where you want to receive notifications")
    print("4. In the left sidebar, click on 'Incoming Webhooks'")
    print("5. Toggle 'Activate Incoming Webhooks' to On")
    print("6. Click 'Add New Webhook to Workspace'")
    print("7. Choose a channel to post to (or create a new one)")
    print("8. Copy the Webhook URL provided")
    print("9. Add the webhook URL to your .env file:")
    print("   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
    print("=== End of Setup Instructions ===\n")
    
    return True
