import os
from supabase import create_client, Client
from collections import Counter
from datetime import datetime

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url:
    url = 'https://yvnkyakuamvahtiwbneq.supabase.co'
    key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2bmt5YWt1YW12YWh0aXdibmVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5Mzg4MTQsImV4cCI6MjA4NDUxNDgxNH0.-v9LyyRgX2tj9EFCImHo44XxSQcZ4_GmQZw-q7ZTX5I'

supabase: Client = create_client(url, key)

def analyze():
    print("Fetching 'closed' races...")
    # Fetch all closed races
    resp = supabase.table('races').select('*').eq('status', 'closed').execute()
    races = resp.data
    
    if not races:
        print("No 'closed' races found.")
        return

    print(f"Found {len(races)} 'closed' races.")
    
    # Analyze Dates
    dates = []
    for r in races:
        # race_time is ISO string
        dt = datetime.fromisoformat(r['race_time'].replace('Z', '+00:00'))
        dates.append(dt)
        
    dates.sort()
    min_date = dates[0]
    max_date = dates[-1]
    
    print(f"\nDate Range:")
    print(f"  Oldest: {min_date}")
    print(f"  Newest: {max_date}")
    
    # Check if they fall within typical backfill windows (e.g. last 7 days)
    # Today is Jan 28
    # 7 days ago = Jan 21
    
    older_than_7_days = [d for d in dates if (datetime.now(d.tzinfo) - d).days > 7]
    print(f"  Older than 7 days: {len(older_than_7_days)}")
    
    # Analyze Meetings
    meetings = [r['meeting_name'] for r in races]
    ctr = Counter(meetings)
    
    print("\nTop 10 Meetings stuck in 'closed':")
    for name, count in ctr.most_common(10):
        print(f"  {name}: {count} races")

    # Sample URL
    print("\nSample URL for debugging:")
    print(f"  {races[0]['meeting_url']}")

if __name__ == "__main__":
    analyze()
