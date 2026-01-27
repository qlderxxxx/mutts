"""
Updated scrape_meeting_results function that:
1. Clicks through all race navigation buttons to get all races
2. Skips meetings where all SPs are $0 (invalid betting data)
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from typing import List, Dict

def scrape_meeting_results_new(meeting_url: str, meeting_name: str) -> List[Dict]:
    """
    Scrape race results from a specific meeting's results page.
    Clicks through all race navigation buttons to get results for all races.
    Skips meetings where all Starting Prices are $0.
    """
    results = []
    
    # Convert fields URL to results URL
    # e.g., /form-guides/angle-park/fields/250176/ -> /results/angle-park/250176/
    results_url = meeting_url.replace('/form-guides/', '/results/').replace('/fields/', '/')
    print(f"  [DEBUG] Transformed URL: {results_url}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            print(f"Navigating to {results_url}...")
            page.goto(results_url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            # Find race navigation items (DIVs with class meeting-events-nav__item)
            # Confirmed via debug: meeting-events-nav__item
            race_nav_items = page.query_selector_all('.meeting-events-nav__item')
            
            valid_race_links = []
            for el in race_nav_items:
                txt = el.text_content().strip()
                if txt.isdigit():
                    race_num = int(txt)
                    valid_race_links.append({
                        'number': race_num,
                        'text': txt
                    })
            
            # Sort by race number
            valid_race_links.sort(key=lambda x: x['number'])
            
            num_races = len(valid_race_links)
            print(f"Found {num_races} race buttons (class-based) for {meeting_name}: {[r['text'] for r in valid_race_links]}")
            
            if num_races == 0:
                print("  No race navigation found. Scraping single page.")
                # Just scrape current page
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                table = soup.select_one('table.results-event__table')
                
                if table:
                    race_data = parse_result_table(table, meeting_name, 1)
                    if race_data and not all_sps_zero(race_data):
                        results.append(race_data)
                    elif all_sps_zero(race_data):
                        print(f"  Skipping {meeting_name} - all SPs are $0")
                
                browser.close()
                return results
            
            # Click through each race
            all_races_have_zero_sp = True
            
            for i in range(num_races):
                try:
                    target_race = valid_race_links[i] 
                    race_num = target_race['number']
                    
                    print(f"  Processing Race {race_num}...")
                    
                    # Click button using robust class + text selector
                    # Re-querying ensures we don't use stale elements
                    selector = f".meeting-events-nav__item:text-is('{race_num}')"
                    
                    # Check if it exists/visible
                    if page.is_visible(selector):
                        page.click(selector)
                        page.wait_for_timeout(2000) # Wait for SPA update
                    else:
                        print(f"    Warning: Nav button for Race {race_num} not visible")
                        
                    # Get updated content
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    table = soup.select_one('table.results-event__table')
                    if table:
                        race_data = parse_result_table(table, meeting_name, int(race_num))
                        if race_data:
                            # Allow races with $0 SPs (User Request: "Resulted - No SPs")
                            # if not all_sps_zero(race_data):
                            all_races_have_zero_sp = False # Treat as valid
                            results.append(race_data)
                            print(f"    -> Scraped {len(race_data['results'])} runners")
                            if all_sps_zero(race_data):
                                print(f"    -> Note: Race {race_num} has all $0 SPs (Runners found)")
                
                except Exception as e:
                    print(f"  Error scraping race {i+1}: {e}")
                    continue
                

            
            browser.close()
            
            # If ALL races had $0 SPs, return empty (skip this meeting)
            if all_races_have_zero_sp and num_races > 0:
                print(f"Skipping {meeting_name} - all races have $0 SPs")
                return []
            
        except Exception as e:
            print(f"Error with Playwright for {meeting_name}: {e}")
            if 'browser' in locals():
                browser.close()
    
    return results


def parse_result_table(table, meeting_name: str, race_number: int) -> Dict:
    """Parse a single result table and return race data"""
    try:
        rows = table.select('tr')[1:]  # Skip header
        
        race_results = []
        for row in rows:
            cells = row.select('td')
            # DEBUG: Check row structure
            if len(cells) < 12:
                print(f"    Warning: Row has {len(cells)} cells (expected 12). Content: {[c.get_text(strip=True) for c in cells]}")
                continue
            
            # Extract data
            place_text = cells[0].get_text(strip=True)
            name_with_box = cells[2].get_text(strip=True)
            sp_text = cells[11].get_text(strip=True)

            # print(f"    DEBUG: Box/Name: {name_with_box} | SP Raw: {sp_text}")
            
            # Parse place
            try:
                place = int(place_text)
            except:
                continue
            
            # Extract box number
            box_match = re.search(r'\((\d+)\)', name_with_box)
            if not box_match:
                continue
            box_number = int(box_match.group(1))
            
            # Extract dog name
            dog_name = re.sub(r'\(\d+\)', '', name_with_box).strip()
            
            # Parse SP
            sp_value = None
            sp_match = re.search(r'\$?([\d.]+)', sp_text)
            if sp_match:
                try:
                    sp_value = float(sp_match.group(1))
                except:
                    pass
            
            race_results.append({
                'race_number': race_number,
                'dog_name': dog_name,
                'box_number': box_number,
                'finishing_position': place,
                'starting_price': sp_value
            })
        
        if race_results:
            return {
                'meeting_name': meeting_name,
                'race_number': race_number,
                'race_date': None, # Will be populated by caller or if passed
                'results': race_results
            }
    
    except Exception as e:
        print(f"Error parsing table for {meeting_name} R{race_number}: {e}")
    
    return None


def all_sps_zero(race_data: Dict) -> bool:
    """Check if all starting prices in a race are $0 or None"""
    if not race_data or 'results' not in race_data:
        return True
    
    for runner in race_data['results']:
        sp = runner.get('starting_price')
        if sp and sp > 0:
            return False  # Found at least one non-zero SP
    
    return True  # All SPs are 0 or None
