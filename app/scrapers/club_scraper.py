import asyncio
import json
import math
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from app.utils.config import COOKIES_FILE, DATA_DIR, CLUB_ALL_SLOTS_FILE
from app.scrapers.cookie_scraper import save_authenticated_session

load_dotenv()

HEBREW_DAYS = [
    "ראשון",
    "שני",
    "שלישי",
    "רביעי",
    "חמישי",
    "שישי",
    "שבת",
]

HEBREW_MONTHS = [
    "ינואר",
    "פברואר",
    "מרץ",
    "אפריל",
    "מאי",
    "יוני",
    "יולי",
    "אוגוסט",
    "ספטמבר",
    "אוקטובר",
    "נובמבר",
    "דצמבר",
]

def _parse_scheduler_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    cleaned = date_str.replace("Z", "+00:00") if "Z" in date_str else date_str
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        try:
            return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

def _combine_date_with_time(base_date: Optional[datetime], time_str: Optional[str]) -> Optional[datetime]:
    if not base_date:
        return None
    if not time_str:
        return base_date
    try:
        hours, minutes = [int(part) for part in time_str.split(":")[:2]]
        return base_date.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    except ValueError:
        return base_date

def _format_hebrew_date(dt: datetime) -> str:
    day_index = int(dt.strftime("%w"))
    day_name = HEBREW_DAYS[day_index]
    month_name = HEBREW_MONTHS[dt.month - 1]
    return f"{day_name}, {dt.day} {month_name} {dt.year}"

def _parse_boat_details(event_data: Dict) -> (Optional[str], Optional[int]):
    participant = event_data.get("participant") or ""
    match = re.search(r"([א-ת\s]+)\s*\((\d+)\)", participant)
    if match:
        return match.group(1).strip(), int(match.group(2))
    room_name = event_data.get("roomName")
    return room_name, None

def _build_activity_record(event_data: Dict, week_label: str, scraped_at: str) -> Optional[Dict]:
    start_base = _parse_scheduler_date(event_data.get("eventDate") or event_data.get("startDate"))
    end_base = _parse_scheduler_date(event_data.get("eventEndDate") or event_data.get("endDate"))
    start_dt = _combine_date_with_time(start_base, event_data.get("startHour"))
    end_dt = _combine_date_with_time(end_base, event_data.get("endHour"))
    if not start_dt or not end_dt:
        return None

    event_id = str(event_data.get("id"))
    date_iso = start_dt.date().isoformat()
    time_range = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    activity_id = f"{event_id}_{start_dt.strftime('%Y%m%d%H%M')}"

    space_limit = event_data.get("spaceLimit")
    num_participants = event_data.get("num_participants")
    available_spots = None
    if space_limit is not None and num_participants is not None:
        try:
            limit_value = int(space_limit)
            participants_value = int(num_participants)
            available_spots = max(limit_value - participants_value, 0)
        except (TypeError, ValueError):
            available_spots = None

    is_available = False
    if available_spots is not None:
        is_available = available_spots > 0
    elif event_data.get("spaceLimit") is None and event_data.get("num_participants") is None:
        is_available = True

    boat_name, boat_capacity = _parse_boat_details(event_data)
    activity_type = event_data.get("activityTypeName") or event_data.get("productTypeName") or ""
    activity_name_raw = event_data.get("subject") or event_data.get("text") or ""
    description_raw = event_data.get("solution") or ""
    activity_name = re.sub(r"<[^>]+>", "", activity_name_raw)
    description = re.sub(r"<[^>]+>", "", description_raw)

    return {
        "activity_id": activity_id,
        "event_id": event_id,
        "registration_event_id": event_id,
        "date": _format_hebrew_date(start_dt),
        "date_iso": date_iso,
        "start_datetime": start_dt.isoformat(),
        "end_datetime": end_dt.isoformat(),
        "time": time_range,
        "activity_type": activity_type.strip(),
        "activity_name": activity_name.strip(),
        "boat_name": boat_name.strip() if isinstance(boat_name, str) else boat_name,
        "boat_capacity": boat_capacity,
        "available_spots": available_spots,
        "is_available": is_available,
        "description": description.strip(),
        "week_label": week_label,
        "scraped_at": scraped_at,
    }

async def _collect_scheduler_events(page) -> Dict:
    return await page.evaluate(
        """
        () => {
            if (typeof scheduler === 'undefined') {
                return [];
            }
            return scheduler.getEvents().map((event) => ({
                id: event.id,
                startDate: event.startDate || event.start_date?.toISOString?.() || event.eventDate,
                endDate: event.endDate || event.end_date?.toISOString?.() || event.eventEndDate,
                eventDate: event.eventDate,
                eventEndDate: event.eventEndDate,
                startHour: event.startHour,
                endHour: event.endHour,
                activityTypeName: event.activityTypeName,
                productTypeName: event.productTypeName,
                subject: event.subject,
                text: event.text,
                participant: event.participant,
                roomName: event.roomName,
                num_participants: event.num_participants,
                spaceLimit: event.spaceLimit,
                solution: event.solution,
            }));
        }
        """
    )

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
        await page.goto("https://yamonline.custhelp.com/app/calendar_club", wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_selector('.dhx_cal_data', state='visible', timeout=10000)
        except Exception as e:
            print(f"Warning: Calendar container not visible yet: {e}")
        
        if "login" in page.url.lower():
            print("Session expired. Re-authenticating...")
            await browser.close()
            success = await save_authenticated_session()
            if not success:
                print("Failed to re-authenticate.")
                return False
            return await scrape_club_activities_for_days(days, filters)
        
        scraped_at = datetime.now().isoformat()
        collected: Dict[str, Dict] = {}
        today = datetime.now().date()
        last_date = today + timedelta(days=days - 1)
        weeks_to_fetch = max(1, math.ceil(days / 7))
        
        for week_index in range(weeks_to_fetch):
            await page.wait_for_function("typeof scheduler !== 'undefined'", timeout=10000)
            await page.wait_for_timeout(250)
            events = await _collect_scheduler_events(page)
            week_label_el = await page.query_selector('.dhx_cal_date')
            week_label = await week_label_el.text_content() if week_label_el else ""
            print(f"Week {week_index + 1} label: {week_label}")
            
            for event_data in events:
                activity = _build_activity_record(event_data, week_label, scraped_at)
                if not activity:
                    continue
                activity_date = datetime.fromisoformat(activity["date_iso"]).date()
                if activity_date < today or activity_date > last_date:
                    continue
                collected[activity["activity_id"]] = activity
            
            if week_index == weeks_to_fetch - 1:
                break
            next_button = await page.query_selector('.dhx_cal_next_button')
            if not next_button:
                print("Could not find next week button. Stopping navigation.")
                break
            await next_button.click()
            await page.wait_for_timeout(500)
        
        activities = sorted(
            collected.values(),
            key=lambda item: (item["date_iso"], item["start_datetime"])
        )
        
        if filters:
            print(f"Filters not yet implemented: {filters}")
        
        with open(CLUB_ALL_SLOTS_FILE, "w", encoding="utf-8") as f:
            json.dump(activities, f, ensure_ascii=False, indent=2)
        
        print(f"Saved club activities data to {CLUB_ALL_SLOTS_FILE}")
        
        await browser.close()
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
