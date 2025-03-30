import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define boat categories
KATAMARAN_BOATS = ["אסתר", "ושתי"]
MONOHULL_BOATS = ["כרמן החדשה", "ליאור", "מישל", "נאווה", "קרפה", "רוני", "רונית", "הרמוני", "קטמנדו"]

# Create a mapping of boat to category
BOAT_TO_CATEGORY = {}
for boat in KATAMARAN_BOATS:
    BOAT_TO_CATEGORY[boat] = "katamaran"
for boat in MONOHULL_BOATS:
    BOAT_TO_CATEGORY[boat] = "monohull"

def get_boat_category(boat_name):
    """Get the category for a given boat name"""
    return BOAT_TO_CATEGORY.get(boat_name, "unknown")

def get_webhook_for_boat(boat_name):
    """Get the appropriate webhook URL for the given boat"""
    category = get_boat_category(boat_name)
    
    # Try to get category-specific webhook
    if category == "katamaran":
        return os.getenv("SLACK_WEBHOOK_URL_KATAMARAN") or os.getenv("SLACK_WEBHOOK_URL")
    elif category == "monohull":
        return os.getenv("SLACK_WEBHOOK_URL_MONOHULL") or os.getenv("SLACK_WEBHOOK_URL")
    
    # Fallback to default webhook
    return os.getenv("SLACK_WEBHOOK_URL")

def get_webhook_for_category(category):
    """Get the webhook URL for a specific category"""
    if category == "katamaran":
        return os.getenv("SLACK_WEBHOOK_URL_KATAMARAN") or os.getenv("SLACK_WEBHOOK_URL")
    elif category == "monohull":
        return os.getenv("SLACK_WEBHOOK_URL_MONOHULL") or os.getenv("SLACK_WEBHOOK_URL")
    
    # Fallback to default webhook
    return os.getenv("SLACK_WEBHOOK_URL")

def group_slots_by_category(slots):
    """Group slots by boat category"""
    categorized_slots = {
        "all": slots,
        "katamaran": [],
        "monohull": [],
        "unknown": []
    }
    
    for slot in slots:
        boat_type = slot.get("service_type", "")
        category = get_boat_category(boat_type)
        categorized_slots[category].append(slot)
    
    return categorized_slots
