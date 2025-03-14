import json
from bs4 import BeautifulSoup
import glob

from app.utils.config import DATA_DIR, ALL_EXTRACTED_DATA_FILE

def extract_calendar_slots(html_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    slots_data = []
    
    date_containers = soup.select('.dhx_scale_holder_now')
    
    if not date_containers:
        print(f"No date containers found in {html_file}")
        return slots_data
    
    for date_container in date_containers:
        if 'aria-label' not in date_container.attrs:
            continue
            
        date = date_container['aria-label']
        
        slot_elements = date_container.select('.dhx_cal_event')
        
        for slot in slot_elements:
            slot_data = {}
            slot_data['date'] = date
            
            if 'aria-label' in slot.attrs:
                label = slot['aria-label'].strip()
                slot_data['full_label'] = label
                
                time_parts = label.split(' - ')
                if len(time_parts) >= 2:
                    slot_data['end_time'] = time_parts[0].strip()
                    slot_data['start_time'] = time_parts[1].strip().split(' ')[0]
                    
                    boat_parts = ' '.join(time_parts[1].strip().split(' ')[1:])
                    if boat_parts:
                        slot_data['boat'] = boat_parts
            
            event_id = slot.get('event_id')
            if event_id:
                slot_data['event_id'] = event_id
            
            slot_data['is_available'] = True
            
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
    
    combined_output_file = ALL_EXTRACTED_DATA_FILE
    with open(combined_output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved all extracted data to {combined_output_file}")
    
    return all_results

if __name__ == "__main__":
    process_all_calendar_files()
