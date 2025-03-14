import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

from app.utils.config import COOKIES_FILE, DATA_DIR, get_urls_to_scrape
from app.scrapers.cookie_scraper import save_authenticated_session

async def scrape_with_cookies():
    if not os.path.exists(COOKIES_FILE):
        print("No cookie file found. Attempting to authenticate and save cookies...")
        success = await save_authenticated_session()
        if not success:
            print("Failed to authenticate and save cookies.")
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
        
        await context.add_cookies(cookies)
        page = await context.new_page()
        
        success = True
        
        for url in urls_to_scrape:
            page_name = url.split('/')[-1]
            output_file = f"{DATA_DIR}/{page_name}_{timestamp}.html"
            
            try:
                print(f"Scraping {url}...")
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
                
                if "login" in page.url.lower():
                    print("Session expired. Attempting to re-authenticate...")
                    await browser.close()
                    
                    # Try to re-authenticate
                    auth_success = await save_authenticated_session()
                    if not auth_success:
                        print("Failed to re-authenticate.")
                        return False
                    
                    # Try scraping again with new cookies
                    return await scrape_with_cookies()
                
                content = await page.content()
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)
                
                print(f"Saved to {output_file}")
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                success = False
        
        await browser.close()
        return success

if __name__ == "__main__":
    success = asyncio.run(scrape_with_cookies())
    sys.exit(0 if success else 1)
