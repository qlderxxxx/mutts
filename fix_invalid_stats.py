import os
import sys
from supabase import create_client

# Use supplied key or user input if needed (I will assume I can reuse the one I just got or ask again if env not set)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yvnkyakuamvahtiwbneq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def fix_invalid_stats():
    global SUPABASE_KEY
    if not SUPABASE_KEY:
        SUPABASE_KEY = input("Enter SUPABASE_KEY: ")
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("\n=== FIX: Resetting Invalid Stats ===")
    
    # Get all resulted races from last few days
    # We want to check if they actually have valid SPs
    response = supabase.table('races') \
        .select('*, runners(*)') \
        .eq('status', 'resulted') \
        .execute()
        
    races = response.data
    print(f"Checking {len(races)} resulted races for valid SPs...")
    
    fixed_count = 0
    
    for r in races:
        runners = r.get('runners', [])
        
        # Check SPs
        valid_sps = [run['starting_price'] for run in runners if run['starting_price'] is not None and run['starting_price'] > 0]
        
        if len(valid_sps) < 2:
            # Insufficient SPs to calculate Top 2
            # Check if top_2_in_top_2 is currently set (not None)
            if r['top_2_in_top_2'] is not None:
                print(f"Fixing {r['meeting_name']} R{r['race_number']} (Valid SPs: {len(valid_sps)})...")
                
                # Reset to NULL
                supabase.table('races').update({
                    'top_2_in_top_2': None
                }).eq('id', r['id']).execute()
                
                fixed_count += 1
                
    print(f"\nFixed {fixed_count} races.")
    print("These races will now be excluded from stats calculations.")

if __name__ == "__main__":
    fix_invalid_stats()
