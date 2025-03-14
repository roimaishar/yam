import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

from app.utils.config import COOKIES_FILE, DATA_DIR
from app.scrapers.cookie_scraper import (
    save_authenticated_session,
    navigate_with_retry,
    wait_for_selector_with_retry,
    query_selector_with_retry
)

async def book_slot(event_id, max_retries=3, retry_delay=5):
    if not os.path.exists(COOKIES_FILE):
        print("No saved cookies found. Performing authentication first...")
        success = await save_authenticated_session()
        if not success:
            print("Failed to authenticate.")
            return False
    
    with open(COOKIES_FILE, "r") as f:
        cookies = json.load(f)
    
    print(f"Attempting to book slot with event_id: {event_id}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see the browser
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
            return await book_slot(event_id, max_retries, retry_delay)
        
        # Wait for the calendar to load
        try:
            await wait_for_selector_with_retry(page, '.dhx_cal_data', max_retries, retry_delay)
        except Exception as e:
            print(f"Error waiting for calendar to load: {e}")
            await browser.close()
            return False
        
        # Find the specific slot by event_id
        print(f"Looking for slot with event_id: {event_id}")
        slot_selector = f".dhx_cal_event[event_id='{event_id}']"
        
        slot = await query_selector_with_retry(page, slot_selector, max_retries, retry_delay)
        if not slot:
            print(f"Could not find slot with event_id: {event_id}")
            await browser.close()
            return False
        
        # Find and click the order button
        order_button = await query_selector_with_retry(slot, ".btnDXNorder", max_retries, retry_delay)
        if not order_button:
            print(f"Slot with event_id {event_id} is not available for booking")
            await browser.close()
            return False
        
        # Click the order button to start the booking process
        print("Clicking order button...")
        await order_button.click()
        await page.wait_for_load_state("networkidle")
        
        # Take a screenshot of the initial response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_screenshot_path = f"{DATA_DIR}/booking_initial_{timestamp}.png"
        await page.screenshot(path=initial_screenshot_path)
        print(f"Saved initial response screenshot to {initial_screenshot_path}")
        
        # Check for failure message "הרישום נכשל"
        page_content = await page.content()
        if "הרישום נכשל" in page_content:
            print("Booking failed: Registration failed message detected")
            await browser.close()
            return False
        
        # Check for confirmation message "אישור הזמנה"
        if "אישור הזמנה" in page_content:
            print("Booking is available and waiting for confirmation")
            
            # Wait for user input before proceeding
            print("\n" + "="*50)
            print("BOOKING CONFIRMATION REQUIRED")
            print("The slot is available for booking.")
            print("A screenshot has been saved to:", initial_screenshot_path)
            print("To complete the booking, you need to run this command with --confirm flag:")
            print(f"python -m app.main book {event_id} --confirm")
            print("="*50 + "\n")
            
            # Take another screenshot of the confirmation form
            confirm_screenshot_path = f"{DATA_DIR}/booking_confirm_form_{timestamp}.png"
            await page.screenshot(path=confirm_screenshot_path)
            print(f"Saved confirmation form screenshot to {confirm_screenshot_path}")
            
            # Check if we should proceed with confirmation
            import sys
            if len(sys.argv) > 3 and sys.argv[3] == "--confirm":
                print("Confirmation flag detected. Proceeding with booking confirmation...")
                
                # Find and click the confirm button
                confirm_button = await query_selector_with_retry(page, "#btnDXNsaveCal", max_retries, retry_delay)
                if confirm_button:
                    await confirm_button.click()
                    await page.wait_for_load_state("networkidle")
                    
                    # Take a final screenshot after confirmation
                    final_screenshot_path = f"{DATA_DIR}/booking_completed_{timestamp}.png"
                    await page.screenshot(path=final_screenshot_path)
                    print(f"Saved final booking screenshot to {final_screenshot_path}")
                    
                    print("Booking has been confirmed!")
                else:
                    print("Could not find confirmation button")
            else:
                print("Booking was not confirmed. Run with --confirm flag to complete the booking.")
        else:
            print("Neither failure nor confirmation message was detected.")
            print("Unexpected response. Please check the screenshot.")
        
        # Keep the browser open for a moment so the user can see the result
        await asyncio.sleep(5)
        await browser.close()
        return True

async def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.scrapers.booking_scraper <event_id> [--confirm]")
        return
    
    event_id = sys.argv[1]
    success = await book_slot(event_id)
    
    if success:
        print(f"Booking process for event_id {event_id} completed")
    else:
        print(f"Booking process for event_id {event_id} failed")

if __name__ == "__main__":
    asyncio.run(main())
