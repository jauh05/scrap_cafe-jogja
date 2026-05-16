from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale='en-US')
    page.goto('https://www.google.com/maps/search/Carani+Coffee+%26+Eatery?hl=en')
    page.wait_for_timeout(5000)
    
    tab = page.locator('[role="tab"]:has-text("Reviews")').first
    if tab.count() > 0:
        tab.click()
        page.wait_for_timeout(3000)
        
    reviews = page.locator('.jftiEf').all()
    print(f"FOUND {len(reviews)} REVIEWS using .jftiEf")
    
    if len(reviews) == 0:
        reviews = page.locator('div[data-review-id]').all()
        print(f"FOUND {len(reviews)} REVIEWS using div[data-review-id]")
        
    browser.close()
