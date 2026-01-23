from playwright.sync_api import sync_playwright

def inspect_links():
    target_url = "https://www.thegreyhoundrecorder.com.au/results/?date=2026-01-22"
    print(f"Inspecting: {target_url}")
    
    with sync_playwright() as p:
        # Launch browser in HEADED mode (matches scraper.py)
        browser = p.chromium.launch(
            headless=False, 
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--start-maximized'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='en-AU',
            timezone_id='Australia/Sydney'
        )
        
        page = context.new_page()
        
        # Stealth scripts
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page.add_init_script("window.chrome = { runtime: {} }")
        
        print("Navigating...")
        # Go to home first
        page.goto("https://www.thegreyhoundrecorder.com.au", timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        
        # Go to target
        page.goto(target_url, timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(5000) # Wait for JS content
        
        page.screenshot(path="debug_results_page.png")
        print("Draft saved to debug_results_page.png")
        
        # Select all links generally slightly better debug
        links = page.query_selector_all('a')
        print(f"Found {len(links)} total links on page")
        
        for link in links:
            href = link.get_attribute('href')
            if href:
                # Filter to likely relevant ones
                if 'results' in href or 'form-guides' in href or 'fields' in href:
                    text = link.text_content().strip().replace('\n', ' ')
                    print(f"  Relevant Link: {text[:40]}... -> {href}")
            
        browser.close()

if __name__ == "__main__":
    inspect_links()
