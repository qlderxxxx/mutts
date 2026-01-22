"""
Quick script to backfill from archive - prompts for credentials
"""
import os

# Prompt for credentials
print("Enter your Supabase credentials:")
supabase_url = input("SUPABASE_URL: ").strip()
supabase_key = input("SUPABASE_KEY: ").strip()

# Set environment variables
os.environ['SUPABASE_URL'] = supabase_url
os.environ['SUPABASE_KEY'] = supabase_key

# Import and run backfill
from backfill_from_archive import backfill_from_archive

# Backfill from 2 days ago
backfill_from_archive(days_ago=2)
