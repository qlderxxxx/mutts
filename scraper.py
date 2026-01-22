#!/usr/bin/env python3
"""
Greyhound Micro-Field Finder - Web Scraper
Scrapes race data from The Greyhound Recorder and stores in Supabase
"""

import os
import sys
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from supabase import create_client, Client

# AEST timezone (UTC+11 during daylight saving)
AEST = timezone(timedelta(hours=11))

# Configuration
FORM_GUIDE_URL = "https://www.thegreyhoundrecorder.com.au/form-guides/"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a web page using Playwright to bypass WAF"""
    try:
        with sync_playwright() as p:
            # Launch browser (headless)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set a real user agent
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            })
            
            print(f"Navigating to {url}...")
            page.goto(url, timeout=60000)
            
            # Wait for content to load (handling WAF challenge)
            try:
                # Wait for the main date header to appear (max 10s)
                page.wait_for_selector('h2.meeting-list__title', timeout=10000)
                print("Content loaded successfully")
            except Exception:
                print("Timeout waiting for selector, attempting to capture content anyway...")
            
            content = page.content()
            browser.close()
            
            return BeautifulSoup(content, 'lxml')
            
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def parse_race_date(date_str: str) -> Optional[datetime]:
    """Parse race date string into datetime object (just date, no time)"""
    try:
        # Parse date (e.g., "Wednesday, January 21")
        date_match = re.search(r'(\w+),\s+(\w+)\s+(\d+)', date_str)
        if not date_match:
            return None
        
        month_name = date_match.group(2)
        day = int(date_match.group(3))
        
        # Map month name to number
        months = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        month = months.get(month_name)
        if not month:
            return None
        
        # Use current year
        year = datetime.now().year
        
        # Return as simple date string YYYY-MM-DD
        return f"{year}-{month:02d}-{day:02d}"
        
    except Exception as e:
        print(f"Warning: Could not parse date '{date_str}'")
        return None


def count_active_runners(runner_elements) -> tuple[int, List[Dict]]:
    """
    Count active runners and extract their details
    Returns: (active_count, list of runner dicts)
    """
    active_runners = []
    
    for idx, runner_elem in enumerate(runner_elements, 1):
        try:
            # Get full text to check for status markers
            runner_text = runner_elem.get_text()
            
            # Check for vacant box (already filtered, but double-check)
            if 'VACANT BOX' in runner_text.upper():
                continue
            
            # Check if scratched
            is_scratched = False
            if 'SCR' in runner_text or 'SCRATCHED' in runner_text.upper():
                is_scratched = True
            
            # Check for reserves (typically box 9-10 or marked as RES)
            # Skip reserves unless they have a confirmed run
            if 'RES' in runner_text and not is_scratched:
                # If it's a reserve without odds, skip it
                continue
            
            # Extract dog name - CORRECTED SELECTOR
            dog_name_elem = runner_elem.select_one('.form-guide-field-selection__name')
            if not dog_name_elem:
                # Try alternative selector
                dog_name_elem = runner_elem.select_one('a.form-guide-field-selection__link')
            if not dog_name_elem:
                continue
            
            dog_name = dog_name_elem.get_text(strip=True)
            
            # Extract box number from rug image alt text
            box_number = idx
            rug_img = runner_elem.select_one('img.form-guide-field-selection__rug')
            if rug_img and rug_img.get('alt'):
                rug_match = re.search(r'Rug\s+(\d+)', rug_img.get('alt'))
                if rug_match:
                    box_number = int(rug_match.group(1))
            
            # Extract GHR odds from column 10 (Our $)
            ghr_odds = None
            odds_cells = runner_elem.select('td')
            if odds_cells and len(odds_cells) >= 10:
                ghr_cell = odds_cells[9]  # 10th column (0-indexed)
                ghr_text = ghr_cell.get_text(strip=True).replace('$', '').replace(',', '')
                try:
                    ghr_odds = float(ghr_text)
                except ValueError:
                    pass
            
            runner_data = {
                'dog_name': dog_name,
                'box_number': box_number,
                'ghr_odds': ghr_odds,
                'sportsbet_odds': None, # data not available in static HTML
                'is_scratched': is_scratched
            }
            
            active_runners.append(runner_data)
            
        except Exception as e:
            print(f"Error parsing runner: {e}")
            continue
    
    # Count only non-scratched runners
    active_count = sum(1 for r in active_runners if not r['is_scratched'])
    
    return active_count, active_runners


def scrape_meeting_fields(meeting_url: str, meeting_name: str) -> List[Dict]:
    """Scrape races from a specific meeting's fields page"""
    races = []
    
    soup = fetch_page(meeting_url)
    if not soup:
        return races
    
    # Parse date from page title (e.g., "Addington Race Fields - 22nd Jan 2026")
    title_elem = soup.select_one('title')
    race_date = None
    if title_elem:
        title_text = title_elem.get_text(strip=True)
        print(f"DEBUG: Title for {meeting_name}: '{title_text}'")
        # Extract date in DD/MM/YY format (e.g., "21/01/26")
        date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2})', title_text)
        if date_match:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            year_short = int(date_match.group(3))
            year = 2000 + year_short  # Convert 26 to 2026
            race_date = f"{year}-{month:02d}-{day:02d}"
            print(f"DEBUG: Parsed date for {meeting_name}: {race_date}")
    
    if not race_date:
        print(f"Could not parse date from page title for {meeting_name}")
        return races
    
    # Find all race events
    race_events = soup.select('.form-guide-field-event')
    
    if not race_events:
        print(f"No races found for {meeting_name}")
        return races
    
    # Remove the old parse_race_date call
    
    for race_event in race_events:
        try:
            # Extract race header info
            header_elem = race_event.select_one('.form-guide-field-event__header')
            if not header_elem:
                continue
            
            header_text = header_elem.get_text(strip=True)
            
            # Extract race number
            race_match = re.search(r'Race\s+(\d+)', header_text)
            if not race_match:
                continue
            
            race_number = int(race_match.group(1))
            
            # Find all runners
            runner_elements = race_event.select('tr.form-guide-field-selection')
            
            # Filter out vacant boxes
            active_runner_elements = [
                r for r in runner_elements 
                if 'form-guide-field-selection--vacant' not in r.get('class', [])
            ]
            
            active_count, runners = count_active_runners(active_runner_elements)
            
            race_data = {
                'meeting_name': meeting_name,
                'race_number': race_number,
                'race_time': race_date,  # Simple date string YYYY-MM-DD
                'status': 'upcoming',
                'active_runner_count': active_count,
                'runners': runners
            }
            
            races.append(race_data)
            print(f"Scraped: {meeting_name} R{race_number} - {active_count} active runners")
            
        except Exception as e:
            print(f"Error parsing race in {meeting_name}: {e}")
            continue
    
    return races


def scrape_form_guides() -> List[Dict]:
    """Scrape all races from the form guides page"""
    all_races = []
    
    soup = fetch_page(FORM_GUIDE_URL)
    if not soup:
        return all_races
    
    # Find date headers (h2.meeting-list__title)
    date_headers = soup.select('h2.meeting-list__title')
    print(f"DEBUG: Found {len(date_headers)} date headers")
    
    if not date_headers:
        # Debug: print first 500 chars of HTML to see what we got
        print("DEBUG: No date headers found! Page content preview:")
        print(soup.prettify()[:500])
    
    # Process first two dates (Today and Tomorrow)
    for date_idx, date_header in enumerate(date_headers[:2]):
        date_str = date_header.get_text(strip=True)
        day_label = "Today" if date_idx == 0 else "Tomorrow"
        
        print(f"\n--- Scraping {day_label} ({date_str}) ---")
        
        # Find all meeting links after this date header
        # Look for "Fields" buttons (a.meetings__row-btn)
        current_elem = date_header.find_next_sibling()
        
        while current_elem and current_elem.name != 'h2':
            # Find all "Fields" links in this section
            fields_links = current_elem.select('a.meetings__row-btn')
            
            for link in fields_links:
                if 'Fields' in link.get_text():
                    meeting_url = link.get('href')
                    if not meeting_url.startswith('http'):
                        meeting_url = 'https://www.thegreyhoundrecorder.com.au' + meeting_url
                    
                    # Extract meeting name from URL or nearby element
                    # URL format: /form-guides/[track-name]/fields/[date-id]/
                    url_parts = meeting_url.split('/')
                    track_slug = url_parts[-4] if len(url_parts) >= 4 else 'unknown'
                    meeting_name = track_slug.replace('-', ' ').title()
                    
                    print(f"\nFetching {meeting_name}...")
                    meeting_races = scrape_meeting_fields(meeting_url, meeting_name)
                    all_races.extend(meeting_races)
            
            current_elem = current_elem.find_next_sibling()
    
    return all_races


def upsert_race_data(race_data: Dict) -> None:
    """Upsert race and runner data to Supabase"""
    try:
        # Prepare race data (without runners)
        race_record = {
            'meeting_name': race_data['meeting_name'],
            'race_number': race_data['race_number'],
            'race_time': race_data['race_time'],
            'status': race_data['status'],
            'active_runner_count': race_data['active_runner_count']
        }
        
        # Upsert race (conflict on meeting_name + race_number + date)
        # This allows same meeting/race on different dates but prevents duplicates on same date
        race_datetime = datetime.fromisoformat(race_data['race_time'])
        race_date_start = race_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        race_date_end = race_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Delete existing race with same meeting, race number, and date
        supabase.table('races').delete().match({
            'meeting_name': race_data['meeting_name'],
            'race_number': race_data['race_number']
        }).gte('race_time', race_date_start.isoformat()).lte('race_time', race_date_end.isoformat()).execute()
        
        # Insert the race
        result = supabase.table('races').insert(race_record).execute()
        
        if not result.data:
            print(f"Error upserting race: {race_data['meeting_name']} R{race_data['race_number']}")
            return
        
        race_id = result.data[0]['id']
        
        # Delete existing runners for this race (to handle scratchings)
        supabase.table('runners').delete().eq('race_id', race_id).execute()
        
        # Insert runners
        for runner in race_data['runners']:
            runner_record = {
                'race_id': race_id,
                'dog_name': runner['dog_name'],
                'box_number': runner['box_number'],
                'ghr_odds': runner['ghr_odds'],
                'sportsbet_odds': runner['sportsbet_odds'],
                'is_scratched': runner['is_scratched']
            }
            
            supabase.table('runners').insert(runner_record).execute()
        
        print(f"Upserted: {race_data['meeting_name']} R{race_data['race_number']}")
        
    except Exception as e:
        print(f"Error upserting race data: {e}")


def main():
    """Main scraper function"""
    print("=" * 60)
    print("Greyhound Micro-Field Finder - Scraper")
    print(f"Started at: {datetime.now(AEST).strftime('%Y-%m-%d %I:%M:%S %p AEST')}")
    print("=" * 60)
    
    # Scrape all races
    all_races = scrape_form_guides()
    
    print(f"\n--- Upserting {len(all_races)} races to Supabase ---")
    
    # Upsert to Supabase
    for race in all_races:
        upsert_race_data(race)
    
    # Summary
    micro_fields = [r for r in all_races if r['active_runner_count'] in [4, 5]]
    print("\n" + "=" * 60)
    print(f"Scraping complete!")
    print(f"Total races: {len(all_races)}")
    print(f"Micro-fields (4-5 runners): {len(micro_fields)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
