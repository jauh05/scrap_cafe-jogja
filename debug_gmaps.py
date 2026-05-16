from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale='en-US')
    page.goto('https://www.google.com/maps/search/ARAH+Coffee+Pandawa?hl=en')
    page.wait_for_timeout(5000)
    
    tab = page.locator('[role="tab"]:has-text("Reviews")').first
    if tab.count() > 0:
        tab.click()
        page.wait_for_timeout(3000)
        
    print("Finding star elements...")
    stars = page.locator('span[aria-label*="stars"]').all()
    print(f"Found {len(stars)} star elements")
    if stars:
        # try to get the parent div that has a specific class
        el = stars[-1]
        js_code = """
        el => {
            let curr = el;
            for(let i=0; i<6; i++) {
                if(curr.parentElement) curr = curr.parentElement;
            }
            return {
                html: curr.innerHTML,
                className: curr.className
            };
        }
        """
        res = el.evaluate(js_code)
        print("CLASS NAME:", res["className"])
        print("HTML:", res["html"][:500])
        
    browser.close()
