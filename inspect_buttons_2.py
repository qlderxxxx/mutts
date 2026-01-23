"""
Script to inspect the HTML structure of race navigation buttons - Attempt 2
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def inspect_buttons(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print(f"Navigating to {url}...")
        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(5000)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n--- Searching for 'Race Results' header ---")
        header = soup.find(string=lambda t: t and "Race Results" in t)
        if header:
            print(f"Found header: {header}")
            parent = header.parent
            print(f"Parent: {parent.name} class={parent.get('class')}")
            
            # Look at siblings / children of container
            container = parent.parent
            print(f"Container: {container.name} class={container.get('class')}")
            
            # Print structure of container
            print("\nContainer Structure:")
            print(container.prettify()[:1000]) # First 1000 chars
        else:
            print("Could not find 'Race Results' text")

        print("\n--- Inspecting 'race-nav' classes ---")
        nav_elements = soup.select('[class*="race-nav"], [class*="meeting-nav"]')
        for el in nav_elements:
             print(f"Element: {el.name} class={el.get('class')}")
             print(el.prettify()[:200])
             print("-" * 20)

        print("\n--- Inspecting elements with numbers 1-12 ---")
        # Look for the number '2' specifically, as it's likely a race button
        twos = soup.find_all(string=lambda t: t and t.strip() == "2")
        for t in twos:
            el = t.parent
            print(f"Element with '2': {el.name} class={el.get('class')}")
            # Check parents
            print(f"Parent: {el.parent.name} class={el.parent.get('class')}")
            print(f"Grandparent: {el.parent.parent.name} class={el.parent.parent.get('class')}")
            print("-" * 20)

        browser.close()

if __name__ == "__main__":
    url = "https://www.thegreyhoundrecorder.com.au/results/ascot-park/250122/"
    inspect_buttons(url)
