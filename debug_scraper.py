import requests
from bs4 import BeautifulSoup
import re

FORM_GUIDE_URL = "https://www.thegreyhoundrecorder.com.au/form-guides/"

def debug_scrape():
    print(f"Fetching {FORM_GUIDE_URL}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(FORM_GUIDE_URL, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    soup = BeautifulSoup(response.content, 'lxml')
    
    # Check date headers
    date_headers = soup.select('h2.meeting-list__title')
    print(f"\nFound {len(date_headers)} date headers:")
    for dh in date_headers:
        print(f" - {dh.get_text(strip=True)}")
    
    # Check meeting links
    print("\nChecking for 'Fields' links...")
    fields_links = soup.select('a.meetings__row-btn')
    print(f"Found {len(fields_links)} potential field links total.")
    
    # Test fetching a specific meeting content to check title/date parsing
    if fields_links:
        test_link = fields_links[0].get('href')
        if not test_link.startswith('http'):
            test_link = 'https://www.thegreyhoundrecorder.com.au' + test_link
            
        print(f"\nTesting specific meeting: {test_link}")
        resp2 = requests.get(test_link, headers=headers)
        soup2 = BeautifulSoup(resp2.content, 'lxml')
        title = soup2.select_one('title')
        if title:
            print(f"Page Title: '{title.get_text(strip=True)}'")
        else:
            print("No title tag found!")

if __name__ == "__main__":
    debug_scrape()
