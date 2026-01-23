#!/usr/bin/env python3
"""
Test script to verify runner counting logic
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

FORM_GUIDE_URL = "https://www.thegreyhoundrecorder.com.au/form-guides/"

def fetch_page(url: str):
    """Fetch and parse a web page using Playwright"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-size=1920,1080',
                    '--start-maximized'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-AU',
                timezone_id='Australia/Sydney',
                has_touch=False,
                is_mobile=False,
                permissions=['geolocation'],
                geolocation={'latitude': -33.8688, 'longitude': 151.2093},
            )
            
            page = context.new_page()
            
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-AU', 'en-US', 'en']})",
                "Object.defineProperty(navigator, 'connection', {get: () => ({rtt: 50, download: 10})})",
                "window.chrome = { runtime: {} }",
                """
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Open Source Technology Center';
                    if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 620 (Kaby Lake GT2)';
                    return getParameter(parameter);
                };
                """
            ]
            
            for script in stealth_scripts:
                page.add_init_script(script)
            
            print(f"Navigating to {url}...")
            
            try:
                if 'form-guides' in url:
                    page.goto("https://www.thegreyhoundrecorder.com.au", timeout=45000, wait_until='domcontentloaded')
                    page.wait_for_timeout(3000)
                
                page.goto(url, timeout=60000, wait_until='domcontentloaded')
                
                try:
                    page.wait_for_selector('.form-guide-field-event__header', timeout=5000)
                except:
                    page.wait_for_selector('body', timeout=5000)
                
                print("Content loaded!")
                
            except Exception as e:
                print(f"Navigation error: {e}")
            
            content = page.content()
            browser.close()
            
            return BeautifulSoup(content, 'lxml')
            
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def test_runner_counting():
    """Test the runner counting logic"""
    print("=" * 60)
    print("Testing Runner Count Logic")
    print("=" * 60)
    
    # Fetch form guides page
    soup = fetch_page(FORM_GUIDE_URL)
    if not soup:
        print("Failed to fetch page")
        return
    
    # Find first meeting with Fields link
    date_headers = soup.select('h2.meeting-list__title')
    print(f"\nFound {len(date_headers)} date headers")
    
    if not date_headers:
        print("No date headers found!")
        return
    
    # Process first date
    date_header = date_headers[0]
    current_elem = date_header.find_next_sibling()
    
    meeting_urls = []
    while current_elem and current_elem.name != 'h2' and len(meeting_urls) < 2:
        fields_links = current_elem.select('a.meetings__row-btn')
        
        for link in fields_links:
            if 'Fields' in link.get_text():
                meeting_url = link.get('href')
                if not meeting_url.startswith('http'):
                    meeting_url = 'https://www.thegreyhoundrecorder.com.au' + meeting_url
                
                url_parts = meeting_url.split('/')
                track_slug = url_parts[-4] if len(url_parts) >= 4 else 'unknown'
                meeting_name = track_slug.replace('-', ' ').title()
                
                meeting_urls.append((meeting_name, meeting_url))
                break
        
        current_elem = current_elem.find_next_sibling()
    
    # Test first 2 meetings
    for meeting_name, meeting_url in meeting_urls:
        print(f"\n{'=' * 60}")
        print(f"Testing: {meeting_name}")
        print(f"{'=' * 60}")
        
        soup = fetch_page(meeting_url)
        if not soup:
            continue
        
        race_events = soup.select('.form-guide-field-event')
        print(f"Found {len(race_events)} races")
        
        for race_event in race_events[:3]:  # Test first 3 races
            header_elem = race_event.select_one('.form-guide-field-event__header')
            if not header_elem:
                continue
            
            header_text = header_elem.get_text(strip=True)
            race_match = re.search(r'Race\s+(\d+)', header_text)
            if not race_match:
                continue
            
            race_number = int(race_match.group(1))
            
            # OLD METHOD: Count table rows
            old_runner_elements = race_event.select('tr.form-guide-field-selection')
            old_active = [r for r in old_runner_elements if 'form-guide-field-selection--vacant' not in r.get('class', [])]
            old_count = len(old_active)
            
            # NEW METHOD: Count links from TABLE ONLY (avoid mobile view duplication)
            table = race_event.select_one('table.form-guide-event__table')
            if table:
                runner_links = table.select('a.form-guide-field-selection__link')
                new_count = len(runner_links)
            else:
                new_count = 0
            
            print(f"\n  Race {race_number}:")
            print(f"    OLD method (all table rows): {old_count} runners")
            print(f"    NEW method (table links only): {new_count} runners")
            
            if old_count != new_count:
                print(f"    WARNING: DIFFERENCE DETECTED!")
            else:
                print(f"    OK: Counts match")


if __name__ == "__main__":
    test_runner_counting()
