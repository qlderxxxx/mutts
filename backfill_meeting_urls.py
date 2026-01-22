"""
One-time script to backfill meeting_url for existing races in the database.
This reconstructs the form guide URLs based on meeting_name and race_time.
"""

import os
from datetime import datetime
from supabase import create_client

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def construct_meeting_url(meeting_name: str, race_time: str) -> str:
    """
    Construct the form guide URL from meeting name and race time.
    
    Args:
        meeting_name: e.g., "Angle Park"
        race_time: ISO timestamp e.g., "2026-01-22T19:30:00+00:00"
    
    Returns:
        Form guide URL e.g., "https://www.thegreyhoundrecorder.com.au/form-guides/angle-park/fields/220126/"
    """
    # Convert meeting name to slug (e.g., "Angle Park" -> "angle-park")
    track_slug = meeting_name.lower().replace(' ', '-')
    
    # Parse race_time and get date ID in DDMMYY format
    # Handle both with and without timezone
    if 'T' in race_time:
        race_date_str = race_time.split('T')[0]
    else:
        race_date_str = race_time
    
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d')
    date_id = race_date.strftime('%d%m%y')
    
    meeting_url = f"https://www.thegreyhoundrecorder.com.au/form-guides/{track_slug}/fields/{date_id}/"
    
    return meeting_url

def main():
    print("Fetching races without meeting_url...")
    
    # Fetch all races that don't have a meeting_url
    response = supabase.table('races').select('id, meeting_name, race_time, meeting_url').execute()
    races = response.data
    
    races_to_update = [r for r in races if not r.get('meeting_url')]
    
    print(f"Found {len(races_to_update)} races without meeting_url")
    
    if not races_to_update:
        print("All races already have meeting_url. Nothing to do!")
        return
    
    # Group by meeting to show progress
    meetings = {}
    for race in races_to_update:
        meeting_name = race['meeting_name']
        race_time = race['race_time']
        
        # Construct URL
        meeting_url = construct_meeting_url(meeting_name, race_time)
        
        # Track for logging
        meeting_key = f"{meeting_name}_{race_time.split('T')[0]}"
        if meeting_key not in meetings:
            meetings[meeting_key] = {
                'name': meeting_name,
                'url': meeting_url,
                'count': 0
            }
        meetings[meeting_key]['count'] += 1
        
        # Update the race
        try:
            supabase.table('races').update({'meeting_url': meeting_url}).eq('id', race['id']).execute()
        except Exception as e:
            print(f"Error updating race {race['id']}: {e}")
    
    print(f"\n✅ Updated {len(races_to_update)} races across {len(meetings)} meetings:")
    for meeting_key, info in sorted(meetings.items()):
        print(f"  - {info['name']}: {info['count']} races")
        print(f"    URL: {info['url']}")
    
    print("\n🎉 Backfill complete! You can now run the scraper to fetch results.")

if __name__ == '__main__':
    main()
