import asyncio
import json
import os
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

from app.utils.config import COOKIES_FILE, DATA_DIR, get_urls_to_scrape

load_dotenv()

USERNAME = os.getenv("YAM_USERNAME")
PASSWORD = os.getenv("YAM_PASSWORD")

async def save_authenticated_session():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navigating to login page...")
        await page.goto("https://yamonline.custhelp.com/app/utils/login_form")
        await page.wait_for_load_state("networkidle")
        
        try:
            username_field = await page.query_selector("#rn_LoginForm_0_Username")
            password_field = await page.query_selector("#rn_LoginForm_0_Password")
            
            if username_field and password_field:
                await username_field.fill(USERNAME)
                await password_field.fill(PASSWORD)
                print("Login form auto-filled.")
                
                # Find and click the login button
                login_button = await page.query_selector('input[type="submit"], button[type="submit"], .login-button')
                if login_button:
                    await login_button.click()
                    print("Login button clicked automatically.")
                else:
                    print("Login button not found. Manual intervention required.")
            else:
                print("Could not find login form elements for auto-fill.")
        except Exception as e:
            print(f"Error auto-filling form: {e}")
        
        # Wait for navigation to complete after login
        try:
            print("Waiting for login to complete...")
            await page.wait_for_navigation(timeout=10000)
        except Exception as e:
            print(f"Navigation timeout: {e}")
        
        # Check if we're still on the login page
        if "login" in page.url.lower():
            print("\n=== MANUAL INTERVENTION REQUIRED ===")
            print("1. Complete the login process in the browser window")
            print("2. Once logged in, the cookies will be saved for future use")
            print("3. Waiting for login to complete...")
            
            while "login" in page.url.lower():
                await asyncio.sleep(1)
        
        print("Login successful! Saving cookies...")
        
        cookies = await context.cookies()
        
        # Create data directory if it doesn't exist
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
        
        print(f"Cookies saved to {COOKIES_FILE}")
        await browser.close()
        return True

async def scrape_with_saved_cookies():
    if not os.path.exists(COOKIES_FILE):
        print("No saved cookies found. Please run save_authenticated_session() first.")
        return False
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    with open(COOKIES_FILE, "r") as f:
        cookies = json.load(f)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    urls_to_scrape = get_urls_to_scrape()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        print("Restoring cookies from previous session...")
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        results = {}
        
        for url in urls_to_scrape:
            page_name = url.split('/')[-1]
            output_file = f"{DATA_DIR}/{page_name}_{timestamp}.html"
            
            print(f"Scraping {url}...")
            try:
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
                
                if "login" in page.url.lower():
                    print("Session expired or invalid cookies. Please re-authenticate.")
                    await browser.close()
                    return False
                
                content = await page.content()
                results[url] = content
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)
                
                print(f"Saved {url} to {output_file}")
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
        
        await browser.close()
        return results

async def scrape_calendar_slots_for_days(days=14, filters=None, max_retries=3, retry_delay=5):
    if not os.path.exists(COOKIES_FILE):
        print("No saved cookies found. Performing authentication first...")
        success = await save_authenticated_session()
        if not success:
            print("Failed to authenticate.")
            return False
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    with open(COOKIES_FILE, "r") as f:
        cookies = json.load(f)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_slots = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        print("Restoring cookies from previous session...")
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        # Navigate to the calendar slots page
        print("Navigating to calendar slots page...")
        await navigate_with_retry(page, "https://yamonline.custhelp.com/app/calendar_slots", max_retries, retry_delay)
        
        # Check if we need to re-authenticate
        if "login" in page.url.lower():
            print("Session expired. Re-authenticating...")
            await browser.close()
            success = await save_authenticated_session()
            if not success:
                print("Failed to re-authenticate.")
                return False
            return await scrape_calendar_slots_for_days(days, filters, max_retries, retry_delay)
        
        # Create a file to store all slots data
        all_slots_file = f"{DATA_DIR}/all_slots_{timestamp}.json"
        
        # Wait for the calendar to load with retry
        try:
            await wait_for_selector_with_retry(page, '.dhx_cal_data', max_retries, retry_delay)
        except Exception as e:
            print(f"Error waiting for calendar to load: {e}")
            print("Attempting to continue anyway...")
        
        # Get current date from the calendar
        current_date_element = await query_selector_with_retry(page, '.dhx_cal_date', max_retries, retry_delay)
        if current_date_element:
            current_date = await current_date_element.text_content()
            print(f"Current date: {current_date}")
        else:
            print("Could not find date element. Using system date.")
            current_date = datetime.now().strftime("%d/%m/%Y")
        
        # Extract slots for the current day
        day_slots = await extract_slots_from_page(page, current_date)
        all_slots.extend(day_slots)
        
        # Navigate through the next days
        for day in range(1, days):
            print(f"Navigating to day {day}...")
            
            # Find and click the next day button
            next_button = await query_selector_with_retry(page, '.dhx_cal_next_button', max_retries, retry_delay)
            if next_button:
                try:
                    await next_button.click()
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(1000)  # Wait for calendar to update
                except Exception as e:
                    print(f"Error clicking next button: {e}")
                    print("Retrying...")
                    try:
                        await next_button.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(1000)
                    except Exception as e2:
                        print(f"Failed to click next button after retry: {e2}")
                        continue
                
                # Get the current date after navigation
                date_element = await query_selector_with_retry(page, '.dhx_cal_date', max_retries, retry_delay)
                if date_element:
                    date = await date_element.text_content()
                    print(f"Date: {date}")
                else:
                    # If date element not found, calculate date based on current date
                    try:
                        date = (datetime.strptime(current_date, "%d/%m/%Y") + timedelta(days=day)).strftime("%d/%m/%Y")
                    except ValueError:
                        date = (datetime.now() + timedelta(days=day)).strftime("%d/%m/%Y")
                    print(f"Calculated date: {date}")
                
                # Extract slots for this day
                day_slots = await extract_slots_from_page(page, date)
                all_slots.extend(day_slots)
            else:
                print("Could not find next day button. Stopping navigation.")
                break
        
        # Apply filters if provided
        if filters:
            filtered_slots = filter_slots(all_slots, filters)
            print(f"Filtered from {len(all_slots)} to {len(filtered_slots)} slots")
            all_slots = filtered_slots
        
        # Save all slots to a single JSON file
        with open(all_slots_file, "w", encoding="utf-8") as f:
            json.dump(all_slots, f, ensure_ascii=False, indent=2)
        
        print(f"Saved all slots data to {all_slots_file}")
        await browser.close()
        return all_slots

async def navigate_with_retry(page, url, max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Navigation failed (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"Navigation failed after {max_retries} attempts: {e}")
                raise

async def wait_for_selector_with_retry(page, selector, max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            return await page.wait_for_selector(selector, state='visible', timeout=10000)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Wait for selector '{selector}' failed (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"Wait for selector '{selector}' failed after {max_retries} attempts: {e}")
                raise

async def query_selector_with_retry(page, selector, max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            element = await page.query_selector(selector)
            if element:
                return element
            if attempt < max_retries - 1:
                print(f"Selector '{selector}' not found (attempt {attempt+1}/{max_retries})")
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"Selector '{selector}' not found after {max_retries} attempts")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Query selector '{selector}' failed (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"Query selector '{selector}' failed after {max_retries} attempts: {e}")
                return None

def filter_slots(slots, filters):
    filtered_slots = slots.copy()
    
    if not filters:
        return filtered_slots
    
    # Filter by boat name
    if 'boat_name' in filters:
        boat_names = [name.lower() for name in filters['boat_name']] if isinstance(filters['boat_name'], list) else [filters['boat_name'].lower()]
        filtered_slots = [slot for slot in filtered_slots if 
                         'boat_name' in slot and 
                         any(name in slot['boat_name'].lower() for name in boat_names)]
    
    # Filter by minimum capacity
    if 'min_capacity' in filters:
        min_capacity = int(filters['min_capacity'])
        filtered_slots = [slot for slot in filtered_slots if 
                         'capacity' in slot and slot['capacity'] >= min_capacity]
    
    # Filter by maximum capacity
    if 'max_capacity' in filters:
        max_capacity = int(filters['max_capacity'])
        filtered_slots = [slot for slot in filtered_slots if 
                         'capacity' in slot and slot['capacity'] <= max_capacity]
    
    # Filter by time range
    if 'start_time_after' in filters:
        start_time = filters['start_time_after']
        filtered_slots = [slot for slot in filtered_slots if 
                         'start_time' in slot and slot['start_time'] >= start_time]
    
    if 'start_time_before' in filters:
        start_time = filters['start_time_before']
        filtered_slots = [slot for slot in filtered_slots if 
                         'start_time' in slot and slot['start_time'] <= start_time]
    
    # Filter by day of week
    if 'day_of_week' in filters:
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'he_IL.UTF-8')  # Set locale for Hebrew day names
        except locale.Error:
            print("Hebrew locale not available, using system default")
        
        days_of_week = filters['day_of_week'] if isinstance(filters['day_of_week'], list) else [filters['day_of_week']]
        
        # Hebrew day names mapping
        hebrew_day_map = {
            'sunday': 'ראשון',
            'monday': 'שני',
            'tuesday': 'שלישי',
            'wednesday': 'רביעי',
            'thursday': 'חמישי',
            'friday': 'שישי',
            'saturday': 'שבת'
        }
        
        # Convert English day names to Hebrew
        hebrew_days = []
        for day in days_of_week:
            day = day.lower()
            if day in hebrew_day_map:
                hebrew_days.append(hebrew_day_map[day])
            else:
                hebrew_days.append(day)
        
        filtered_slots = [slot for slot in filtered_slots if 
                         'date' in slot and 
                         any(day in slot['date'] for day in hebrew_days)]
    
    return filtered_slots

async def extract_slots_from_page(page, date):
    slots = []
    
    # Get the HTML content of the page
    content = await page.content()
    
    # Save the HTML content for debugging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = date.replace('/', '_').replace(' ', '_')
    output_file = f"{DATA_DIR}/calendar_slots_{date_str}_{timestamp}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Extract slot information using the specific structure of YAM Online calendar
    slot_elements = await page.query_selector_all('.dhx_cal_event')
    
    import re
    for slot in slot_elements:
        slot_data = {"date": date}
        
        # Extract event ID
        event_id = await slot.get_attribute('event_id')
        if event_id:
            slot_data["event_id"] = event_id
        
        # Extract time from title
        title_elem = await slot.query_selector('.dhx_title')
        if title_elem:
            time_text = await title_elem.text_content()
            if time_text:
                # Normalize the time format (YAM shows end time - start time)
                time_parts = time_text.strip().split(' - ')
                if len(time_parts) == 2:
                    end_time, start_time = time_parts  # Reversed in the original
                    normalized_time = f"{start_time} - {end_time}"
                    slot_data["time"] = normalized_time
                    slot_data["start_time"] = start_time
                    slot_data["end_time"] = end_time
                else:
                    slot_data["time"] = time_text.strip()
        
        # Extract service type (boat name) from aria-label
        aria_label = await slot.get_attribute('aria-label')
        if aria_label:
            parts = aria_label.split('-')
            if len(parts) > 1:
                service_type = parts[1].strip()
                slot_data["service_type"] = service_type
                
                # Extract boat name and capacity if available
                boat_match = re.search(r'([^\(]+)\s*\((\d+)\)', service_type)
                if boat_match:
                    slot_data["boat_name"] = boat_match.group(1).strip()
                    slot_data["capacity"] = int(boat_match.group(2))
        
        # Check if the slot is available (has an order button)
        order_button = await slot.query_selector('.btnDXNorder')
        slot_data["is_available"] = order_button is not None
        
        # Only add slots that have time information
        if slot_data.get("time"):
            slots.append(slot_data)
    
    print(f"Extracted {len(slots)} slots for {date}")
    return slots

async def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "calendar":
        # Parse filters if provided
        filters = {}
        if len(sys.argv) > 3 and sys.argv[3] == "filter":
            for i in range(4, len(sys.argv), 2):
                if i + 1 < len(sys.argv):
                    key = sys.argv[i]
                    value = sys.argv[i + 1]
                    
                    # Handle list values (comma-separated)
                    if ',' in value:
                        filters[key] = value.split(',')
                    else:
                        filters[key] = value
        
        # Get number of days to scrape
        days = 14
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                print(f"Invalid number of days: {sys.argv[2]}. Using default: 14 days.")
        
        # Scrape calendar slots with filters
        await scrape_calendar_slots_for_days(days, filters)
        return
    
    # Regular scraping logic
    if os.path.exists(COOKIES_FILE):
        print("Found saved cookies. Attempting to use them...")
        results = await scrape_with_saved_cookies()
        
        if results:
            print("Scraping completed successfully using saved cookies!")
            return
        
        print("Saved cookies are invalid or expired.")
    
    print("Performing authentication to get new cookies...")
    success = await save_authenticated_session()
    
    if not success:
        print("Failed to authenticate.")
        return
    
    results = await scrape_with_saved_cookies()
    
    if results:
        print("Scraping completed successfully with new cookies!")
    else:
        print("Failed to scrape with new cookies. Please check your credentials.")

if __name__ == "__main__":
    asyncio.run(main())
