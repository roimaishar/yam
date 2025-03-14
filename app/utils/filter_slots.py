import json
import re

def parse_time(time_str):
    match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if match:
        hour, minute = map(int, match.groups())
        return hour, minute
    return None

def is_in_time_range(time_str, start_hour=9, start_minute=0, end_hour=17, end_minute=0):
    time_parts = parse_time(time_str)
    if not time_parts:
        return False
    
    hour, minute = time_parts
    
    if hour > start_hour or (hour == start_hour and minute >= start_minute):
        if hour < end_hour or (hour == end_hour and minute <= end_minute):
            return True
    
    return False

def extract_boat_name(service_type_str):
    if not service_type_str:
        return ""
    
    parts = service_type_str.split()
    if len(parts) < 2:
        return service_type_str
    
    # The boat name is typically the second part
    # Format: "HH:MM BoatName (capacity)"
    return parts[1].strip() if len(parts) > 1 else ""

def filter_slots(slots, days_ahead=None, time_range=None, service_type=None, only_available=True):
    if not slots:
        return []
    
    filtered_slots = []
    
    # Parse time range
    start_hour, start_minute = 9, 0
    end_hour, end_minute = 17, 0
    
    if time_range:
        time_parts = time_range.split('-')
        if len(time_parts) == 2:
            start_time = time_parts[0].strip()
            end_time = time_parts[1].strip()
            
            start_match = re.search(r'(\d{1,2}):(\d{2})', start_time)
            end_match = re.search(r'(\d{1,2}):(\d{2})', end_time)
            
            if start_match:
                start_hour, start_minute = map(int, start_match.groups())
            if end_match:
                end_hour, end_minute = map(int, end_match.groups())
    
    for slot in slots:
        # Filter by availability
        if only_available and not slot.get("is_available", False):
            continue
        
        # Filter by service type
        if service_type:
            boat_name = extract_boat_name(slot.get("service_type", ""))
            if service_type.lower() != boat_name.lower():
                continue
        
        # Filter by time range
        if not is_in_time_range(slot.get("time", ""), start_hour, start_minute, end_hour, end_minute):
            continue
        
        filtered_slots.append(slot)
    
    return filtered_slots

def load_and_filter_slots(file_path, days_ahead=None, time_range=None, service_type=None, only_available=True):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            slots = json.load(f)
        
        return filter_slots(slots, days_ahead, time_range, service_type, only_available)
    except Exception as e:
        print(f"Error loading or filtering slots: {e}")
        return []
