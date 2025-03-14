import json
from bs4 import BeautifulSoup
import glob

from app.utils.config import DATA_DIR, ALL_EXTRACTED_DATA_FILE

def extract_calendar_slots(html_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    slots_data = []
    
    slots_container = soup.select('.calendar-slots, .slots-container, .time-slots')
    
    if not slots_container:
        print(f"No slots container found in {html_file}")
        return slots_data
    
    slot_elements = soup.select('.slot, .time-slot, .calendar-item')
    
    if not slot_elements:
        print(f"No slot elements found in {html_file}")
        return slots_data
    
    for slot in slot_elements:
        slot_data = {}
        
        date_elem = slot.select_one('.date, .slot-date, .time')
        if date_elem:
            slot_data['date'] = date_elem.text.strip()
        
        avail_elem = slot.select_one('.availability, .status, .slot-status')
        if avail_elem:
            slot_data['availability'] = avail_elem.text.strip()
        
        price_elem = slot.select_one('.price, .cost, .slot-price')
        if price_elem:
            slot_data['price'] = price_elem.text.strip()
        
        is_available = not ('disabled' in slot.get('class', []) or 'unavailable' in slot.get('class', []))
        slot_data['is_available'] = is_available
        
        if slot_data:
            slots_data.append(slot_data)
    
    return slots_data

def process_all_calendar_files():
    calendar_files = glob.glob(f'{DATA_DIR}/calendar_slots_*.html')
    
    if not calendar_files:
        print("No calendar slot files found")
        return
    
    all_results = {}
    
    for file in calendar_files:
        print(f"Processing {file}...")
        
        try:
            slots = extract_calendar_slots(file)
            
            if slots:
                file_name = file.split('/')[-1]
                all_results[file_name] = slots
                print(f"Extracted {len(slots)} slots from {file}")
            else:
                print(f"No slots found in {file}")
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    # Save all extracted data to a single JSON file
    combined_output_file = ALL_EXTRACTED_DATA_FILE
    with open(combined_output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved all extracted data to {combined_output_file}")
    
    return all_results

if __name__ == "__main__":
    process_all_calendar_files()
