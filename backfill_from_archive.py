"""
Backfill results by finding the real meeting URLs from the form guide archive.
This works by:
1. Finding races from N days ago in the database
2. Scraping the form guide page for that date to get real meeting URLs
3. Matching meetings by name and date
4. Scraping results using the real URLs
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict
from supabase import create_client

# Import from main scraper
from scraper import scrape_meeting_results, update_race_results, AEST, fetch_page

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RESULTS_URL = "https://www.thegreyhoundrecorder.com.au/results/"

def get_meeting_urls_for_date(target_date: datetime) -> Dict[str, str]:
    """
    Scrape the results page to get real meeting URLs for a specific date.
    The results page shows historical dates with links to each meeting's results.
    Returns dict of {meeting_name: results_url}
    """
    print(f"\nFetching results page to find meeting URLs for {target_date.strftime('%Y-%m-%d')}...")
    
    # Format date for the results page search (YYYY-MM-DD)
    date_str = target_date.strftime('%Y-%m-%d')
    results_search_url = f"{RESULTS_URL}?date={date_str}"
    
    soup = fetch_page(results_search_url)
    if not soup:
        print("Could not fetch results page")
        return {}
    
    # The results page shows meetings grouped by date
    # Find the date header for our target date
    target_date_display = target_date.strftime('%A, %B %d')  # e.g., "Wednesday, January 21"
    
    meetings = {}
    
    # Find all meeting result links
    # They appear as links with meeting names followed by "Results" buttons
    meeting_sections = soup.find_all('div', class_='results-meeting')
    
    if not meeting_sections:
        # Try alternative structure - look for meeting names and Results buttons
        print("Trying alternative parsing method...")
        
        # Find all Results buttons/links
        result_links = soup.select('a[href*="/results/"]')
        
        for link in result_links:
            href = link.get('href')
            if not href or '/results/' not in href:
                continue
            
            # Extract meeting name from URL
            # URL format: /results/[track-name]/[meeting-id]/
            url_parts = href.split('/')
            if len(url_parts) >= 4:
                track_slug = url_parts[-3] if url_parts[-1] == '' else url_parts[-2]
                meeting_name = track_slug.replace('-', ' ').title()
                
                # Validate ID: Must be numeric and logical (e.g. > 240000)
                # This filters out date-based IDs (e.g. 220126) and generic pages
                meeting_id = url_parts[-2]
                
                if not meeting_id.isdigit():
                    continue
                    
                if int(meeting_id) < 240000:
                    print(f"  Skipping likely invalid/date ID: {meeting_name} -> {meeting_id}")
                    continue

                # Build full URL
                if not href.startswith('http'):
                    href = 'https://www.thegreyhoundrecorder.com.au' + href
                
                # Convert results URL back to form guide URL for consistency
                # /results/angle-park/250176/ -> /form-guides/angle-park/fields/250176/
                form_guide_url = href.replace('/results/', '/form-guides/').replace(f'/{meeting_id}/', f'/fields/{meeting_id}/')
                
                if meeting_name not in meetings:
                    meetings[meeting_name] = form_guide_url
                    print(f"  Found: {meeting_name} -> {form_guide_url}")
    
    return meetings

def backfill_from_archive(days_ago: int = 2):
    """
    Backfill results for races from N days ago by finding real meeting URLs.
    """
    print(f"\n{'='*60}")
    print(f"BACKFILLING RESULTS FROM {days_ago} DAYS AGO")
    print(f"{'='*60}\n")
    
    # Calculate target date
    today = datetime.now(AEST)
    target_date = today - timedelta(days=days_ago)
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    print(f"Target date: {target_date_str}")
    
    # Get real meeting URLs from the form guide archive
    real_meeting_urls = get_meeting_urls_for_date(target_date)
    
    if not real_meeting_urls:
        print(f"\nNo meetings found on form guide for {target_date_str}")
        print("The form guide might only show today/tomorrow, or the date might be too old.")
        return
    
    print(f"\nFound {len(real_meeting_urls)} meetings with real URLs")
    
    # Fetch races from database for this date
    try:
        response = supabase.table('races').select('meeting_name, race_number, status, meeting_url').gte('race_time', target_date_str).lt('race_time', target_date_str + 'T23:59:59').execute()
        db_races = response.data
        
        print(f"Found {len(db_races)} races in database for {target_date_str}")
        
        # Group by meeting name
        db_meetings = {}
        for race in db_races:
            meeting_name = race['meeting_name']
            if meeting_name not in db_meetings:
                db_meetings[meeting_name] = []
            db_meetings[meeting_name].append(race)
        
        # Match meetings and scrape results
        all_results = []
        
        # Merge web-found meetings and DB-found meetings
        # Web found (real_meeting_urls) takes precedence if VALID
        
        # Check DB races for valid meeting URLs first
        db_urls = {}
        for race in db_races:
            m_name = race['meeting_name']
            m_url = race.get('meeting_url')
            # Extract ID from DB URL if present
            if m_url and '/form-guides/' in m_url:
                try:
                    # Simple check for ID validity
                    # .../fields/250176/
                    parts = m_url.strip('/').split('/')
                    if parts[-1].isdigit() and int(parts[-1]) > 240000:
                        db_urls[m_name] = m_url
                except:
                    pass

        # Combined list of meeting names to check
        all_meeting_names = set(db_meetings.keys())
        
        for meeting_name in all_meeting_names:
            # Determine which URL to use
            scrape_url = None
            source = "None"
            
            if meeting_name in real_meeting_urls:
                scrape_url = real_meeting_urls[meeting_name]
                source = "Web Archive"
            elif meeting_name in db_urls:
                scrape_url = db_urls[meeting_name]
                source = "DB Record"
            
            if scrape_url:
                races_count = len(db_meetings[meeting_name])
                resulted_count = sum(1 for r in db_meetings[meeting_name] if r.get('status') == 'resulted')
                
                print(f"\n[{meeting_name}] {races_count} races (Source: {source}), {resulted_count} resulted")
                
                if resulted_count < races_count:
                    print(f"  Scraping results from {scrape_url}...")
                    results = scrape_meeting_results(scrape_url, meeting_name)
                    all_results.extend(results)
                    print(f"  -> Found {len(results)} race results")
                else:
                    print(f"  All races already have results, skipping")
            else:
                print(f"\n[{meeting_name}] No valid URL found in Archive or DB. Skipping.")
        
        # Update database
        if all_results:
            print(f"\n{'='*60}")
            print(f"UPDATING DATABASE WITH {len(all_results)} RACE RESULTS")
            print(f"{'='*60}\n")
            
            for idx, race_results in enumerate(all_results, 1):
                meeting_name = race_results['meeting_name']
                race_number = race_results['race_number']
                print(f"[{idx}/{len(all_results)}] Updating {meeting_name} R{race_number}...")
                update_race_results(race_results)
            
            print(f"\n{'='*60}")
            print(f"BACKFILL COMPLETE!")
            print(f"{'='*60}")
            print(f"Updated {len(all_results)} races with results")
        else:
            print("\nNo results to update")
        
    except Exception as e:
        print(f"Error during backfill: {e}")
        raise

if __name__ == '__main__':
    import sys
    days_ago = 2
    if len(sys.argv) > 1:
        try:
            days_ago = int(sys.argv[1])
        except ValueError:
            print(f"Invalid argument: {sys.argv[1]}. Using default of 2 days.")
    
    backfill_from_archive(days_ago)
