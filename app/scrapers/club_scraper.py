import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

from app.utils.config import COOKIES_FILE, DATA_DIR, CLUB_ALL_SLOTS_FILE
from app.scrapers.cookie_scraper import save_authenticated_session

load_dotenv()

async def scrape_club_activities_for_days(days=14, filters=None):
    """
    Scrape club activities from calendar_club page for specified number of days.
    
    Args:
        days (int): Number of days to scrape ahead (default: 14)
        filters (dict): Optional filters to apply to activities
        
    Returns:
        list: List of club activity data dictionaries
    """
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
    
    all_activities = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        print("Restoring cookies from previous session...")
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        print("Navigating to club calendar page...")
        await page.goto("https://yamonline.custhelp.com/app/calendar_club")
        try:
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
            return await scrape_club_activities_for_days(days, filters)
        
        await page.wait_for_selector('.dhx_cal_data', state='visible', timeout=10000)
        
        current_date_element = await page.query_selector('.dhx_cal_date')
        if current_date_element:
            current_date = await current_date_element.text_content()
            print(f"Current date: {current_date}")
        else:
            print("Could not find date element. Using system date.")
            current_date = datetime.now().strftime("%d/%m/%Y")
        
        day_activities = await extract_activities_from_page(page, current_date)
        all_activities.extend(day_activities)
        
        for day in range(1, days):
            print(f"Navigating to day {day}...")
            
            next_button = await page.query_selector('.dhx_cal_next_button')
            if next_button:
                await next_button.click()
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception as e:
                    print(f"Warning: Load state timeout: {e}")
                    print("Continuing with calendar navigation...")
                
                await page.wait_for_timeout(1000)
                
                date_element = await page.query_selector('.dhx_cal_date')
                if date_element:
                    date = await date_element.text_content()
                    print(f"Date: {date}")
                else:
                    date = (datetime.now() + timedelta(days=day)).strftime("%d/%m/%Y")
                    print(f"Calculated date: {date}")
                
                day_activities = await extract_activities_from_page(page, date)
                all_activities.extend(day_activities)
            else:
                print("Could not find next day button. Stopping navigation.")
                break
        
        # Apply filters if provided
        filtered_activities = all_activities
        if filters:
            # Future: implement activity filtering
            print(f"Filters not yet implemented: {filters}")
        
        with open(CLUB_ALL_SLOTS_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered_activities if filters else all_activities, f, ensure_ascii=False, indent=2)
        
        print(f"Saved club activities data to {CLUB_ALL_SLOTS_FILE}")
        
        await browser.close()
        return filtered_activities if filters else all_activities

async def extract_activities_from_page(page, date):
    """
    Extract club activities from a single calendar page.
    
    Args:
        page: Playwright page object
        date (str): Current date being processed
        
    Returns:
        list: List of activity data dictionaries
    """
    activities = []
    
    activity_elements = await page.query_selector_all('.dhx_cal_event')
    
    for activity in activity_elements:
        activity_data = {"date": date, "scraped_at": datetime.now().isoformat()}
        
        event_id = await activity.get_attribute('event_id')
        if event_id:
            activity_data["event_id"] = event_id
        
        title_elem = await activity.query_selector('.dhx_title')
        if title_elem:
            time_text = await title_elem.text_content()
            if time_text:
                # Fix time format: change from "end - start" to "start - end"
                time_parts = time_text.strip().split(' - ')
                if len(time_parts) == 2:
                    end_time, start_time = time_parts
                    activity_data["time"] = f"{start_time} - {end_time}"
                else:
                    activity_data["time"] = time_text.strip()
        
        aria_label = await activity.get_attribute('aria-label')
        if aria_label:
            # Parse aria-label to extract activity details
            # Format: " סדנא - סקר דולפינים 11:00 - 07:00 מישל (12) "
            activity_data["aria_label"] = aria_label.strip()
            
            # Extract activity type (first part before first " - ")
            parts = aria_label.strip().split(' - ')
            if len(parts) > 0:
                activity_type = parts[0].strip()
                activity_data["activity_type"] = activity_type
            
            # Extract activity name (second part)
            if len(parts) > 1:
                activity_name_part = parts[1].strip()
                # Remove time information from activity name
                activity_name = re.sub(r'\d+:\d+\s*-\s*\d+:\d+', '', activity_name_part).strip()
                if activity_name:
                    activity_data["activity_name"] = activity_name
            
            # Extract boat name (text in parentheses at the end)
            boat_match = re.search(r'([א-ת\s]+)\s*\((\d+)\)\s*$', aria_label)
            if boat_match:
                boat_name = boat_match.group(1).strip()
                boat_capacity = boat_match.group(2)
                activity_data["boat_name"] = boat_name
                activity_data["boat_capacity"] = int(boat_capacity)
            
            # Extract description (remaining text after removing known parts)
            description_text = aria_label
            for part in parts[:2]:  # Remove activity type and name
                description_text = description_text.replace(part, '', 1).replace(' - ', '', 1)
            # Remove time pattern
            description_text = re.sub(r'\d+:\d+\s*-\s*\d+:\d+', '', description_text)
            # Remove boat info
            description_text = re.sub(r'[א-ת\s]+\s*\(\d+\)\s*$', '', description_text)
            description_text = description_text.strip()
            if description_text:
                activity_data["description"] = description_text
        
        # Check for הרשמה (registration) button - this indicates availability
        registration_button = await activity.query_selector('button[onclick*="onSlotSelection"]')
        activity_data["is_available"] = registration_button is not None
        
        # If available, extract the onclick event ID for direct registration
        if registration_button:
            onclick_attr = await registration_button.get_attribute('onclick')
            if onclick_attr:
                # Extract event ID from onclick="onSlotSelection(319751);"
                event_id_match = re.search(r'onSlotSelection\((\d+)\)', onclick_attr)
                if event_id_match:
                    activity_data["registration_event_id"] = event_id_match.group(1)
        
        if activity_data.get("time"):
            activities.append(activity_data)
    
    print(f"Extracted {len(activities)} activities for {date}")
    available_count = sum(1 for a in activities if a.get('is_available', False))
    print(f"  Available activities: {available_count}")
    
    return activities

async def main():
    """Main function for testing club scraper independently."""
    import sys
    
    days = 14
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number of days: {sys.argv[1]}. Using default: 14 days.")
    
    print(f"Scraping club activities for {days} days...")
    activities = await scrape_club_activities_for_days(days)
    
    if activities:
        print(f"\nScraping completed successfully!")
        print(f"Total activities: {len(activities)}")
        available_activities = [a for a in activities if a.get('is_available', False)]
        print(f"Available activities: {len(available_activities)}")
        
        if available_activities:
            print("\nAvailable activities:")
            for activity in available_activities[:5]:  # Show first 5
                print(f"  - {activity.get('activity_type', 'Unknown')} on {activity.get('date', 'Unknown')}")
                print(f"    Time: {activity.get('time', 'Unknown')}")
                print(f"    Boat: {activity.get('boat_name', 'Unknown')}")
    else:
        print("Failed to scrape club activities.")

if __name__ == "__main__":
    asyncio.run(main())
