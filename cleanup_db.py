#!/usr/bin/env python3
"""Clean up database - delete all races and runners"""

import os
import sys
from supabase import create_client, Client

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Deleting all runners...")
result = supabase.table('runners').delete().neq('id', 0).execute()
print(f"Deleted runners")

print("Deleting all races...")
result = supabase.table('races').delete().neq('id', 0).execute()
print(f"Deleted races")

print("\nDatabase cleaned successfully!")
