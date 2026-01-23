
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict
from supabase import create_client
from scraper import fetch_page, count_active_runners

# Supabase credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL:
    SUPABASE_URL = 'https://yvnkyakuamvahtiwbneq.supabase.co'
if not SUPABASE_KEY:
    SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2bmt5YWt1YW12YWh0aXdibmVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5Mzg4MTQsImV4cCI6MjA4NDUxNDgxNH0.-v9LyyRgX2tj9EFCImHo44XxSQcZ4_GmQZw-q7ZTX5I'

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def backfill_distances():
    print("Starting distance backfill...")

    # Get all races with missing distance OR invalid distance (>1000)
    # Supabase filter: distance_meters is null OR distance_meters > 1000
    # Client-side filtering is easier for combined conditions
    # Fetch all races (or chunked if too many) - for now fetch recent/all
    print("Fetching races to check...")
    response = supabase.table('races').select('id, meeting_name, meeting_url, race_number, distance_meters').execute()
    all_races = response.data
    
    races_to_update = [
        r for r in all_races 
        if r['distance_meters'] is None or r['distance_meters'] > 1000
    ]
    
    if not races_to_update:
        print("No races found with missing/invalid distance.")
        return

    print(f"Found {len(races_to_update)} races with missing or invalid distance (>1000m).")

    # Group by meeting_url to minimize requests
    meetings = {}
    for race in races_to_update:
        url = race.get('meeting_url')
        if not url:
            continue
        
        if url not in meetings:
            meetings[url] = []
        meetings[url].append(race)

    print(f"grouped into {len(meetings)} unique meetings.")

    for i, (url, race_list) in enumerate(meetings.items(), 1):
        meeting_name = race_list[0]['meeting_name']
        print(f"[{i}/{len(meetings)}] Processing {meeting_name}...")
        
        try:
            soup = fetch_page(url)
            if not soup:
                print(f"  Failed to fetch {url}")
                continue

            # Find all race events
            race_events = soup.select('.form-guide-field-event')
            
            updates_count = 0
            
            for race_event in race_events:
                # Extract header
                header_elem = race_event.select_one('.form-guide-field-event__header')
                if not header_elem:
                    continue
                
                header_text = header_elem.get_text(strip=True)
                
                # Match Race Number
                race_match = re.search(r'Race\s+(\d+)', header_text)
                if not race_match:
                    continue
                race_num = int(race_match.group(1))

                # Match Distance (Safe Regex)
                dist_match = re.search(r'\b([2-9]\d{2})m\b', header_text)
                distance = None
                
                if dist_match:
                    distance = int(dist_match.group(1))
                
                # Check if we need to update this race
                # Find matching race in our list
                target_races = [r for r in race_list if r['race_number'] == race_num]
                
                for target_race in target_races:
                    current_dist = target_race.get('distance_meters')
                    
                    # Updates:
                    # 1. We found a valid distance, and it differs from DB
                    # 2. We did NOT find a valid distance, but DB has invalid value (>1000) -> Set to None
                    
                    if distance is not None:
                         if current_dist != distance:
                            print(f"  Fixing R{race_num}: {current_dist} -> {distance}m")
                            supabase.table('races').update({'distance_meters': distance}).eq('id', target_race['id']).execute()
                            updates_count += 1
                    elif current_dist and current_dist > 1000:
                        print(f"  Clearing Invalid R{race_num}: {current_dist} -> NULL")
                        supabase.table('races').update({'distance_meters': None}).eq('id', target_race['id']).execute()
                        updates_count += 1
            
            print(f"  -> Updated {updates_count} races for {meeting_name}")
            
            # Rate limit
            time.sleep(2)

        except Exception as e:
            print(f"  Error processing {meeting_name}: {e}")

    print("Backfill complete!")

if __name__ == "__main__":
    backfill_distances()
