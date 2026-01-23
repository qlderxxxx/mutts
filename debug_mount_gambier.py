#!/usr/bin/env python3
"""
Debug script to check race boundary selection for Mount Gambier
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

url = "https://www.thegreyhoundrecorder.com.au/form-guides/mount-gambier/fields/250127/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    print(f"Loading {url}...")
    page.goto(url, timeout=60000, wait_until='networkidle')
    
    content = page.content()
    browser.close()
    
    soup = BeautifulSoup(content, 'lxml')
    
    # Find all race events
    race_events = soup.select('.form-guide-field-event')
    print(f"\nFound {len(race_events)} race events\n")
    
    # Look at Race 9 and Race 10
    for idx in [8, 9]:  # 0-indexed, so 8=R9, 9=R10
        if idx < len(race_events):
            race_event = race_events[idx]
            
            header = race_event.select_one('.form-guide-field-event__header')
            header_text = header.get_text(strip=True) if header else "No header"
            
            print(f"{'='*60}")
            print(f"Race Event {idx+1}: {header_text}")
            print(f"{'='*60}")
            
            # Check table
            table = race_event.select_one('table.form-guide-event__table')
            if table:
                print("Table found!")
                
                # Get all runner links
                links = table.select('a.form-guide-field-selection__link')
                print(f"Total links in table: {len(links)}\n")
                
                # Check each link's parent
                for i, link in enumerate(links, 1):
                    parent_tr = link.find_parent('tr', class_='form-guide-field-selection')
                    if parent_tr:
                        classes = parent_tr.get('class', [])
                        is_vacant = 'form-guide-field-selection--vacant' in classes
                        is_scratched = 'form-guide-field-selection--scratched' in classes
                        
                        dog_name = link.get_text(strip=True)
                        
                        status = []
                        if is_vacant:
                            status.append("VACANT")
                        if is_scratched:
                            status.append("SCRATCHED")
                        
                        status_str = f" [{', '.join(status)}]" if status else ""
                        print(f"  {i}. {dog_name}{status_str}")
            else:
                print("No table found!")
            
            print()
