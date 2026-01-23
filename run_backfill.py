"""
Quick backfill script - prompts for credentials and runs backfill
"""
import os
import sys

# Prompt for credentials
print("Enter your Supabase credentials:")
supabase_url = input("SUPABASE_URL: ").strip()
supabase_key = input("SUPABASE_KEY: ").strip()

# Set environment variables
os.environ['SUPABASE_URL'] = supabase_url
os.environ['SUPABASE_KEY'] = supabase_key

# Import and run backfill
from backfill_results import backfill_results

# Run backfill for 3 days
backfill_results(days_back=3)
