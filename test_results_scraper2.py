#!/usr/bin/env python3
"""
Better test script to examine results table structure
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://www.thegreyhoundrecorder.com.au/results/angle-park/250176/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print(f"Loading {url}...")
    page.goto(url, timeout=60000, wait_until='networkidle')
    page.wait_for_timeout(3000)
    
    content = page.content()
    browser.close()
    
    soup = BeautifulSoup(content, 'lxml')
    
    # Find the table
    table = soup.select_one('table.results-event__table')
    
    if table:
        print("\nFound results table!")
        
        # Get all rows
        rows = table.select('tr')
        print(f"\nTotal rows: {len(rows)}")
        
        # Print first few rows to understand structure
        for i, row in enumerate(rows[:10], 1):
            cells = row.select('td, th')
            print(f"\nRow {i}: {len(cells)} cells")
            for j, cell in enumerate(cells, 1):
                text = cell.get_text(strip=True)
                classes = cell.get('class', [])
                print(f"  Cell {j}: '{text}' (classes: {classes})")
    else:
        print("\nNo table found!")
