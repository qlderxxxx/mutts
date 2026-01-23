#!/usr/bin/env python3
"""
Simple debug - just get the HTML and see what's there
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://www.thegreyhoundrecorder.com.au/form-guides/addington/fields/250123/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print(f"Loading {url}...")
    page.goto(url, timeout=60000, wait_until='networkidle')
    
    content = page.content()
    browser.close()
    
    soup = BeautifulSoup(content, 'lxml')
    
    # Find Race 1
    race_events = soup.select('.form-guide-field-event')
    print(f"\nFound {len(race_events)} race events\n")
    
    if race_events:
        race1 = race_events[0]
        
        # Check for different table selectors
        print("Checking for table elements:")
        print(f"  table.form-guide-event__table: {len(race1.select('table.form-guide-event__table'))}")
        print(f"  table: {len(race1.select('table'))}")
        print(f"  .form-guide-event__table: {len(race1.select('.form-guide-event__table'))}")
        
        # Get ALL tr elements with form-guide-field-selection
        all_selections = race1.select('.form-guide-field-selection')
        print(f"\n  All .form-guide-field-selection: {len(all_selections)}")
        
        # Get table rows specifically
        table_rows = race1.select('tr.form-guide-field-selection')
        print(f"  tr.form-guide-field-selection: {len(table_rows)}")
        
        # Get links
        all_links = race1.select('a.form-guide-field-selection__link')
        print(f"  a.form-guide-field-selection__link: {len(all_links)}")
        
        print("\nShowing all selections:")
        for i, sel in enumerate(all_selections[:15], 1):  # First 15
            classes = ' '.join(sel.get('class', []))
            text = sel.get_text(strip=True)[:50]
            print(f"  {i}. [{classes[:40]}...] {text}")
