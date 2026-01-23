#!/usr/bin/env python3
"""
Debug script to see actual runner data being extracted
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from typing import List, Dict

def fetch_page(url: str):
    """Fetch and parse a web page using Playwright"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            page.wait_for_selector('body', timeout=5000)
            content = page.content()
            browser.close()
            return BeautifulSoup(content, 'lxml')
    except Exception as e:
        print(f"Error: {e}")
        return None

def count_active_runners(runner_elements) -> tuple[int, List[Dict]]:
    """Count active runners and extract their details"""
    active_runners = []
    
    for idx, runner_elem in enumerate(runner_elements, 1):
        try:
            runner_text = runner_elem.get_text()
            runner_text_upper = runner_text.upper()
            
            if 'VACANT BOX' in runner_text_upper:
                continue
            
            is_scratched = False
            if re.search(r'\bSCR\b', runner_text_upper) or 'SCRATCHED' in runner_text_upper:
                is_scratched = True
            
            dog_name_elem = runner_elem.select_one('.form-guide-field-selection__name')
            if not dog_name_elem:
                dog_name_elem = runner_elem.select_one('a.form-guide-field-selection__link')
            if not dog_name_elem:
                continue
            
            dog_name = dog_name_elem.get_text(strip=True)
            
            box_number = idx
            rug_img = runner_elem.select_one('img.form-guide-field-selection__rug')
            if rug_img and rug_img.get('alt'):
                rug_match = re.search(r'Rug\s+(\d+)', rug_img.get('alt'))
                if rug_match:
                    box_number = int(rug_match.group(1))
            
            runner_data = {
                'dog_name': dog_name,
                'box_number': box_number,
                'is_scratched': is_scratched
            }
            
            active_runners.append(runner_data)
            
        except Exception as e:
            print(f"Error parsing runner: {e}")
            continue
    
    active_count = sum(1 for r in active_runners if not r['is_scratched'])
    return active_count, active_runners

# Test Cambridge specifically
url = "https://www.thegreyhoundrecorder.com.au/form-guides/cambridge/fields/250123/"
print(f"Fetching Cambridge races...")
soup = fetch_page(url)

if soup:
    race_events = soup.select('.form-guide-field-event')
    print(f"Found {len(race_events)} races\n")
    
    for race_event in race_events[:5]:  # First 5 races
        header_elem = race_event.select_one('.form-guide-field-event__header')
        if not header_elem:
            continue
        
        header_text = header_elem.get_text(strip=True)
        race_match = re.search(r'Race\s+(\d+)', header_text)
        if not race_match:
            continue
        
        race_number = int(race_match.group(1))
        
        # Use NEW method (links)
        runner_links = race_event.select('a.form-guide-field-selection__link')
        runner_elements = []
        for link in runner_links:
            parent_tr = link.find_parent('tr', class_='form-guide-field-selection')
            if parent_tr and parent_tr not in runner_elements:
                runner_elements.append(parent_tr)
        
        active_count, runners = count_active_runners(runner_elements)
        
        print(f"Race {race_number}:")
        print(f"  Total elements: {len(runner_elements)}")
        print(f"  Active count: {active_count}")
        print(f"  Runners:")
        for r in runners:
            status = "SCRATCHED" if r['is_scratched'] else "ACTIVE"
            print(f"    Box {r['box_number']}: {r['dog_name']} [{status}]")
        print()
