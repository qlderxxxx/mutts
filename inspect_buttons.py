"""
Script to inspect the HTML structure of race navigation buttons.
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def inspect_buttons(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print(f"Navigating to {url}...")
        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(5000)  # Wait for full load
        
        # Get full HTML
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for the race navigation section
        # Based on screenshot, it's above the results table
        # Let's verify commonly used classes or just dump relevant sections
        
        print("\n--- Inspecting Race Navigation ---")
        
        # Try to find the container
        # Often it's in a div with class like 'race-nav', 'meeting-nav', etc.
        # Or look for the '1', '2' buttons specifically
        
        # dump all buttons to see what we have
        buttons = soup.find_all('button')
        print(f"Found {len(buttons)} total buttons on page")
        
        print("\nButtons with numbers:")
        for btn in buttons:
            text = btn.get_text(strip=True)
            if text.isdigit() and int(text) <= 15:
                print(f"Button text: '{text}' | Classes: {btn.get('class')} | Parent: {btn.parent.name} class={btn.parent.get('class')}")
                print(f"Full element: {btn}")
                print("-" * 40)

        # Also look for links that might be buttons
        links = soup.find_all('a')
        print("\nLinks with numbers:")
        for link in links:
            text = link.get_text(strip=True)
            if text.isdigit() and int(text) <= 15:
                 print(f"Link text: '{text}' | Classes: {link.get('class')} | Parent: {link.parent.name} class={link.parent.get('class')}")
                 print("-" * 40)
                 
        browser.close()

if __name__ == "__main__":
    # URL from key: Ascot Park
    url = "https://www.thegreyhoundrecorder.com.au/results/ascot-park/250122/"
    inspect_buttons(url)
