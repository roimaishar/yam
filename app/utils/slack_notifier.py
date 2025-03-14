import json
import requests
from typing import List, Dict, Any

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_message(self, message: str) -> bool:
        payload = {
            "text": message
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False
    
    def notify_new_slots(self, new_slots: List[Dict[str, Any]], criteria: Dict[str, Any]) -> bool:
        if not new_slots:
            return True
        
        criteria_text = ", ".join([f"{k}: {v}" for k, v in criteria.items() if v])
        
        message = f"🚨 *New boat slots available!* 🚨\n"
        message += f"Monitoring criteria: {criteria_text}\n\n"
        
        for i, slot in enumerate(new_slots, 1):
            date = slot.get("date", "Unknown date")
            time = slot.get("time", "Unknown time")
            service = slot.get("service_type", "Unknown service")
            
            message += f"*{i}. {date}*\n"
            message += f"   Time: {time}\n"
            message += f"   Boat: {service}\n\n"
        
        message += "Book now at https://yam-online.com/calendar"
        
        return self.send_message(message)
