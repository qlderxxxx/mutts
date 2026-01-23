import os
import sys
from datetime import datetime, timedelta

# Mock Supabase envs to allow import
os.environ['SUPABASE_URL'] = 'https://example.supabase.co'
os.environ['SUPABASE_KEY'] = 'dummy-key'

try:
    from backfill_from_archive import get_meeting_urls_for_date
except ImportError:
    # Add current dir to path if needed
    sys.path.append(os.getcwd())
    from backfill_from_archive import get_meeting_urls_for_date

from playwright.sync_api import sync_playwright

def debug_race_buttons(meeting_url):
    # Convert to results URL (matching scraper.py logic)
    results_url = meeting_url.replace('/form-guides/', '/results/').replace('/fields/', '/')
    
    print(f"\n{'='*50}")
    print(f"Debugging URL: {results_url}")
    print(f"{'='*50}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("Navigating...")
        try:
            page.goto(results_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(5000) # Wait for JS
        except Exception as e:
            print(f"Navigation failed: {e}")
            browser.close()
            return
            
        # Simulate the clicking loop
        print("\nChecking .meeting-events-nav__item:")
        init_items = page.query_selector_all('.meeting-events-nav__item')
        count = len(init_items)
        print(f"Found {count} items initially")
        
        print("\nSimulating click loop...")
        
        # We found 'count' buttons initially
        for i in range(count):
            print(f"\n[Iteration {i+1}/{count}]")
            
            # Re-query (matching scraper logic)
            items = page.query_selector_all('.meeting-events-nav__item')
            buttons = [item for item in items if item.text_content() and item.text_content().strip().isdigit()]
            
            print(f"  Found {len(buttons)} buttons on re-query")
            
            if i < len(buttons):
                btn = buttons[i]
                race_num = btn.text_content().strip()
                print(f"  Targeting Race {race_num}")
                
                try:
                    # Click
                    btn.click(timeout=2000)
                    print("  Clicked.")
                    page.wait_for_timeout(2000)
                    
                    # Verify content update (check for race number in headers/table)
                    # Just debug print title or something unique
                    # This helps verify if page actually changed
                    # maybe check active class?
                    active_btn = page.query_selector('.meeting-events-nav__item.active') # assuming active class
                    if active_btn:
                        print(f"  Active button text: {active_btn.text_content().strip()}")
                        
                except Exception as e:
                    print(f"  Click failed: {e}")
            else:
                print("  Index out of range for buttons list!")

        browser.close()

if __name__ == "__main__":
    # Test specific URL provided by user
    target_url = "https://www.thegreyhoundrecorder.com.au/results/sandown-park/250177/"
    print(f"Testing user provided URL: {target_url}")
    
    debug_race_buttons(target_url)
    
    # Also take a screenshot for visual debugging
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto(target_url, wait_until='networkidle')
        page.screenshot(path="debug_sandown.png")
        print("Captured debug_sandown.png")
        browser.close()
