#!/usr/bin/env python3
"""
Test script to scrape results from The Greyhound Recorder
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

# Test with Angle Park Race 3 from your screenshot
url = "https://www.thegreyhoundrecorder.com.au/results/angle-park/250176/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    print(f"Loading {url}...")
    page.goto(url, timeout=60000, wait_until='networkidle')
    
    # Wait a bit for content
    page.wait_for_timeout(3000)
    
    content = page.content()
    browser.close()
    
    soup = BeautifulSoup(content, 'lxml')
    
    # Find all race result sections
    # Look for elements that contain race data
    print("\nLooking for race results...")
    
    # Try different selectors
    print("\n1. Looking for race containers:")
    race_containers = soup.select('.race-result')
    print(f"   Found {len(race_containers)} .race-result elements")
    
    race_containers = soup.select('[class*="race"]')
    print(f"   Found {len(race_containers)} elements with 'race' in class")
    
    # Look for tables
    print("\n2. Looking for tables:")
    tables = soup.select('table')
    print(f"   Found {len(tables)} tables")
    
    if tables:
        for i, table in enumerate(tables[:3], 1):
            print(f"\n   Table {i} classes: {table.get('class', [])}")
            rows = table.select('tr')
            print(f"   Rows: {len(rows)}")
            if rows:
                print(f"   First row: {rows[0].get_text(strip=True)[:100]}")
    
    # Save HTML for inspection
    with open('c:/Users/mdoyle/Desktop/Mutts/results_page.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("\nSaved HTML to results_page.html for inspection")
