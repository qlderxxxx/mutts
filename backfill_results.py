"""
One-time script to backfill race results for historical races.
This scrapes results for races from the past N days.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict
from supabase import create_client

# Import the scraping functions from the main scraper
from scraper import scrape_meeting_results, update_race_results, AEST

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

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
    
    # Calculate date range
    today = datetime.now(AEST)
    start_date = today - timedelta(days=days_back)
    start_date_str = start_date.strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    print(f"Date range: {start_date_str} to {today_str}")
    
    # Fetch races from the date range
    try:
        response = supabase.table('races').select('meeting_name, meeting_url, race_time, status').gte('race_time', start_date_str).lte('race_time', today_str).execute()
        races_to_check = response.data
        
        print(f"Found {len(races_to_check)} total races in date range")
        
        # Filter to only races that haven't been resulted yet
        unresulted_races = [r for r in races_to_check if r.get('status') != 'resulted']
        print(f"Found {len(unresulted_races)} races without results")
        
        if not unresulted_races:
            print("\n✅ All races already have results!")
            return
        
        # Group by meeting_url to avoid duplicate scrapes
        meetings_to_scrape = {}
        for race in unresulted_races:
            meeting_url = race.get('meeting_url')
            meeting_name = race['meeting_name']
            
            # Skip if no meeting_url
            if not meeting_url:
                print(f"⚠️  Warning: No meeting_url for {meeting_name}, skipping")
                continue
            
            if meeting_url not in meetings_to_scrape:
                meetings_to_scrape[meeting_url] = meeting_name
        
        print(f"\nWill scrape results from {len(meetings_to_scrape)} unique meetings\n")
        
        # Scrape results for each meeting
        all_results = []
        for idx, (meeting_url, meeting_name) in enumerate(meetings_to_scrape.items(), 1):
            print(f"[{idx}/{len(meetings_to_scrape)}] Scraping results for {meeting_name}...")
            results = scrape_meeting_results(meeting_url, meeting_name)
            all_results.extend(results)
            print(f"  → Found {len(results)} race results")
        
        # Update database with results
        print(f"\n{'='*60}")
        print(f"UPDATING DATABASE WITH {len(all_results)} RACE RESULTS")
        print(f"{'='*60}\n")
        
        for idx, race_results in enumerate(all_results, 1):
            meeting_name = race_results['meeting_name']
            race_number = race_results['race_number']
            print(f"[{idx}/{len(all_results)}] Updating {meeting_name} R{race_number}...")
            update_race_results(race_results)
        
        print(f"\n{'='*60}")
        print(f"✅ BACKFILL COMPLETE!")
        print(f"{'='*60}")
        print(f"Scraped {len(meetings_to_scrape)} meetings")
        print(f"Updated {len(all_results)} races with results")
        
    except Exception as e:
        print(f"❌ Error during backfill: {e}")
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
