import re

def parse_time(time_str):
    """Extract hours and minutes from a time string"""
    match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if match:
        hour, minute = map(int, match.groups())
        return hour * 60 + minute  # Convert to minutes for easier comparison
    return None

def merge_consecutive_slots(slots):
    """
    Merge consecutive time slots for the same boat on the same day.
    Returns a new list with merged slots, original slots are not modified.
    """
    if not slots:
        return []
    
    # Group slots by date and boat type
    grouped_slots = {}
    for slot in slots:
        date = slot.get('date', '')
        boat = slot.get('service_type', '')
        is_available = slot.get('is_available', False)
        
        # Skip unavailable slots
        if not is_available:
            continue
            
        key = f"{date}_{boat}"
        if key not in grouped_slots:
            grouped_slots[key] = []
        grouped_slots[key].append(slot)
    
    result = []
    
    # Process each group
    for key, group in grouped_slots.items():
        # Sort slots by start time
        sorted_slots = sorted(group, key=lambda x: parse_time(x.get('time', '').split(' - ')[0]))
        
        # Find consecutive slots
        current_sequence = [sorted_slots[0]]
        
        for i in range(1, len(sorted_slots)):
            prev_slot = current_sequence[-1]
            curr_slot = sorted_slots[i]
            
            prev_time_parts = prev_slot.get('time', '').split(' - ')
            curr_time_parts = curr_slot.get('time', '').split(' - ')
            
            if len(prev_time_parts) == 2 and len(curr_time_parts) == 2:
                prev_end = prev_time_parts[1].strip()
                curr_start = curr_time_parts[0].strip()
                
                # Check if slots are consecutive
                if prev_end == curr_start:
                    current_sequence.append(curr_slot)
                else:
                    # Process the completed sequence
                    result.extend(process_sequence(current_sequence))
                    current_sequence = [curr_slot]
            else:
                # Invalid time format, treat as non-consecutive
                result.extend(process_sequence(current_sequence))
                current_sequence = [curr_slot]
        
        # Process the last sequence
        result.extend(process_sequence(current_sequence))
    
    return result

def process_sequence(sequence):
    """Process a sequence of consecutive slots"""
    if not sequence:
        return []
        
    if len(sequence) == 1:
        # Single slot, no merging needed
        return sequence
    
    # Create a merged slot
    first_slot = sequence[0]
    last_slot = sequence[-1]
    
    first_time_parts = first_slot.get('time', '').split(' - ')
    last_time_parts = last_slot.get('time', '').split(' - ')
    
    if len(first_time_parts) != 2 or len(last_time_parts) != 2:
        # Invalid time format, return original
        return sequence
    
    start_time = first_time_parts[0].strip()
    end_time = last_time_parts[1].strip()
    
    merged_slot = {
        'date': first_slot.get('date', ''),
        'service_type': first_slot.get('service_type', ''),
        'time': f"{start_time} - {end_time}",
        'is_available': True,
        'slots': len(sequence),  # Add count of merged slots
        'event_ids': [slot.get('event_id') for slot in sequence if 'event_id' in slot]
    }
    
    return [merged_slot]

def format_merged_slots_for_notification(merged_slots):
    """Format merged slots for notification, with additional slot count information"""
    formatted_slots = []
    
    for slot in merged_slots:
        formatted_slot = slot.copy()
        
        # Add slot count to the formatted message if it exists
        if 'slots' in slot and slot['slots'] > 1:
            formatted_slot['slots_info'] = f"• Slots: {slot['slots']}"
        
        formatted_slots.append(formatted_slot)
    
    return formatted_slots
