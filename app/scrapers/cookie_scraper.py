import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

from app.utils.config import COOKIES_FILE, DATA_DIR, ALL_SLOTS_FILE, get_urls_to_scrape

load_dotenv()

USERNAME = os.getenv("YAM_USERNAME")
PASSWORD = os.getenv("YAM_PASSWORD")

async def save_authenticated_session():
    async with async_playwright() as p:
        # Check if running in GitHub Actions or other CI environment
        is_ci_environment = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
        
        # Force headless mode in CI environments
        browser = await p.chromium.launch(headless=is_ci_environment)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navigating to login page...")
        await page.goto("https://yamonline.custhelp.com/app/utils/login_form")
        try:
            # Wait for load state with a shorter timeout - if it fails, continue anyway
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception as e:
            print(f"Warning: Page load state timeout: {e}")
            print("Continuing with login process anyway...")
        
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
            # Don't use wait_for_navigation as it's deprecated
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Navigation timeout: {e}")
            print("Proceeding with login validation anyway...")
        
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
        
        # Create directory for cookies file if it doesn't exist
        cookies_dir = os.path.dirname(COOKIES_FILE)
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir)
            
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
            output_file = f"{DATA_DIR}/{page_name}.html"
            
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
        
        # Save all results to a single JSON file
        all_data_file = ALL_SLOTS_FILE
        with open(all_data_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Saved all scraped data to {all_data_file}")
        
        await browser.close()
        return results

async def scrape_calendar_slots_for_days(days=14, filters=None):
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
    
    all_slots = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        print("Restoring cookies from previous session...")
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        print("Navigating to calendar slots page...")
        await page.goto(
            "https://yamonline.custhelp.com/app/calendar_slots",
            wait_until="domcontentloaded",
            timeout=60000
        )
        try:
            # Wait for load state with a shorter timeout
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception as e:
            print(f"Warning: Page load state timeout: {e}")
            print("Continuing anyway...")
        
        # Check if we're still on the login page (session expired)
        if "login" in page.url.lower():
            print("Session expired. Re-authenticating...")
            await browser.close()
            success = await save_authenticated_session()
            if not success:
                print("Failed to re-authenticate.")
                return False
            return await scrape_calendar_slots_for_days(days, filters)
        
        all_slots_file = ALL_SLOTS_FILE
        
        await page.wait_for_selector('.dhx_cal_data', state='visible', timeout=10000)
        
        current_date_element = await page.query_selector('.dhx_cal_date')
        if current_date_element:
            current_date = await current_date_element.text_content()
            print(f"Current date: {current_date}")
        else:
            print("Could not find date element. Using system date.")
            current_date = datetime.now().strftime("%d/%m/%Y")
        
        day_slots = await extract_slots_from_page(page, current_date)
        all_slots.extend(day_slots)
        
        for day in range(1, days):
            print(f"Navigating to day {day}...")
            
            next_button = await page.query_selector('.dhx_cal_next_button')
            if next_button:
                await next_button.click()
                try:
                    # Use domcontentloaded instead of networkidle to avoid timeouts
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception as e:
                    print(f"Warning: Load state timeout: {e}")
                    print("Continuing with calendar navigation...")
                
                # Always wait a bit for the calendar to update
                await page.wait_for_timeout(1000)
                
                date_element = await page.query_selector('.dhx_cal_date')
                if date_element:
                    date = await date_element.text_content()
                    print(f"Date: {date}")
                else:
                    date = (datetime.now() + timedelta(days=day)).strftime("%d/%m/%Y")
                    print(f"Calculated date: {date}")
                
                day_slots = await extract_slots_from_page(page, date)
                all_slots.extend(day_slots)
            else:
                print("Could not find next day button. Stopping navigation.")
                break
        
        # Apply filters if provided
        filtered_slots = all_slots
        if filters:
            from app.utils.filter_slots import filter_slots
            filtered_slots = filter_slots(all_slots, **filters)
            print(f"Applied filters: {len(all_slots)} -> {len(filtered_slots)} slots")
        
        with open(all_slots_file, "w", encoding="utf-8") as f:
            json.dump(filtered_slots if filters else all_slots, f, ensure_ascii=False, indent=2)
        
        print(f"Saved slots data to {all_slots_file}")
        
        await browser.close()
        return filtered_slots if filters else all_slots

async def extract_slots_from_page(page, date):
    slots = []
    
    slot_elements = await page.query_selector_all('.dhx_cal_event')
    
    for slot in slot_elements:
        slot_data = {"date": date}
        
        event_id = await slot.get_attribute('event_id')
        if event_id:
            slot_data["event_id"] = event_id
        
        title_elem = await slot.query_selector('.dhx_title')
        if title_elem:
            time_text = await title_elem.text_content()
            if time_text:
                # Fix time format: change from "end - start" to "start - end"
                time_parts = time_text.strip().split(' - ')
                if len(time_parts) == 2:
                    end_time, start_time = time_parts
                    slot_data["time"] = f"{start_time} - {end_time}"
                else:
                    slot_data["time"] = time_text.strip()
        
        aria_label = await slot.get_attribute('aria-label')
        if aria_label:
            parts = aria_label.split('-')
            if len(parts) > 1:
                service_type = parts[1].strip()
                
                # Extract only the Hebrew boat name
                # Format is typically: "HH:MM Hebrew_Name (number)"
                hebrew_name_match = re.search(r'\d+:\d+\s+([א-ת]+(?:\s+[א-ת]+)*)', service_type)
                if hebrew_name_match:
                    service_type = hebrew_name_match.group(1).strip()
                
                slot_data["service_type"] = service_type
        
        order_button = await slot.query_selector('.btnDXNorder')
        slot_data["is_available"] = order_button is not None
        
        if slot_data.get("time"):
            slots.append(slot_data)
    
    print(f"Extracted {len(slots)} slots for {date}")
    return slots

async def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "calendar":
        # Scrape calendar slots for the next 14 days
        await scrape_calendar_slots_for_days(14)
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
