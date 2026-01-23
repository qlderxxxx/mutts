#!/usr/bin/env python3
"""
Test the results scraping functionality
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from scraper import scrape_meeting_results, update_race_results

# Test with Angle Park from today (which has results)
meeting_url = "https://www.thegreyhoundrecorder.com.au/form-guides/angle-park/fields/250176/"
meeting_name = "Angle Park"

print("=" * 60)
print("Testing Results Scraper")
print("=" * 60)

# Scrape results
print(f"\nScraping results for {meeting_name}...")
results = scrape_meeting_results(meeting_url, meeting_name)

print(f"\nFound {len(results)} races with results")

# Display results
for race_result in results:
    print(f"\n{race_result['meeting_name']} R{race_result['race_number']}:")
    for runner in race_result['results']:
        print(f"  {runner['finishing_position']}. {runner['dog_name']} (Box {runner['box_number']}) - SP: ${runner['starting_price']}")
    
    # Calculate Top 2 in Top 2
    sorted_by_sp = sorted([r for r in race_result['results'] if r['starting_price'] is not None], 
                          key=lambda x: x['starting_price'])
    if len(sorted_by_sp) >= 2:
        top_2_favorites = {sorted_by_sp[0]['box_number'], sorted_by_sp[1]['box_number']}
        sorted_by_position = sorted(race_result['results'], key=lambda x: x['finishing_position'])
        if len(sorted_by_position) >= 2:
            top_2_finishers = {sorted_by_position[0]['box_number'], sorted_by_position[1]['box_number']}
            top_2_in_top_2 = top_2_favorites == top_2_finishers
            print(f"  Top 2 favorites: Boxes {sorted(top_2_favorites)}")
            print(f"  Top 2 finishers: Boxes {sorted(top_2_finishers)}")
            print(f"  Top 2 in Top 2? {top_2_in_top_2}")

# Test database update (only if results found)
if results:
    print(f"\n\nTesting database update for first race...")
    update_race_results(results[0])
    print("Database update test complete!")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
