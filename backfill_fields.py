"""
Backfill Fields Script
Re-scrapes form guide (fields) data for races in the past N days that are missing data.
Useful for recovering races missed during downtime.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from supabase import create_client

from scraper import scrape_meeting_fields, upsert_race_data, AEST

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL:
    SUPABASE_URL = 'https://yvnkyakuamvahtiwbneq.supabase.co'
    SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2bmt5YWt1YW12YWh0aXdibmVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5Mzg4MTQsImV4cCI6MjA4NDUxNDgxNH0.-v9LyyRgX2tj9EFCImHo44XxSQcZ4_GmQZw-q7ZTX5I'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def construct_meeting_url(meeting_name: str, race_time: str) -> str:
    """Reconstruct the form guide URL from meeting name and race time."""
    track_slug = meeting_name.lower().replace(' ', '-')
    race_date_str = race_time.split('T')[0]
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    date_id = race_date.strftime('%d%m%y')
    return f"https://www.thegreyhoundrecorder.com.au/form-guides/{track_slug}/fields/{date_id}/"


def backfill_fields(days_back: int = 7):
    """
    Re-scrape form guide fields for races in the past N days.
    Only targets races that have no runners or are missing key data.

    Args:
        days_back: Number of days to look back (default: 7)
    """
    print(f"\n{'='*60}")
    print(f"BACKFILLING FIELDS FOR PAST {days_back} DAYS")
    print(f"{'='*60}\n")

    now = datetime.now(AEST)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=days_back)

    start_str = start_date.strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    print(f"Date range: {start_str} to {today_str}")

    # Fetch races in the date range - check which ones have no runners
    try:
        response = supabase.table('races').select(
            'id, meeting_name, meeting_url, race_time, active_runner_count'
        ).gte('race_time', start_str).lte('race_time', today_str + 'T23:59:59').execute()

        all_races = response.data
        print(f"Found {len(all_races)} total races in date range")

        # Target races with 0 runners (missing field data)
        missing_races = [r for r in all_races if not r.get('active_runner_count') or r['active_runner_count'] == 0]
        print(f"Found {len(missing_races)} races with missing runner data")

        if not missing_races:
            print("\nAll races in range already have runner data!")
            return

        # Group by meeting_url to avoid duplicate scrapes
        meetings_to_scrape = {}
        for race in missing_races:
            meeting_url = race.get('meeting_url')
            meeting_name = race['meeting_name']
            race_time = race['race_time']

            # Reconstruct URL if missing
            if not meeting_url:
                meeting_url = construct_meeting_url(meeting_name, race_time)
                print(f"  Reconstructed URL for {meeting_name}: {meeting_url}")

            if meeting_url not in meetings_to_scrape:
                meetings_to_scrape[meeting_url] = meeting_name

        print(f"\nWill re-scrape {len(meetings_to_scrape)} unique meetings\n")

        # Scrape and upsert each meeting
        total_races_updated = 0
        for idx, (meeting_url, meeting_name) in enumerate(meetings_to_scrape.items(), 1):
            print(f"[{idx}/{len(meetings_to_scrape)}] Scraping fields for {meeting_name}...")
            try:
                races = scrape_meeting_fields(meeting_url, meeting_name)
                if races:
                    for race in races:
                        upsert_race_data(race)
                        total_races_updated += 1
                    print(f"  -> Upserted {len(races)} races for {meeting_name}")
                else:
                    print(f"  -> No races found (page may no longer be available)")
            except Exception as e:
                print(f"  -> Failed: {e}")

        print(f"\n{'='*60}")
        print(f"BACKFILL COMPLETE!")
        print(f"{'='*60}")
        print(f"Scraped {len(meetings_to_scrape)} meetings")
        print(f"Updated {total_races_updated} races with field data")

    except Exception as e:
        print(f"Error during backfill: {e}")
        raise


if __name__ == '__main__':
    days_back = 7
    if len(sys.argv) > 1:
        try:
            days_back = int(sys.argv[1])
        except ValueError:
            print(f"Invalid argument: {sys.argv[1]}. Using default of 7 days.")

    backfill_fields(days_back)
