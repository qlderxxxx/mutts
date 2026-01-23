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
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            print(f"Navigating to {results_url}...")
            page.goto(results_url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            # Find all race navigation buttons
            # The buttons are in a navigation area and numbered (1, 2, 3, etc.)
            all_buttons = page.query_selector_all('button')
            race_buttons = [btn for btn in all_buttons if btn.text_content() and btn.text_content().strip().isdigit()]
            
            num_races = len(race_buttons)
            print(f"Found {num_races} race buttons for {meeting_name}")
            
            if num_races == 0:
                # No race buttons, just scrape current page
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
            
            # Click through each race button
            all_races_have_zero_sp = True
            
            for i in range(num_races):
                try:
                    # Re-query buttons (DOM might update)
                    current_buttons = page.query_selector_all('button')
                    current_race_buttons = [btn for btn in current_buttons if btn.text_content() and btn.text_content().strip().isdigit()]
                    
                    if i < len(current_race_buttons):
                        race_num = current_race_buttons[i].text_content().strip()
                        print(f"  Clicking race {race_num}...")
                        
                        current_race_buttons[i].click()
                        page.wait_for_timeout(1500)
                        
                        # Get updated content
                        html = page.content()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        table = soup.select_one('table.results-event__table')
                        if table:
                            race_data = parse_result_table(table, meeting_name, int(race_num))
                            if race_data:
                                if not all_sps_zero(race_data):
                                    all_races_have_zero_sp = False
                                    results.append(race_data)
                                    print(f"    -> Scraped {len(race_data['results'])} runners")
                                else:
                                    print(f"    -> Race {race_num} has all $0 SPs, skipping")
                
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
            if len(cells) < 12:
                continue
            
            # Extract data
            place_text = cells[0].get_text(strip=True)
            name_with_box = cells[2].get_text(strip=True)
            sp_text = cells[11].get_text(strip=True)
            
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
