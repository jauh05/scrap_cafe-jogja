from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale='en-US')
    page.goto('https://www.google.com/maps/search/Jempolan+Coffee+%26+Eatery?hl=en')
    page.wait_for_timeout(3000)
    
    links = page.locator('a[href*="/maps/place/"]').all()
    if links:
        links[0].click()
        page.wait_for_timeout(3000)
        
    name_el = page.locator('h1.DUwDvf').first
    if name_el.count() > 0:
        name_el.focus()
        print("Focused on H1")
        for _ in range(15):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(500)
            
    reviews = page.locator('div[data-review-id]').all()
    print(f"FOUND {len(reviews)} REVIEWS")
    browser.close()
