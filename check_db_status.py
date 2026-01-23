import os
import sys
from supabase import create_client, Client
from datetime import datetime

# Initialize Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url:
    url = input("SUPABASE_URL: ")
if not key:
    key = input("SUPABASE_KEY: ")

supabase: Client = create_client(url, key)

def check_backfill_status():
    try:
        # Check races on Jan 21 specifically
        print("\nChecking races for 2026-01-21...")
        response = supabase.table('races') \
            .select('race_id, meeting_name, race_number, race_time, top_2_in_top_2, active_runner_count') \
            .gte('race_time', '2026-01-21T00:00:00') \
            .lt('race_time', '2026-01-22T00:00:00') \
            .eq('active_runner_count', 4) \
            .execute()
        
        races = response.data
        print(f"Found {len(races)} races with 4 runners on Jan 21.")
        
        null_count = sum(1 for r in races if r['top_2_in_top_2'] is None)
        valid_count = sum(1 for r in races if r['top_2_in_top_2'] is not None)
        
        print(f"  Null top_2_in_top_2: {null_count}")
        print(f"  Valid top_2_in_top_2: {valid_count}")
        
        if null_count > 0:
            print("\nRaces with NULL top_2_in_top_2:")
            for r in races:
                if r['top_2_in_top_2'] is None:
                    print(f"  - {r['meeting_name']} R{r['race_number']} ({r['race_time']}) Top2={r['top_2_in_top_2']}")

    except Exception as e:
        print(f"Error querying DB: {e}")

if __name__ == "__main__":
    check_backfill_status()
