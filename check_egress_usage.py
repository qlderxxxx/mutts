#!/usr/bin/env python3
"""
Check Egress Usage Estimator
Estimates current database size and projected egress usage
"""

import os
import sys
from supabase import create_client

def get_supabase():
    url = os.environ.get("SUPABASE_URL", 'https://yvnkyakuamvahtiwbneq.supabase.co')
    key = os.environ.get("SUPABASE_KEY", 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2bmt5YWt1YW12YWh0aXdibmVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5Mzg4MTQsImV4cCI6MjA4NDUxNDgxNH0.-v9LyyRgX2tj9EFCImHo44XxSQcZ4_GmQZw-q7ZTX5I')
    
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        sys.exit(1)
        
    return create_client(url, key)

def main():
    print("=" * 60)
    print("Supabase Egress Usage Estimator")
    print("=" * 60)
    
    client = get_supabase()
    
    # Count total races
    races_response = client.table('races').select('id', count='exact').execute()
    total_races = races_response.count if races_response.count else 0
    
    # Count total runners
    runners_response = client.table('runners').select('id', count='exact').execute()
    total_runners = runners_response.count if runners_response.count else 0
    
    print(f"\n📊 Database Statistics:")
    print(f"   Total Races: {total_races:,}")
    print(f"   Total Runners: {total_runners:,}")
    print(f"   Avg Runners per Race: {total_runners / total_races if total_races > 0 else 0:.1f}")
    
    # Estimate payload sizes
    # Race record: ~500 bytes (8 columns × ~60 bytes avg)
    # Runner record: ~200 bytes (8 columns × ~25 bytes avg)
    race_size = 500
    runner_size = 200
    
    # OLD query (all races)
    old_payload = (total_races * race_size) + (total_runners * runner_size)
    old_payload_mb = old_payload / (1024 * 1024)
    
    # NEW query - Upcoming view (assume ~20 races in next 2 days)
    upcoming_races = min(20, total_races)
    upcoming_runners = int(upcoming_races * (total_runners / total_races if total_races > 0 else 6))
    new_upcoming_payload = (upcoming_races * race_size) + (upcoming_runners * runner_size)
    new_upcoming_payload_kb = new_upcoming_payload / 1024
    
    # NEW query - History view (assume 7 days = ~150 races)
    history_races = min(150, total_races)
    history_runners = int(history_races * (total_runners / total_races if total_races > 0 else 6))
    new_history_payload = (history_races * race_size) + (history_runners * runner_size)
    new_history_payload_kb = new_history_payload / 1024
    
    print(f"\n📦 Payload Size Estimates:")
    print(f"   OLD (all races): {old_payload_mb:.2f} MB")
    print(f"   NEW (upcoming view): {new_upcoming_payload_kb:.1f} KB")
    print(f"   NEW (history view, 7 days): {new_history_payload_kb:.1f} KB")
    print(f"   Reduction: {((old_payload - new_upcoming_payload) / old_payload * 100):.1f}%")
    
    # Calculate egress projections
    print(f"\n📡 Egress Projections:")
    
    # OLD: Every 2 minutes = 30 requests/hour
    old_requests_per_hour = 30
    old_egress_per_hour = old_payload * old_requests_per_hour
    old_egress_per_day = old_egress_per_hour * 24
    old_egress_per_day_mb = old_egress_per_day / (1024 * 1024)
    
    print(f"\n   OLD (2-min refresh, all races):")
    print(f"      Per hour: {old_egress_per_hour / (1024 * 1024):.1f} MB")
    print(f"      Per day: {old_egress_per_day_mb:.1f} MB")
    print(f"      Per month: {old_egress_per_day_mb * 30:.1f} MB ({old_egress_per_day_mb * 30 / 1024:.2f} GB)")
    
    # NEW: Every 30 minutes = 2 requests/hour, mostly cached
    # Assume 95% cache hit rate (only first request per 30-min window hits DB)
    new_requests_per_hour = 2
    cache_hit_rate = 0.95
    uncached_requests_per_hour = new_requests_per_hour * (1 - cache_hit_rate)
    
    # Assume 80% upcoming view, 20% history view
    avg_new_payload = (new_upcoming_payload * 0.8) + (new_history_payload * 0.2)
    
    new_uncached_egress_per_hour = avg_new_payload * uncached_requests_per_hour
    new_cached_egress_per_hour = avg_new_payload * (new_requests_per_hour - uncached_requests_per_hour)
    
    new_uncached_egress_per_day = new_uncached_egress_per_hour * 24
    new_cached_egress_per_day = new_cached_egress_per_hour * 24
    
    new_uncached_egress_per_day_mb = new_uncached_egress_per_day / (1024 * 1024)
    new_cached_egress_per_day_mb = new_cached_egress_per_day / (1024 * 1024)
    
    print(f"\n   NEW (30-min refresh, filtered queries, 95% cached):")
    print(f"      Uncached per day: {new_uncached_egress_per_day_mb:.2f} MB")
    print(f"      Cached per day: {new_cached_egress_per_day_mb:.2f} MB")
    print(f"      Uncached per month: {new_uncached_egress_per_day_mb * 30:.1f} MB ({new_uncached_egress_per_day_mb * 30 / 1024:.3f} GB)")
    print(f"      Cached per month: {new_cached_egress_per_day_mb * 30:.1f} MB ({new_cached_egress_per_day_mb * 30 / 1024:.3f} GB)")
    
    # Calculate reduction
    total_reduction = ((old_egress_per_day - new_uncached_egress_per_day) / old_egress_per_day * 100)
    
    print(f"\n✅ Expected Improvement:")
    print(f"   Uncached egress reduction: {total_reduction:.1f}%")
    print(f"   Uncached quota usage: {new_uncached_egress_per_day_mb * 30 / 1024 / 5 * 100:.1f}% of 5 GB")
    print(f"   Cached quota usage: {new_cached_egress_per_day_mb * 30 / 1024 / 5 * 100:.1f}% of 5 GB")
    print(f"   Total quota usage: {(new_uncached_egress_per_day_mb * 30 + new_cached_egress_per_day_mb * 30) / 1024 / 10 * 100:.1f}% of 10 GB combined")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
