"""
Backfill script to scrape historical race data (Fields + Results) 
starting from Jan 1st, 2026 to Present.

Strategy:
1. Iterate dates (YYYY-MM-DD)
2. Visit https://www.thegreyhoundrecorder.com.au/results/search/YYYY-MM-DD/
3. Extract meeting links -> Get Meeting ID and Name.
4. Construct Form Guide URL: /form-guides/[slug]/fields/[id]/
5. Scrape Fields (Runners/Boxes) -> Insert into DB.
6. Scrape Results -> Update DB.
"""

import os
import sys
import re
from datetime import datetime, timedelta
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from supabase import create_client, Client

# Import existing scrapers 
# (Assuming they are in the same directory)
from scraper import scrape_meeting_fields
from new_results_scraper import scrape_meeting_results_new

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", 'https://yvnkyakuamvahtiwbneq.supabase.co')
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2bmt5YWt1YW12YWh0aXdibmVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5Mzg4MTQsImV4cCI6MjA4NDUxNDgxNH0.-v9LyyRgX2tj9EFCImHo44XxSQcZ4_GmQZw-q7ZTX5I')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase creds missing")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

START_DATE = datetime(2026, 1, 1) # Jan 1st 2026
END_DATE = datetime.now()

def get_meetings_for_date(date_obj):
    """
    Scrape the search results page to find meetings for a specific date.
    URL: https://www.thegreyhoundrecorder.com.au/results/search/YYYY-MM-DD/
    """
    date_str = date_obj.strftime('%Y-%m-%d')
    url = f"https://www.thegreyhoundrecorder.com.au/results/search/{date_str}/"
    
    print(f"\nSearching meetings for {date_str}...")
    
    meetings = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=30000)
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # The search results list meetings.
            # Look for links like /results/[slug]/[id]/
            # Structure matches the "Meeting List" rows usually.
            
            # Selector might need adjustment based on page structure.
            # Based on inspection of similar pages:
            # Usually in a table or list. Let's look for known patterns.
            # Links containing '/results/' and an ID.
            
            links = soup.select('a[href*="/results/"]')
            
            seen_ids = set()
            
            for link in links:
                href = link.get('href')
                # Pattern: /results/track-name/123456/
                match = re.search(r'/results/([^/]+)/(\d+)/?$', href)
                if match:
                    slug = match.group(1)
                    meeting_id = match.group(2)
                    meeting_name = slug.replace('-', ' ').title()
                    
                    if meeting_id not in seen_ids:
                        seen_ids.add(meeting_id)
                        
                        # Construct Form Guide URL
                        # Note: Sometimes the ID in results is different? 
                        # User said: "results/addington/249609/" -> "form-guides/addington/fields/249609/"
                        # So ID is shared.
                        
                        form_url = f"https://www.thegreyhoundrecorder.com.au/form-guides/{slug}/fields/{meeting_id}/"
                        
                        meetings.append({
                            'id': meeting_id,
                            'name': meeting_name,
                            'slug': slug,
                            'form_url': form_url,
                            'results_url': f"https://www.thegreyhoundrecorder.com.au{href}" if href.startswith('/') else href
                        })
            
        except Exception as e:
            print(f"Error fetching search page: {e}")
        finally:
            browser.close()
            
    return meetings

def save_race_to_db(race_data):
    """
    Save scraped race data (from fields) to Supabase.
    Logic copied from scraper.py upsert_race_data but simplified.
    """
    try:
        # Prepare race record
        race_record = {
            'meeting_name': race_data['meeting_name'],
            'meeting_url': race_data['meeting_url'],
            'race_number': race_data['race_number'],
            'race_time': race_data['race_time'], # YYYY-MM-DD from scraper
            'distance_meters': race_data.get('distance_meters'),
            'status': 'closed', # Set to closed so it gets picked up by backfill_results (which looks for != resulted)
            'active_runner_count': race_data['active_runner_count']
        }
        
        # Conflict resolution is tricky. 
        # scraper.py deletes based on meeting+race+time range.
        # Here we have exact date.
        
        # Check if race exists
        # We match on meeting_name + race_number + date (race_time)
        res = supabase.table('races').select('id').match({
            'meeting_name': race_data['meeting_name'],
            'race_number': race_data['race_number'],
            'race_time': race_data['race_time']
        }).execute()
        
        race_id = None
        if res.data:
            race_id = res.data[0]['id']
            # Update existing
            supabase.table('races').update(race_record).eq('id', race_id).execute()
        else:
            # Insert new
            res = supabase.table('races').insert(race_record).execute()
            if res.data:
                race_id = res.data[0]['id']

        if not race_id:
            print(f"Start failed for {race_data['meeting_name']} R{race_data['race_number']}")
            return

        # Handle Runners
        # Delete existing runners
        supabase.table('runners').delete().eq('race_id', race_id).execute()
        
        # Insert new runners
        runners_to_insert = []
        for r in race_data['runners']:
            runners_to_insert.append({
                'race_id': race_id,
                'box_number': r['box_number'],
                'dog_name': r['dog_name'],
                'ghr_odds': r.get('ghr_odds'),
                'sportsbet_odds': r.get('sportsbet_odds'),
                'is_scratched': r['is_scratched']
            })
            
        if runners_to_insert:
            supabase.table('runners').insert(runners_to_insert).execute()
            
        return race_id

    except Exception as e:
        print(f"DB Save Error: {e}")
        return None

def update_race_results(meeting_name, race_number, race_date, results_data):
    """
    Update the race with results (positions and SPs).
    """
    try:
        # Find race ID
        res = supabase.table('races').select('id').match({
            'meeting_name': meeting_name,
            'race_number': race_number,
            'race_time': race_date
        }).execute()
        
        if not res.data:
            print(f"Race not found for results: {meeting_name} R{race_number}")
            return

        race_id = res.data[0]['id']
        
        # Update runners
        for res_runner in results_data['results']:
             supabase.table('runners').update({
                 'finishing_position': res_runner['finishing_position'],
                 'starting_price': res_runner['starting_price']
             }).match({
                 'race_id': race_id,
                 'box_number': res_runner['box_number']
                 # We match box number as it's cleaner than name sometimes
             }).execute()
        
        # Mark race as resulted
        supabase.table('races').update({'status': 'resulted'}).eq('id', race_id).execute()
        print(f"  ✅ Results updated for R{race_number}")

    except Exception as e:
        print(f"Result Update Error: {e}")

def main():
    current_date = START_DATE
    while current_date <= END_DATE:
        print(f"\n\n========================================")
        print(f"PROCESSING DATE: {current_date.strftime('%Y-%m-%d')}")
        print(f"========================================")
        
        meetings = get_meetings_for_date(current_date)
        print(f"Found {len(meetings)} meetings.")
        
        for m in meetings:
            print(f"\n--- Processing {m['name']} ---")
            print(f"Fields URL: {m['form_url']}")
            
            # 1. Scrape Fields
            # Note: scrape_meeting_fields returns List[Dict] (races)
            # It expects specific DOM structure. hopefully backdated pages are same.
            try:
                races_data = scrape_meeting_fields(m['form_url'], m['name'])
                
                if not races_data:
                    print("No races found in form guide.")
                    continue
                    
                # 2. Save Race skeletons
                for r_data in races_data:
                    # Enforce date from our loop to ensure matching
                    r_data['race_time'] = current_date.strftime('%Y-%m-%d')
                    save_race_to_db(r_data)
                    
                print(f"Saved {len(races_data)} race skeletons.")
                
            except Exception as e:
                print(f"Error scraping fields for {m['name']}: {e}")
                continue

            # 3. Scrape Results
            try:
                # Reuse the new results scraper
                # scrape_meeting_results_new(url, name)
                results = scrape_meeting_results_new(m['form_url'], m['name']) # It converts form URL to results URL inside
                
                for r_res in results:
                    update_race_results(
                        m['name'], 
                        r_res['race_number'], 
                        current_date.strftime('%Y-%m-%d'),
                        r_res
                    )
                    
            except Exception as e:
                 print(f"Error scraping results for {m['name']}: {e}")

        # Advance date
        current_date += timedelta(days=1)
        # Sleep to be nice
        time.sleep(2)

if __name__ == "__main__":
    main()
