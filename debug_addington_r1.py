#!/usr/bin/env python3
"""
Show exactly what runners the scraper finds for Addington Race 1
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

url = "https://www.thegreyhoundrecorder.com.au/form-guides/addington/fields/250123/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    print(f"Loading {url}...")
    page.goto(url, timeout=60000, wait_until='domcontentloaded')
    
    # Wait for table
    page.wait_for_selector('table.form-guide-event__table', timeout=15000)
    page.wait_for_timeout(2000)
    
    content = page.content()
    browser.close()
    
    soup = BeautifulSoup(content, 'lxml')
    
    # Find Race 1
    race_events = soup.select('.form-guide-field-event')
    print(f"\nFound {len(race_events)} total races\n")
    
    if race_events:
        race1 = race_events[0]
        
        # Get header
        header = race1.select_one('.form-guide-field-event__header')
        print(f"Race Header: {header.get_text(strip=True) if header else 'N/A'}\n")
        
        # Find table
        table = race1.select_one('table.form-guide-event__table')
        if table:
            print("Table found!")
            
            # Get all links
            links = table.select('a.form-guide-field-selection__link')
            print(f"\nTotal links found in table: {len(links)}\n")
            
            # Get all tr elements
            all_trs = table.select('tr.form-guide-field-selection')
            print(f"Total TR elements: {len(all_trs)}\n")
            
            # Show each runner
            print("Runners found:")
            print("=" * 60)
            for i, link in enumerate(links, 1):
                parent_tr = link.find_parent('tr')
                classes = parent_tr.get('class', []) if parent_tr else []
                
                # Get rug number
                rug_img = parent_tr.select_one('img.form-guide-field-selection__rug') if parent_tr else None
                rug_text = rug_img.get('alt', '') if rug_img else ''
                
                print(f"{i}. {link.get_text(strip=True)}")
                print(f"   Rug: {rug_text}")
                print(f"   Classes: {classes}")
                print()
        else:
            print("No table found!")
