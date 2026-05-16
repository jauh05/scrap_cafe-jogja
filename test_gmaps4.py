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
        
    print("Clicking rating...")
    rating_el = page.locator('div.F7B36e').first
    if rating_el.count() > 0:
        rating_el.click()
        page.wait_for_timeout(3000)
        
    reviews = page.locator('div[data-review-id]').all()
    print(f"FOUND {len(reviews)} REVIEWS")
    
    # Try scrolling
    for _ in range(5):
        if len(page.locator('div[data-review-id]').all()) > 0:
            page.locator('div[data-review-id]').last.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            
    reviews = page.locator('div[data-review-id]').all()
    print(f"FOUND {len(reviews)} REVIEWS AFTER SCROLL")
    browser.close()
