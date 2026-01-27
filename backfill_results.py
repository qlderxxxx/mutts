import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from supabase import create_client

# Import the scraping functions from the main scraper
from scraper import update_race_results, AEST
from new_results_scraper import scrape_meeting_results_new as scrape_meeting_results

# Supabase credentials
# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL:
    SUPABASE_URL = 'https://yvnkyakuamvahtiwbneq.supabase.co'
    SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2bmt5YWt1YW12YWh0aXdibmVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5Mzg4MTQsImV4cCI6MjA4NDUxNDgxNH0.-v9LyyRgX2tj9EFCImHo44XxSQcZ4_GmQZw-q7ZTX5I'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def backfill_results(days_back: int = 7):
    """
    Backfill race results for the past N days.
    
    Args:
        days_back: Number of days to look back (default: 7)
    """
    print(f"\n{'='*60}")
    print(f"BACKFILLING RESULTS FOR PAST {days_back} DAYS")
    print(f"{'='*60}\n")
    
    # Calculate date range - exclude today, only backfill past races
    today = datetime.now(AEST)
    yesterday = today - timedelta(days=1)
    start_date = today - timedelta(days=days_back)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"Date range: {start_date_str} to {yesterday_str} (excluding today)")
    
    # Fetch races from the date range (up to yesterday, not today)
    try:
        response = supabase.table('races').select('meeting_name, meeting_url, race_time, status').gte('race_time', start_date_str).lt('race_time', yesterday_str + 'T23:59:59').execute()
        races_to_check = response.data
        
        print(f"Found {len(races_to_check)} total races in date range")
        
        # Filter to only races that haven't been resulted yet
        unresulted_races = [r for r in races_to_check if r.get('status') != 'resulted']
        print(f"Found {len(unresulted_races)} races without results")
        
        if not unresulted_races:
            print("\nAll races already have results!")
            return
        
        # Group by meeting_url to avoid duplicate scrapes
        # Store metadata: {url: {'name': name, 'date': date_str}}
        meetings_to_scrape = {}
        skipped_fake_urls = 0
        
        for race in unresulted_races:
            meeting_url = race.get('meeting_url')
            meeting_name = race['meeting_name']
            
            # DEBUG
            if skipped_fake_urls < 3:
                print(f"DEBUG: {meeting_name} race_time={race.get('race_time')} url={meeting_url}")
            
            # Extract date from race_time
            race_date = None
            try:
                r_time_iso = race.get('race_time')
                if r_time_iso:
                    # Handle ISO format
                    if r_time_iso.endswith('Z'):
                        r_time_iso = r_time_iso.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(r_time_iso)
                    dt_aest = dt.astimezone(AEST)
                    race_date = dt_aest.strftime('%Y-%m-%d')
            except Exception as e:
                print(f"Warn: Date parse error for {meeting_name}: {e}")
    
            if not race_date:
                print(f"Skipping {meeting_name} - No Date")
                continue
    
            # CRITICAL: Do NOT scrape Future races.
            today_str = datetime.now(AEST).strftime('%Y-%m-%d')
            if race_date >= today_str:
                 print(f"Skipping Future/Today Race: {meeting_name} on {race_date} (Today is {today_str})")
                 continue
    
            # Skip if no URL or sportsbet
            if not meeting_url or "sportsbet.com.au" in meeting_url:
                skipped_fake_urls += 1
                continue
                
            if meeting_url not in meetings_to_scrape:
                meetings_to_scrape[meeting_url] = {
                    'name': meeting_name,
                    'date': race_date
                }
        
        if skipped_fake_urls > 0:
            print(f"Skipped {skipped_fake_urls} races with fake date-based URLs")
        
        if not meetings_to_scrape:
            print("\nNo races with real meeting URLs found. Only races that were scraped from the form guide can be backfilled.")
            return
        
        print(f"\nWill scrape results from {len(meetings_to_scrape)} unique meetings\n")
        
        # Scrape results for each meeting
        all_results = []
        for idx, (meeting_url, meta) in enumerate(meetings_to_scrape.items(), 1):
            meeting_name = meta['name']
            meeting_date = meta['date']
            print(f"[{idx}/{len(meetings_to_scrape)}] Scraping results for {meeting_name} ({meeting_date})...", flush=True)
            try:
                results = scrape_meeting_results(meeting_url, meeting_name)
                # Only inject race_date if missing? 
                # Actually, let's trust the scraper's parsed date. 
                # If scraper fails, THEN use meeting_date as fallback.
                for r in results:
                    if not r.get('race_date'):
                        r['race_date'] = meeting_date
                
                all_results.extend(results)
                print(f"  -> Found {len(results)} race results", flush=True)
            except Exception as e:
                print(f"  Failed to scrape {meeting_name}: {e}", flush=True)
        
        # Update database with results
        print(f"\n{'='*60}")
        print(f"UPDATING DATABASE WITH {len(all_results)} RACE RESULTS")
        print(f"{'='*60}\n")
        
        for idx, race_results in enumerate(all_results, 1):
            meeting_name = race_results['meeting_name']
            race_number = race_results['race_number']
            r_date = race_results.get('race_date', 'Unknown')
            print(f"[{idx}/{len(all_results)}] Updating {meeting_name} R{race_number} ({r_date})...")
            update_race_results(race_results)
        
        print(f"\n{'='*60}")
        print(f"BACKFILL COMPLETE!")
        print(f"{'='*60}")
        print(f"Scraped {len(meetings_to_scrape)} meetings")
        print(f"Updated {len(all_results)} races with results")
        
    except Exception as e:
        print(f"Error during backfill: {e}")
        raise

if __name__ == '__main__':
    # Allow specifying days back as command line argument
    days_back = 7
    if len(sys.argv) > 1:
        try:
            days_back = int(sys.argv[1])
        except ValueError:
            print(f"Invalid argument: {sys.argv[1]}. Using default of 7 days.")
    
    backfill_results(days_back)
