from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale='en-US')
    page.goto('https://www.google.com/maps/search/Jempolan+Coffee+%26+Eatery')
    page.wait_for_timeout(5000)
    
    print("TABS FOUND:")
    tabs = page.locator('[role="tab"]').all()
    for tab in tabs:
        try:
            print(f" - Text: {tab.inner_text()[:30]}, Aria: {tab.get_attribute('aria-label')}")
        except: pass
        
    print("\nALL BUTTONS WITH Review or Ulasan:")
    btns = page.locator('button').all()
    for btn in btns:
        try:
            text = btn.inner_text()
            aria = btn.get_attribute('aria-label')
            if ('review' in str(text).lower() or 'ulasan' in str(text).lower() or 
                'review' in str(aria).lower() or 'ulasan' in str(aria).lower()):
                print(f" - Text: {text[:30]}, Aria: {aria}")
        except: pass
        
    browser.close()
