import os
import sys
from supabase import create_client, Client
from datetime import datetime, timedelta

# Create Supabase client (using mock envs if locally running without them, but relies on system having them or user provided)
# We'll just define the imports and main check logic.
# The user env likely has the keys set in the terminal session if we use run_command with env?
# Or I might need to ask for them or hardcode the ones I saw earlier (risky if they expire).
# I'll rely on the user having run successful commands before. 
# Wait, I saw keys in previous outputs. 
# URL: https://yvnkyakuamvahtiwbneq.supabase.co
# KEY: ... (service role)
# I will try to read from env or prompt.

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yvnkyakuamvahtiwbneq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# If key missing, I'll print a message to supply it, or use the one I saw (if I can recall it safely - better not hardcode in artifacts).
# I'll let the script fail if no key, and then user (me) can supply it in command input.

def audit_stats():
    # If no key, ask for it
    global SUPABASE_KEY
    if not SUPABASE_KEY:
        SUPABASE_KEY = input("Enter SUPABASE_KEY: ")
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("\n=== AUDIT: 4-Runner Races (History Audit) ===")
    
    # Get all races from last 3 days
    today = datetime.now()
    start_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    print(f"Checking races from {start_date} to {today_str} (excluding today)...")
    
    response = supabase.table('races') \
        .select('*') \
        .gte('race_time', start_date) \
        .lt('race_time', today_str) \
        .eq('active_runner_count', 4) \
        .execute()
        
    races = response.data
    print(f"Found {len(races)} historical 4-runner races.")
    
    stats_count = 0
    
    print("\nDetails:")
    print(f"{'Date':<12} {'Meeting':<20} {'Race':<5} {'Status':<10} {'Top2inTop2':<10} {'Included?'}")
    print("-" * 75)
    
    for r in races:
        # Check if included in stats (top_2_in_top_2 is not null)
        is_included = r['top_2_in_top_2'] is not None
        
        status_str = r['status'] or 'null'
        t2_str = str(r['top_2_in_top_2'])
        inc_str = "YES" if is_included else "NO"
        
        if is_included:
            stats_count += 1
            
        date_short = r['race_time'].split('T')[0]
        print(f"{date_short:<12} {r['meeting_name']:<20} {r['race_number']:<5} {status_str:<10} {t2_str:<10} {inc_str}")

    print("-" * 75)
    print(f"Total Stats Denominator: {stats_count}")
    print("If this matches '2', then the rows with 'YES' are the culprits.")

if __name__ == "__main__":
    try:
        from supabase import create_client
    except ImportError:
        print("Installing supabase...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase"])
        from supabase import create_client

    audit_stats()
