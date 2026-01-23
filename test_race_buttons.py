"""
Test script to scrape all races from a meeting by clicking through race buttons
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

def scrape_all_races_from_meeting(results_url: str, meeting_name: str):
    """
    Scrape all race results by clicking through race navigation buttons
    """
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print(f"Navigating to {results_url}...")
        page.goto(results_url, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(2000)
        
        # Find all race buttons - they're numbered (1, 2, 3, etc.)
        # Look for buttons or links in the race navigation area
        race_buttons = page.query_selector_all('div.race-navigation button, nav.race-nav button, button[data-race]')
        
        if not race_buttons:
            # Try finding by text content (buttons with numbers)
            all_buttons = page.query_selector_all('button')
            race_buttons = [btn for btn in all_buttons if btn.text_content().strip().isdigit()]
        
        num_races = len(race_buttons)
        print(f"Found {num_races} race buttons")
        
        if num_races == 0:
            # No buttons found, just scrape current page
            print("No race buttons found, scraping current page only")
            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.select_one('table.results-event__table')
            if table:
                print("Found 1 result table")
                # Parse it
            return results
        
        # Click through each race button
        for i in range(num_races):
            try:
                # Re-query buttons each time (DOM might update)
                current_buttons = page.query_selector_all('div.race-navigation button, nav.race-nav button, button[data-race]')
                if not current_buttons:
                    all_buttons = page.query_selector_all('button')
                    current_buttons = [btn for btn in all_buttons if btn.text_content().strip().isdigit()]
                
                if i < len(current_buttons):
                    button_text = current_buttons[i].text_content().strip()
                    print(f"\nClicking race button: {button_text}")
                    
                    current_buttons[i].click()
                    page.wait_for_timeout(1500)  # Wait for content to update
                    
                    # Get the updated page content
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find the result table
                    table = soup.select_one('table.results-event__table')
                    if table:
                        print(f"  Found result table for race {button_text}")
                        # Here you would parse the table
                        # For now, just count rows
                        rows = table.select('tr')[1:]  # Skip header
                        print(f"  {len(rows)} runners")
                    else:
                        print(f"  No result table found for race {button_text}")
            
            except Exception as e:
                print(f"Error clicking race {i+1}: {e}")
                continue
        
        browser.close()
    
    return results

if __name__ == '__main__':
    # Test with Ascot Park from the screenshot
    test_url = "https://www.thegreyhoundrecorder.com.au/results/ascot-park/250122/"
    scrape_all_races_from_meeting(test_url, "Ascot Park")
