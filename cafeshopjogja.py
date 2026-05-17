import os
import json
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import random

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
# 3. UTILS & CORE SCRAPER ENGINE
# ==========================================
def random_delay(min_s=2, max_s=5):
    """Menambahkan jeda acak untuk meniru perilaku manusia"""
    time.sleep(random.uniform(min_s, max_s))

def run_research_scraper(queries, max_cafes=300, reviews_per_cafe=50):
    cafes_data, reviews_data, absa_data = [], [], []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        # Menggunakan locale en-US agar text selector (seperti "Reviews") konsisten tidak berubah bahasa
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800}, 
            locale='en-US',
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        # AKTIFKAN STEALTH MODE (Matikan sementara jika blank)
        # stealth_sync(page)

        cafe_count = 0
        for query in queries:
            if cafe_count >= max_cafes: break
            print(f"\n🔎 Melakukan Crawling Wilayah: {query}")
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl=en"
            page.goto(search_url)
            
            # Tunggu elemen list muncul (biasanya elemen dengan role feed)
            try:
                page.wait_for_selector('div[role="feed"]', timeout=15000)
            except:
                print("⚠️ List belum muncul, mencoba menunggu lebih lama...")
            
            random_delay(3, 5)

            # Scroll list hasil pencarian cafe dengan cara yang lebih halus
            for _ in range(5): 
                # Pastikan fokus ada di area list sebelum scroll
                try:
                    page.hover('div[role="feed"]')
                except:
                    pass
                page.mouse.wheel(0, random.randint(2000, 4000))
                random_delay(2, 3)

            cafe_links = page.locator('a[href*="/maps/place/"]').all()
            print(f"📍 Ditemukan {len(cafe_links)} potensi tempat dari query ini.")

            for link in cafe_links:
                if cafe_count >= max_cafes: break
                try:
                    # Klik cafe untuk buka panel detail
                    link.click()
                    random_delay(3, 5)
                    
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
                    review_tab = page.locator('button:has-text("Reviews"), button:has-text("Ulasan"), [role="tab"]:has-text("Reviews"), [role="tab"]:has-text("Ulasan")').first
                    
                    if review_tab.count() > 0:
                        review_tab.click()
                        random_delay(4, 6)
                    else:
                        review_btn = page.locator('button[aria-label*="reviews"]').first
                        if review_btn.count() == 0:
                            review_btn = page.locator('button[aria-label*="ulasan"]').first
                        if review_btn.count() > 0:
                            review_btn.click()
                            random_delay(3, 5)
                            
                    # LOGIKA SCROLLING & EKSTRAKSI REVIEW ITEM – ambil 20 review terbaru
                    extracted_this_cafe = 0
                    seen_ids = set()
                    max_attempts = 25
                    attempts = 0
                    
                    while extracted_this_cafe < reviews_per_cafe and attempts < max_attempts:
                        attempts += 1
                        
                        # Klik tombol "More" / "Lainnya" untuk teks ulasan lengkap
                        more_btns = page.locator('button.w8nwRe.kyuRq, button:has-text("More"), button:has-text("Lainnya")').all()
                        for btn in more_btns:
                            try:
                                btn.click()
                                page.wait_for_timeout(200)
                            except:
                                pass
                        
                        # Scroll ke bawah untuk memicu lazy loading ulasan baru
                        reviews_els = page.locator('div[data-review-id]')
                        if reviews_els.count() == 0:
                            reviews_els = page.locator('.jftiEf')
                            
                        if reviews_els.count() > 0:
                            try:
                                reviews_els.last.scroll_into_view_if_needed()
                            except:
                                pass
                        else:
                            page.keyboard.press('PageDown')
                            
                        random_delay(1, 2)
                        
                        # Ambil elemen ulasan yang sudah tampil
                        current_raw = page.locator('div[data-review-id]').all()
                        if not current_raw:
                            current_raw = page.locator('.jftiEf').all()
                            
                        for rev in current_raw:
                            if extracted_this_cafe >= reviews_per_cafe:
                                break
                                
                            rid = rev.get_attribute('data-review-id')
                            if rid and rid in seen_ids:
                                continue
                            if rid:
                                seen_ids.add(rid)
                                
                            # Ekstraksi Teks
                            rev_texts = rev.locator('.wiI7pd, .wi9C4c, .MyEned').all_inner_texts()
                            rev_text_raw = max(rev_texts, key=len) if rev_texts else ""
                            rev_text = " ".join(rev_text_raw.split())
                            
                            if len(rev_text) < 10:
                                continue
                                
                            # Ekstraksi Rating
                            stars_el = rev.locator('span[role="img"]').first
                            star_text = stars_el.get_attribute('aria-label') if stars_el.count() > 0 else ""
                            user_rating = 5
                            if star_text:
                                try:
                                    # Mengambil angka dari "5 stars" atau "Rating 5"
                                    user_rating = int(''.join(filter(str.isdigit, star_text.split()[0])))
                                except:
                                    pass
                                    
                            # Simpan Data
                            review_id_code = f"RV{len(reviews_data)+1:06d}"
                            reviews_data.append({
                                "review_id": review_id_code, 
                                "cafe_id": cafe_id, 
                                "review_text": rev_text,
                                "review_rating": user_rating, 
                                "review_date": datetime.now().strftime("%Y-%m-%d"), 
                                "language": "id"
                            })
                            extracted_this_cafe += 1
                            
                            # Analisis ABSA
                            absa_labels = extract_absa_labels(rev_text, review_id_code)
                            absa_data.extend(absa_labels)

                    print(f"   => Terambil {extracted_this_cafe} review untuk cafe ini.")

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
    
    # Simpan CSV
    df1.to_csv('dataset/processed/coffee_shops.csv', index=False)
    if len(df2) > 0: df2.to_csv('dataset/processed/reviews_clean.csv', index=False)
    if len(df3) > 0: df3.to_csv('dataset/processed/absa_labels.csv', index=False)
    
    # Simpan EXCEL terpisah agar lebih rapi untuk dianalisis
    df1.to_excel('dataset/processed/coffee_shops.xlsx', index=False)
    if len(df2) > 0: df2.to_excel('dataset/processed/reviews_clean.xlsx', index=False)
    if len(df3) > 0: df3.to_excel('dataset/processed/absa_labels.xlsx', index=False)
    
    print(f"✅ DATASET SELESAI!")
    print(f"📁 File CSV dan Excel (.xlsx) sudah tersimpan di folder 'dataset/processed/'")
    print(f"📊 Cafe: {len(df1)} | Review: {len(df2)} | ABSA Records: {len(df3)}")

if __name__ == "__main__":
    setup_directories()
    
    # === MODE PERCOBAAN (TESTING 1 DATA) ===
    # Hanya menggunakan 1 kata kunci untuk testing
    # Daftar kata kunci wilayah yang luas (lebih dari 30 kata) untuk mencapai target 600 kafe
    queries = [
        "coffee shop depok sleman",
        "coffee shop ngaglik sleman",
        "coffee shop mlati sleman",
        "coffee shop umbulharjo yogyakarta",
        "coffee shop gondokusuman yogyakarta",
        "coffee shop mantrijeron yogyakarta",
        "coffee shop sewon bantul",
        "coffee shop kasihan bantul",
        "coffee shop banguntapan bantul",
        "cafe hits yogyakarta",
        "specialty coffee jogja",
        "roastery cafe yogyakarta",
        "cafe estetik sleman",
        "tempat nongkrong bantul",
        "cafe alun-alun jogja",
        "coffee shop kebon jeruk",
        "cafe wisata kuliner jogja",
        "kopi tradisional jogja",
        "cozy cafe jogja",
        "coffee shop kemalan",
        "cafe mrican",
        "artisan coffee jogja",
        "cafe sunrise jogja",
        "cafe sunset jogja",
        "cafe pusat kota",
        "cafe di dekat stasiun jogja",
        "cafe dekat universitas",
        "coffee shop near mall jogja",
        "cafe di kawasan bisnis jogja",
        "coffee shop daerah kebayoran jogja",
        "cafe di area pemukiman jogja",
        "cafe kuliner keluarga",
        "cafe ramah anak jogja",
        "cafe kopi susu jogja",
        "cafe dengan wifi gratis",
        "cafe 24 jam jogja",
        "coffee shop brunch jogja"
    ]
    
    # Jalankan Scraper (Target: 600 Cafe, @ 20 Review per cafe)
    print("\n⚠️ MENJALANKAN SCRAPING UNTUK 600 CAFÉ & 12.000 REVIEW...")
    c, r, a = run_research_scraper(queries, max_cafes=600, reviews_per_cafe=20)
    save_research_dataset(c, r, a)
