import asyncio
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.scrapers.cookie_scraper import (
    navigate_with_retry,
    wait_for_selector_with_retry,
    query_selector_with_retry
)
from playwright.async_api import async_playwright

async def test_navigate_with_retry():
    print("Testing navigate_with_retry with invalid URL...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Test with invalid URL to trigger retry
            await navigate_with_retry(page, "https://invalid-domain-that-doesnt-exist.xyz", max_retries=2, delay=2)
            print("❌ Test failed: Expected exception was not raised")
        except Exception as e:
            print(f"✅ Test passed: Exception correctly raised after retries: {e}")
        
        await browser.close()

async def test_wait_for_selector_with_retry():
    print("\nTesting wait_for_selector_with_retry with non-existent selector...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to a simple page
        await page.goto("https://example.com")
        
        try:
            # Test with non-existent selector to trigger retry
            await wait_for_selector_with_retry(page, "#non-existent-element", max_retries=2, delay=2)
            print("❌ Test failed: Expected exception was not raised")
        except Exception as e:
            print(f"✅ Test passed: Exception correctly raised after retries: {e}")
        
        await browser.close()

async def test_query_selector_with_retry():
    print("\nTesting query_selector_with_retry with non-existent selector...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to a simple page
        await page.goto("https://example.com")
        
        # Test with non-existent selector
        element = await query_selector_with_retry(page, "#non-existent-element", max_retries=2, delay=2)
        
        if element is None:
            print("✅ Test passed: Correctly returned None for non-existent selector")
        else:
            print("❌ Test failed: Expected None but got an element")
        
        # Test with existing selector
        element = await query_selector_with_retry(page, "h1", max_retries=2, delay=2)
        
        if element is not None:
            print("✅ Test passed: Correctly found existing element")
        else:
            print("❌ Test failed: Expected to find h1 element but got None")
        
        await browser.close()

async def main():
    print("Running error recovery tests...")
    
    await test_navigate_with_retry()
    await test_wait_for_selector_with_retry()
    await test_query_selector_with_retry()
    
    print("\nAll tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
