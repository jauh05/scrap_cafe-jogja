import os
import json
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

# ==========================================
# 1. SETUP STRUKTUR FOLDER PENELITIAN
# ==========================================
DIRS = ["dataset/raw", "dataset/processed", "models", "outputs/visualization", "notebooks"]

def setup_directories():
    for d in DIRS: os.makedirs(d, exist_ok=True)
    print("✅ Struktur folder penelitian Sinta 1 siap.")

# ==========================================
# 2. DEFINISI ASPEK (UNTUK TABLE 3: ABSA)
# ==========================================
ASPECT_KEYWORDS = {
    'coffee_quality': ['kopi', 'latte', 'espresso', 'rasa', 'beans', 'manual brew', 'pahit', 'enak', 'cappuccino', 'americano'],
    'ambience': ['nyaman', 'aesthetic', 'suasana', 'dingin', 'ac', 'vibe', 'betah', 'dekorasi', 'tempat'],
    'service': ['pelayanan', 'barista', 'ramah', 'cepat', 'sopan', 'pelayan', 'kasir'],
    'price': ['mahal', 'murah', 'terjangkau', 'harga', 'worth it', 'kantong', 'pricey'],
    'wifi': ['wifi', 'internet', 'kencang', 'lemot', 'koneksi', 'colokan', 'stopkontak'],
    'parking': ['parkir', 'sempit', 'luas', 'motor', 'mobil', 'lahan', 'tukang parkir'],
    'cleanliness': ['bersih', 'kotor', 'toilet', 'wangi', 'rapi', 'meja'],
    'food_quality': ['makanan', 'camilan', 'snack', 'roti', 'nasi', 'lezat', 'menu'],
    'music': ['musik', 'lagu', 'playlist', 'bising', 'kencang', 'berisik'],
    'waiting_time': ['lama', 'antre', 'cepat', 'nunggu', 'penyajian']
}

def extract_absa_labels(review_text, review_id):
    labels = []
    text_lower = review_text.lower()
    for aspect, keywords in ASPECT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            sentiment = 'positive' if any(pos in text_lower for pos in ['enak', 'nyaman', 'bagus', 'cepat', 'ramah', 'bersih', 'murah', 'luas']) else 'negative'
            labels.append({
                "absa_id": f"AB{int(time.time()*1000000) % 1000000000}", 
                "review_id": review_id,
                "aspect": aspect,
                "sentiment": sentiment,
                "confidence_score": 0.85
            })
    return labels

# ==========================================
# 3. CORE SCRAPER ENGINE
# ==========================================
def run_research_scraper(queries, max_cafes=300, reviews_per_cafe=50):
    cafes_data, reviews_data, absa_data = [], [], []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        # Menggunakan locale en-US agar text selector (seperti "Reviews") konsisten tidak berubah bahasa
        context = browser.new_context(viewport={'width': 1280, 'height': 800}, locale='en-US')
        page = context.new_page()

        cafe_count = 0
        for query in queries:
            if cafe_count >= max_cafes: break
            print(f"\n🔎 Melakukan Crawling Wilayah: {query}")
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl=en"
            page.goto(search_url)
            page.wait_for_timeout(5000)

            # Scroll list hasil pencarian cafe
            for _ in range(6): 
                page.mouse.wheel(0, 5000)
                page.wait_for_timeout(1500)

            cafe_links = page.locator('a[href*="/maps/place/"]').all()
            print(f"📍 Ditemukan {len(cafe_links)} potensi tempat dari query ini.")

            for link in cafe_links:
                if cafe_count >= max_cafes: break
                try:
                    # Klik cafe untuk buka panel detail
                    link.click()
                    page.wait_for_timeout(3000)
                    
                    # 1. Scraping Master Data Cafe (TABLE 1)
                    name_el = page.locator('h1.DUwDvf').first
                    name = name_el.inner_text() if name_el.count() > 0 else "N/A"
                    if name == "N/A" or "Result" in name or "Hasil" in name:
                        continue # Skip invalid
                        
                    rating_el = page.locator('div.F7B36e').first
                    rating = rating_el.inner_text() if rating_el.count() > 0 else "0"
                    
                    address_el = page.locator('button[data-item-id="address"]').first
                    address = address_el.inner_text() if address_el.count() > 0 else "Jogja"
                    
                    cafe_id = f"CF{cafe_count+1:04d}"
                    cafes_data.append({
                        "cafe_id": cafe_id, "cafe_name": name, "district": query.split()[-1], "address": address,
                        "latitude": page.url.split('!3d')[1].split('!4d')[0] if '!3d' in page.url else 0,
                        "longitude": page.url.split('!4d')[1].split('!16s')[0] if '!4d' in page.url else 0,
                        "avg_rating": rating, "total_reviews": reviews_per_cafe, "maps_url": page.url
                    })
                    print(f"☕ [{cafe_id}] {name} berhasil didata.")

                    # 2. Masuk ke Tab Review (TABLE 2)
                    # Karena URL di set ke ?hl=en, tab akan berbahasa Inggris "Reviews"
                    review_tab = page.locator('[role="tab"]:has-text("Reviews")').first
                    if review_tab.count() == 0:
                        review_tab = page.locator('[role="tab"]:has-text("Ulasan")').first
                        
                    if review_tab.count() > 0:
                        review_tab.click()
                        page.wait_for_timeout(3000) # Tunggu loading tab review
                    else:
                        # Fallback: Terkadang Google Maps tidak punya tab 'Reviews',
                        # tapi punya tombol ber-label '... reviews' di halaman ringkasan.
                        review_btn = page.locator('button[aria-label*="reviews"]').first
                        if review_btn.count() == 0:
                            review_btn = page.locator('button[aria-label*="ulasan"]').first
                        if review_btn.count() > 0:
                            review_btn.click()
                            page.wait_for_timeout(3000)
                        
                        
                    # LOGIKA SCROLLING YANG LEBIH PASTI: 
                    # Cari review terakhir dan paksa browser scroll ke elemen tersebut
                    for _ in range(8): # Lakukan scroll beberapa kali
                        reviews = page.locator('div[data-review-id]')
                        if reviews.count() > 0:
                            try:
                                reviews.last.scroll_into_view_if_needed()
                                page.wait_for_timeout(1500)
                            except:
                                pass
                        else:
                            # Fallback scroll dengan mouse jika selector ID tidak ketemu
                            page.mouse.move(300, 400) 
                            page.mouse.wheel(0, 5000)
                            page.wait_for_timeout(1000)
                        
                        # Klik tombol "More" / "Lainnya" untuk ekspansi text review yang panjang
                        more_btns = page.locator('button:has-text("More")').all() + page.locator('button:has-text("Lainnya")').all()
                        for btn in more_btns:
                            try: btn.click(); page.wait_for_timeout(300)
                            except: pass

                        # Ekstraksi review item
                        raw_reviews = page.locator('div[data-review-id]').all()
                        if not raw_reviews:
                            raw_reviews = page.locator('.jftiEf').all() # Fallback class Google Maps
                            
                        extracted_this_cafe = 0
                        for rev in raw_reviews:
                            if extracted_this_cafe >= reviews_per_cafe: break
                            
                            # Ekstrak text
                            rev_text_el = rev.locator('.wi9C4c')
                            if rev_text_el.count() == 0: rev_text_el = rev.locator('.MyEned')
                            
                            rev_text = rev_text_el.first.inner_text() if rev_text_el.count() > 0 else ""
                            if len(rev_text) < 10: continue # Skip review kosong
                            
                            # Ekstraksi rating
                            stars_el = rev.locator('span[role="img"]').first
                            star_text = stars_el.get_attribute('aria-label') if stars_el.count() > 0 else ""
                            user_rating = 5
                            if star_text:
                                try:
                                    user_rating = int(''.join(filter(str.isdigit, star_text.split()[0])))
                                except: pass
                            
                            rev_id = f"RV{len(reviews_data)+1:06d}"
                            rev_entry = {
                                "review_id": rev_id, "cafe_id": cafe_id, "review_text": rev_text,
                                "review_rating": user_rating, "review_date": datetime.now().strftime("%Y-%m-%d"), "language": "id"
                            }
                            reviews_data.append(rev_entry)
                            extracted_this_cafe += 1
                            
                            # 3. Ekstraksi Aspek ABSA
                            absa_labels = extract_absa_labels(rev_text, rev_id)
                            absa_data.extend(absa_labels)
                            
                        print(f"   => Terambil {extracted_this_cafe} review untuk cafe ini.")
                    else:
                        print("   => ⚠️ Tab Review tidak ditemukan.")

                    cafe_count += 1
                except Exception as e: 
                    # print(f"Error pada item: {e}")
                    continue

        browser.close()
    return cafes_data, reviews_data, absa_data

# ==========================================
# 4. EXPORT ENGINE
# ==========================================
def save_research_dataset(cafes, reviews, absa):
    print("\n💾 Menyimpan Dataset Penelitian...")
    df1, df2, df3 = pd.DataFrame(cafes), pd.DataFrame(reviews), pd.DataFrame(absa)
    
    df1.to_csv('dataset/processed/coffee_shops.csv', index=False)
    if len(df2) > 0: df2.to_csv('dataset/processed/reviews_clean.csv', index=False)
    if len(df3) > 0: df3.to_csv('dataset/processed/absa_labels.csv', index=False)
    
    with pd.ExcelWriter('dataset/processed/RESEARCH_DATASET_FINAL.xlsx') as writer:
        df1.to_excel(writer, sheet_name='1_Coffee_Shops', index=False)
        if len(df2) > 0: df2.to_excel(writer, sheet_name='2_Reviews_NLP', index=False)
        if len(df3) > 0: df3.to_excel(writer, sheet_name='3_ABSA_Labels', index=False)
    
    print(f"✅ DATASET SELESAI!")
    print(f"📊 Cafe: {len(df1)} | Review: {len(df2)} | ABSA Records: {len(df3)}")

if __name__ == "__main__":
    setup_directories()
    
    # === MODE PERCOBAAN (TESTING 1 DATA) ===
    # Hanya menggunakan 1 kata kunci untuk testing
    queries = [
        "coffee shop depok sleman"
    ]
    
    # Jalankan Scraper (Target: 1 Cafe, @ 10 Review per cafe)
    print("\n⚠️ MENJALANKAN MODE PERCOBAAN (TESTING 1 CAFE)...")
    c, r, a = run_research_scraper(queries, max_cafes=1, reviews_per_cafe=10)
    save_research_dataset(c, r, a)
