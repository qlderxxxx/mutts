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

# Initialize Supabase client
# Fallback for dev/local scripts if env vars missing
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL:
    # Try to find from hardcoded (for local agent execution match)
    pass 

supabase: Optional[Client] = None

def get_supabase():
    global supabase
    if supabase:
        return supabase
        
    url = os.environ.get("SUPABASE_URL", 'https://yvnkyakuamvahtiwbneq.supabase.co')
    key = os.environ.get("SUPABASE_KEY", 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2bmt5YWt1YW12YWh0aXdibmVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5Mzg4MTQsImV4cCI6MjA4NDUxNDgxNH0.-v9LyyRgX2tj9EFCImHo44XxSQcZ4_GmQZw-q7ZTX5I')
    
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        sys.exit(1)
        
    supabase = create_client(url, key)
    return supabase

# Initialize on module load ONLY if we are running as main, 
# OR just let it be lazy? 
# Existing code expects `supabase` variable to exist.
# We will initialize it immediately but with fallback if missing, 
# OR we update usage sites. 
# Updating usage sites is safer.
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None



def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a web page using Playwright to bypass WAF"""
    try:
        with sync_playwright() as p:
            # Launch browser in HEADED mode (requires Xvfb on server)
            # This is significantly harder to detect than headless
            browser = p.chromium.launch(
                headless=False,  # <--- KEY CHANGE: Run "visible"
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-size=1920,1080',
                    '--start-maximized' # Ensure full screen for realism
                ]
            )
            
            # Create context with realistic attributes
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-AU',
                timezone_id='Australia/Sydney',
                has_touch=False,
                is_mobile=False,
                permissions=['geolocation'],
                geolocation={'latitude': -33.8688, 'longitude': 151.2093}, # Sydney
            )
            
            page = context.new_page()
            
            # ADVANCED STEALTH INJECTIONS to mask automation
            stealth_scripts = [
                # Mask webdriver
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                # Mock plugins (Headless usually has 0)
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                # Mock languages
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-AU', 'en-US', 'en']})",
                # Mock connection
                "Object.defineProperty(navigator, 'connection', {get: () => ({rtt: 50, download: 10})})",
                # Pass chrome check
                "window.chrome = { runtime: {} }",
                # Mock WebGL vendor (often reveals 'Google Inc.')
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
            
            print(f"Navigating to {url} (Headed Mode)...")
            
            try:
                # 1. Visit homepage first
                if 'form-guides' in url:
                    page.goto("https://www.thegreyhoundrecorder.com.au", timeout=45000, wait_until='domcontentloaded')
                    page.wait_for_timeout(3000) # Human pause
                
                # 2. Go to target
                page.goto(url, timeout=60000, wait_until='domcontentloaded')
                
                # 3. Wait for content to load - CRITICAL: Wait for the actual table with runner data
                # The page uses JavaScript to populate the tables, so we need to wait for them
                try:
                    # Wait for the table element that contains runner data
                    page.wait_for_selector('table.form-guide-event__table', timeout=15000)
                    # Give extra time for all JavaScript to finish rendering
                    page.wait_for_timeout(2000)
                except:
                    # Fallback to just wait for body if specific element missing
                    page.wait_for_selector('body', timeout=5000)
                
                print("Content loaded successfully!")
                
            except Exception as e:
                print(f"Navigation/Selector error: {e}")
                print("Capturing content state anyway...")
            
            content = page.content()
            
            # Debug: Screenshot if it fails (stored in memory/logs if we could)
            # page.screenshot(path="debug_screenshot.png")
            
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
            runner_text_upper = runner_text.upper()
            
            # Check for vacant box (already filtered, but double-check)
            if 'VACANT BOX' in runner_text_upper:
                continue
            
            # Check if scratched - Use multiple methods
            # 1. Check CSS class (most reliable)
            # 2. Check for SCR as a whole word in text
            # 3. Check for SCRATCHED in text
            is_scratched = False
            scratch_reason = None
            runner_classes = runner_elem.get('class', [])
            if 'form-guide-field-selection--scratched' in runner_classes:
                is_scratched = True
                scratch_reason = "CSS class"
            elif re.search(r'\bSCR\b', runner_text_upper):
                is_scratched = True
                scratch_reason = "SCR in text"
            elif 'SCRATCHED' in runner_text_upper:
                is_scratched = True
                scratch_reason = "SCRATCHED in text"
            
            # Check for reserves (typically box 9-10 or marked as RES)
            # Skip reserves unless they have a confirmed run
            # Use Regex for RES as whole word
            if re.search(r'\bRES\b', runner_text_upper) and not is_scratched:
                # If it's a reserve without odds, skip it
                # Logic: If it has odds, it might be running? 
                # For now, let's just mark it as not active if we aren't sure, 
                # but usually RES dogs don't run unless scratched.
                # If we skip here, they aren't in the list at all.
                pass 
            
            # Extract dog name - CORRECTED SELECTOR
            dog_name_elem = runner_elem.select_one('.form-guide-field-selection__name')
            if not dog_name_elem:
                # Try alternative selector
                dog_name_elem = runner_elem.select_one('a.form-guide-field-selection__link')
            if not dog_name_elem:
                print(f"Skipping runner idx {idx}: No name element found. Text: {runner_text[:50]}...")
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
            
            # Extract Sportsbet fixed odds
            sportsbet_odds = None
            sb_el = runner_elem.select_one('[class*="best-odds--sportsbet"]')
            if sb_el:
                sb_text = sb_el.get_text(strip=True).replace('$', '').strip()
                try:
                    sportsbet_odds = float(sb_text)
                    print(f"    -> SB Odds for box {box_number}: ${sportsbet_odds}")
                except ValueError:
                    pass

            runner_data = {
                'dog_name': dog_name,
                'box_number': box_number,
                'ghr_odds': ghr_odds,
                'sportsbet_odds': sportsbet_odds,
                'is_scratched': is_scratched,
                'scratch_reason': scratch_reason if is_scratched else None
            }
            
            active_runners.append(runner_data)
            
        except Exception as e:
            print(f"Error parsing runner: {e}")
            continue
    
    # Count only non-scratched runners
    active_count = sum(1 for r in active_runners if not r['is_scratched'])
    
    # DEBUG: Print runner details for verification
    if len(active_runners) > 0:
        print(f"  DEBUG: Total runners found: {len(active_runners)}, Active (non-scratched): {active_count}")
        if active_count != len(active_runners):
            print(f"  Scratched runners detected:")
            for r in active_runners:
                if r['is_scratched']:
                    print(f"    - Box {r['box_number']}: {r['dog_name']} (Reason: {r.get('scratch_reason', 'unknown')})")
    
    return active_count, active_runners


def scrape_meeting_results(meeting_url: str, meeting_name: str) -> List[Dict]:
    """
    Scrape race results from a specific meeting's results page.
    Clicks through all race navigation buttons to get results for all races.
    Skips meetings where all Starting Prices are $0.
    """
    results = []
    
    # Convert fields URL to results URL
    # e.g., /form-guides/angle-park/fields/250176/ -> /results/angle-park/250176/
    results_url = meeting_url.replace('/form-guides/', '/results/').replace('/fields/', '/')
    
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            print(f"Navigating to {results_url}...", flush=True)
            page.goto(results_url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            # Find all race navigation items
            # Based on inspection, they are divs with class 'meeting-events-nav__item' inside 'nav.meeting-events-nav'
            race_nav_items = page.query_selector_all('.meeting-events-nav__item')
            
            # Filter to ensure they act like buttons (have numbers)
            race_buttons = [item for item in race_nav_items if item.text_content() and item.text_content().strip().isdigit()]
            
            num_races = len(race_buttons)
            print(f"Found {num_races} race buttons for {meeting_name}")
            
            if num_races == 0:
                # Fallback: try finding any numbered elements in a nav
                race_buttons = page.query_selector_all('nav div, nav button, nav a')
                race_buttons = [btn for btn in race_buttons if btn.text_content() and btn.text_content().strip().isdigit() and int(btn.text_content().strip()) <= 15]
                num_races = len(race_buttons)
                print(f"Fallback found {num_races} race buttons")
            
            if num_races == 0:
                # No race buttons, just scrape current page
                html = page.content()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                table = soup.select_one('table.results-event__table')
                
                if table:
                    race_data = parse_result_table(table, meeting_name, 1)
                    if race_data:
                        results.append(race_data)
                
                browser.close()
                return results
            
            # Click through each race button
            for i in range(num_races):
                try:
                    # Re-query buttons (DOM might update)
                    race_nav_items = page.query_selector_all('.meeting-events-nav__item')
                    current_race_buttons = [item for item in race_nav_items if item.text_content() and item.text_content().strip().isdigit()]
                    
                    if not current_race_buttons:
                         # Fallback re-query
                         race_nav_items = page.query_selector_all('nav div, nav button, nav a')
                         current_race_buttons = [btn for btn in race_nav_items if btn.text_content() and btn.text_content().strip().isdigit() and int(btn.text_content().strip()) <= 15]
                    
                    if i < len(current_race_buttons):
                        button = current_race_buttons[i]
                        race_num = button.text_content().strip()
                        print(f"  Clicking race {race_num}...", flush=True)
                        
                        # Check if clickable (might be disabled if active)
                        # We can try to click, if it fails, we assume it's active and page is already showing it?
                        # No, if we iterate 1..12, we need to click 1, then 2, etc.
                        # If 1 is active, clicking might do nothing.
                        # But we need to ensure we are ON race 1.
                        
                        try:
                            # Force click or just click
                            button.click(timeout=2000)
                            # Increase wait time to ensure table loads
                            page.wait_for_timeout(3000)
                        except Exception as click_err:
                            # If click fails (e.g. pointer-events: none), it might be the active one
                            print(f"    Click validation: {click_err} (might be active race)")
                            pass
                        
                        # Get updated content
                        html = page.content()
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        table = soup.select_one('table.results-event__table')
                        if table:
                            race_data = parse_result_table(table, meeting_name, int(race_num))
                            if race_data:
                                results.append(race_data)
                                print(f"    -> Scraped {len(race_data['results'])} runners")
                            else:
                                print(f"    -> Parsed no data for R{race_num}")
                        else:
                            print(f"    -> Warning: No results table found for R{race_num}")
                
                except Exception as e:
                    print(f"  Error scraping race {i+1}: {e}")
                    continue
            
            browser.close()
            
        except Exception as e:
            print(f"Error with Playwright for {meeting_name}: {e}")
            if 'browser' in locals():
                browser.close()
    
    return results


def parse_result_table(table, meeting_name: str, race_number: int) -> Dict:
    """Parse a single result table and return race data"""
    try:
        rows = table.select('tr')[1:]  # Skip header
        
        race_results = []
        for row in rows:
            cells = row.select('td')
            if len(cells) < 12:
                continue
            
            # Extract data
            place_text = cells[0].get_text(strip=True)
            name_with_box = cells[2].get_text(strip=True)
            sp_text = cells[11].get_text(strip=True)
            
            # Parse place
            try:
                place = int(place_text)
            except:
                continue
            
            # Extract box number
            box_match = re.search(r'\((\d+)\)', name_with_box)
            if not box_match:
                continue
            box_number = int(box_match.group(1))
            
            # Extract dog name
            dog_name = re.sub(r'\(\d+\)', '', name_with_box).strip()
            
            # Parse SP
            sp_value = None
            sp_match = re.search(r'\$?([\d.]+)', sp_text)
            if sp_match:
                try:
                    sp_value = float(sp_match.group(1))
                except:
                    pass
            
            race_results.append({
                'race_number': race_number,
                'dog_name': dog_name,
                'box_number': box_number,
                'finishing_position': place,
                'starting_price': sp_value
            })
        
        if race_results:
            return {
                'meeting_name': meeting_name,
                'race_number': race_number,
                'results': race_results
            }
    
    except Exception as e:
        print(f"Error parsing table for {meeting_name} R{race_number}: {e}")
    
    return None


def all_sps_zero(race_data: Dict) -> bool:
    """Check if all starting prices in a race are $0 or None"""
    if not race_data or 'results' not in race_data:
        return True
    
    for runner in race_data['results']:
        sp = runner.get('starting_price')
        if sp and sp > 0:
            return False  # Found at least one non-zero SP
    
    return True  # All SPs are 0 or None


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
            
            header_text = header_elem.get_text(separator=' ', strip=True) # Use separator to avoid mashing
            
            # Extract race number
            race_match = re.search(r'Race\s+(\d+)', header_text)
            if not race_match:
                continue
            
            race_number = int(race_match.group(1))

            # Extract Race Time (e.g. 8:45PM)
            # Text might be "Race 1... 8:45PM (AEST)"
            # User confirms site times are "accurate to my timezone" (Sydney AEDT)
            # So we treat the digits as Sydney Local Time (+11:00 in Summer, +10:00 Winter)
            # Currently Jan = Summer = +11:00
            full_race_time_iso = race_date # Default fallback
            
            # Robust Regex: Match time with optional space before AM/PM
            time_match = re.search(r'(\d{1,2}:\d{2})\s?(:?AM|PM)', header_text, re.IGNORECASE)
            
            if time_match:
                time_str = time_match.group(1)
                meridiem = time_match.group(2).upper()
                
                # Parse hour/minute
                dt = datetime.strptime(f"{time_str} {meridiem}", "%I:%M %p")
                
                # Combine with date
                year, month, day = map(int, race_date.split('-'))
                full_dt = dt.replace(year=year, month=month, day=day)
                
                # Handle 12-hour wrap around (If race is early AM next day?)
                # Unlikely for greyhounds (usually PM), but if we parse 12:15 AM
                # and the race date was the previous day... logic gets complex.
                # Assuming race_date from Title applies to the whole meeting.
                
                # FORCE Timezone to Sydney (AEDT +11:00)
                # Regardless of what the text says (AEST/AEDT)
                tz_offset = timezone(timedelta(hours=11)) 
                
                full_dt = full_dt.replace(tzinfo=tz_offset)
                full_race_time_iso = full_dt.isoformat()
                
                print(f"  DEBUG: Parsed time {time_str} {meridiem} -> {full_race_time_iso} (Forced AEDT)")
            else:
                 print(f"  WARNING: No time found in header: '{header_text}'")

            # Extract distance (Safe Regex: 200m - 999m)
            # Try multiple sources (header matching often fails for upcoming events)
            full_text = race_event.get_text(separator=' ', strip=True)
            
            distance_meters = None
            dist_match = re.search(r'\b([2-9]\d{2})m\b', full_text)
            if dist_match:
                distance_meters = int(dist_match.group(1))
            
            # Find all runners by looking for links in the DESKTOP TABLE ONLY
            # (The page has both mobile and desktop views, we need to avoid double-counting)
            # Look specifically within the table element
            table = race_event.select_one('table.form-guide-event__table')
            if not table:
                print(f"Warning: No table found for {meeting_name} R{race_number}")
                continue
            
            runner_links = table.select('a.form-guide-field-selection__link')
            print(f"  DEBUG: Found {len(runner_links)} runner links in table for R{race_number}")
            
            # Get the parent tr elements for each link, excluding vacant boxes
            runner_elements = []
            for link in runner_links:
                parent_tr = link.find_parent('tr', class_='form-guide-field-selection')
                if parent_tr and parent_tr not in runner_elements:
                    # CRITICAL: Ensure this tr is actually within the current race_event
                    # to prevent cross-race contamination
                    if parent_tr.find_parent(class_='form-guide-field-event') == race_event:
                        # CRITICAL: Filter out vacant boxes by CSS class
                        tr_classes = parent_tr.get('class', [])
                        if 'form-guide-field-selection--vacant' not in tr_classes:
                            runner_elements.append(parent_tr)
            
            print(f"  DEBUG: After filtering vacant boxes: {len(runner_elements)} runner elements")
            
            active_count, runners = count_active_runners(runner_elements)
            
            race_data = {
                'meeting_name': meeting_name,
                'meeting_url': meeting_url,  # Store URL for later results scraping
                'race_number': race_number,
                'race_time': full_race_time_iso,  # Use parsed time with timezone
                'distance_meters': distance_meters,
                'status': 'upcoming',
                'active_runner_count': active_count,
                'runners': runners
            }
            
            races.append(race_data)
            print(f"Scraped: {meeting_name} R{race_number} ({distance_meters}m) - {active_count} active runners")
            
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
            'meeting_url': race_data['meeting_url'],
            'race_number': race_data['race_number'],
            'race_time': race_data['race_time'],
            'distance_meters': race_data.get('distance_meters'),
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


def update_race_results(race_results: Dict):
    """Update race with results data (SP, finishing positions, top_2_in_top_2)"""
    try:
        meeting_name = race_results['meeting_name']
        race_number = race_results['race_number']
        results = race_results['results']
        
        # Find the race in database
        # There might be multiple races with same meeting_name/number (different dates)
        race_response = supabase.table('races').select('id').eq('meeting_name', meeting_name).eq('race_number', race_number).order('race_time', desc=True).execute()
        
        if not race_response.data:
            print(f"Race not found in DB: {meeting_name} R{race_number}")
            return
            
        candidates = race_response.data
        race_id = None
        
        # If only one, use it
        if len(candidates) == 1:
            race_id = candidates[0]['id']
        else:
            # Multiple candidates (e.g. today's Taree R1 vs last week's Taree R1)
            # Find the one that actually contains our runners
            # We check the first valid runner from our results against the candidate race
            test_runner = next((r for r in results if r['dog_name']), None)
            
            if test_runner:
                for cand in candidates:
                    cid = cand['id']
                    # Check if test dog exists in this race
                    check = supabase.table('runners').select('id').eq('race_id', cid).ilike('dog_name', test_runner['dog_name']).execute()
                    if check.data:
                        race_id = cid
                        # print(f"    Matched race ID {race_id} for {meeting_name} R{race_number} using dog {test_runner['dog_name']}", flush=True)
                        break
            
            # Fallback: if no match found (maybe all scratched?), just use the most recent one (index 0 due to sort)
            if not race_id:
                race_id = candidates[0]['id']
                print(f"    Warning: Could not confirm race ID via runner match. Defaulting to most recent: {race_id}", flush=True)
        
        # Update each runner with SP and finishing position
        # Update each runner with SP and finishing position
        for result in results:
            # Find runner by race_id, dog_name, and box_number
            # Use ilike for case-insensitive matching (Results often UPPERCASE, Fields often Title Case)
            runner_response = supabase.table('runners').select('id').eq('race_id', race_id).ilike('dog_name', result['dog_name']).eq('box_number', result['box_number']).execute()
            
            if runner_response.data:
                runner_id = runner_response.data[0]['id']
                # print(f"    Updating runner {result['dog_name']}...", flush=True)
                supabase.table('runners').update({
                    'starting_price': result['starting_price'],
                    'finishing_position': result['finishing_position']
                }).eq('id', runner_id).execute()
            else:
                print(f"    Runner match failed: {result['dog_name']} (Box {result['box_number']}) on race {race_id}", flush=True)
        
        # Calculate "Top 2 in Top 2?"
        # Get top 2 by SP (lowest odds) - MUST be strictly positive (exclude $0.00 SPs)
        sorted_by_sp = sorted([r for r in results if r['starting_price'] is not None and r['starting_price'] > 0], key=lambda x: x['starting_price'])
        if len(sorted_by_sp) >= 2:
            top_2_favorites = {sorted_by_sp[0]['box_number'], sorted_by_sp[1]['box_number']}
            
            # Get top 2 finishers
            sorted_by_position = sorted(results, key=lambda x: x['finishing_position'])
            if len(sorted_by_position) >= 2:
                top_2_finishers = {sorted_by_position[0]['box_number'], sorted_by_position[1]['box_number']}
                
                # Check if they match
                top_2_in_top_2 = top_2_favorites == top_2_finishers
                
                # Update race with Top 2 in Top 2 and status
                supabase.table('races').update({
                    'top_2_in_top_2': top_2_in_top_2,
                    'status': 'resulted'
                }).eq('id', race_id).execute()
                
                print(f"Updated results: {meeting_name} R{race_number} - Top 2 in Top 2: {top_2_in_top_2}")
        else:
            # Handle case where we have results but valid SPs are missing (e.g. all $0)
            # We still mark as resulted so it doesn't stay 'upcoming', but top_2_in_top_2 remains null
            # This ensures it doesn't skew stats but shows we attempted to result it
            supabase.table('races').update({
                'status': 'resulted'
            }).eq('id', race_id).execute()
            print(f"Updated results: {meeting_name} R{race_number} - Resulted but invalid SP comparison (skipped Top 2 calc)")
        
    except Exception as e:
        print(f"Error updating race results: {e}")


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
    
    # Scrape results for historical races (today and yesterday)
    print(f"\n--- Scraping historical results ---")
    
    # Calculate today and yesterday's dates
    today = datetime.now(AEST)
    yesterday = today - timedelta(days=1)
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"Fetching races from {yesterday_str} and {today_str} to scrape results...")
    
    # Fetch races from today and yesterday from database
    try:
        response = supabase.table('races').select('meeting_name, meeting_url, race_time').gte('race_time', yesterday_str).lte('race_time', today_str).execute()
        races_to_check = response.data
        
        print(f"Found {len(races_to_check)} races from today and yesterday")
        
        # Group by meeting_url to avoid duplicate scrapes
        meetings_to_scrape = {}
        for race in races_to_check:
            meeting_url = race.get('meeting_url')
            meeting_name = race['meeting_name']
            
            # Skip if no meeting_url (shouldn't happen, but be safe)
            if not meeting_url:
                print(f"Warning: No meeting_url for {meeting_name}, skipping results scrape")
                continue
            
            if meeting_url not in meetings_to_scrape:
                meetings_to_scrape[meeting_url] = meeting_name
        
        # Scrape results for each meeting
        all_results = []
        for meeting_url, meeting_name in meetings_to_scrape.items():
            print(f"Scraping results for {meeting_name}...")
            results = scrape_meeting_results(meeting_url, meeting_name)
            all_results.extend(results)
        
        # Update database with results
        print(f"\n--- Updating {len(all_results)} races with results ---")
        for race_result in all_results:
            update_race_results(race_result)
            
    except Exception as e:
        print(f"Error fetching/updating historical results: {e}")
        all_results = []
    
    
    # Summary
    micro_fields = [r for r in all_races if r['active_runner_count'] in [4, 5]]
    print("\n" + "=" * 60)
    print(f"Scraping complete!")
    print(f"Total races: {len(all_races)}")
    print(f"Micro-fields (4-5 runners): {len(micro_fields)}")
    print(f"Results updated: {len(all_results)} races")
    print("=" * 60)


if __name__ == "__main__":
    main()
