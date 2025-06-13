
import os
import time
import requests
from bs4 import BeautifulSoup
import smtplib, ssl
from email.mime.text import MIMEText

# ─── CONFIG ──────────────────────────────────────────────────────────
EMAIL_ADDRESS = ""
EMAIL_PASSWORD = "" #USE APP PASSWORD SETUP FOR GMAIL TO USE SMTP. 
TO_EMAIL      = ""

SEEN_FILE     = "seen_jobs.txt"
ALREADY_SEEN = []
PAGES_TO_SCRAPE = 3  # each page ~25 jobs

KEYWORDS = [
    #Job specific keywords, take full job dexcrition like Software Develper.
]

LOCATIONS = [
    #Locations to filter out jobs.
]

# ─── EMAIL ───────────────────────────────────────────────────────────
def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From']    = EMAIL_ADDRESS
    msg['To']      = TO_EMAIL
    context = ssl.create_default_context()
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as s:
        s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        s.send_message(msg)

# ─── LOAD / SAVE STATE ───────────────────────────────────────────────
def load_seen() -> set:
    return set(open(SEEN_FILE, "r").read().splitlines()) if os.path.exists(SEEN_FILE) else set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        f.write("\n".join(sorted(seen)))

# ─── SCRAPER ─────────────────────────────────────────────────────────
def scrape_linkedin():
    headers = {'User-Agent': 'Mozilla/5.0'}
    results = []
    all_links = set()
    for i in range(PAGES_TO_SCRAPE):
        url = f'https://www.linkedin.com/jobs/search/?f_E=1%2C2&f_JT=I&f_TPR=r3600&geoId=103644278&keywords=intern&location=United%20States&sortBy=DD&start={i*25}'
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        cards = soup.find_all('div', class_='base-card')
        print(f"[DEBUG] Page {i+1}: found {len(cards)} job cards")
        for card in cards:
            a = card.select_one('a.base-card__full-link')
            if not a:
                time.sleep(10)
                continue
            title = a.get_text(strip=True)
            link = a['href'].split('?')[0]
            all_links.add(link)
            
            if link in ALREADY_SEEN:
                time.sleep(10)
                continue
            
            ALREADY_SEEN.append(link)

            loc_el = (card.select_one('span.job-search-card__location') or
                      card.select_one('span.base-search-card__location') or
                      card.find('span', class_='job-result-card__location'))
            loc = loc_el.get_text(strip=True) if loc_el else ''

            print(f"💼 {title} | {loc}\n🌐 {link}")
            
            # CAN USE LOCATION FILTER HERE AS WELL FOR SPECIFIC LOCATIONS.  
            
            # Case-insensitive keyword check
            title_lower = title.lower()
            if not any(k.lower() in title_lower for k in KEYWORDS):
                print(f"🚫 Keyword filter: {title}\n")
                time.sleep(10)
                continue

            results.append((title, link, loc))
            print(f"\n\n✅ ✅ Description Matched!!\n")
            time.sleep(10)
        time.sleep(10)
    return results, all_links

# ─── MAIN CHECK ──────────────────────────────────────────────────────
def check_and_notify():
    seen = load_seen()
    new_jobs = []
    scraped_jobs, all_links = scrape_linkedin()

    for job in scraped_jobs:
        title, link, loc = job
        if link not in seen:
            new_jobs.append(job)

    # Update seen file with all unique job links seen
    seen.update(link for title, link, loc in scraped_jobs)
    save_seen(seen)

    if new_jobs:
        body = "\n\n".join([f"{t}\n{l}\nLocation: {loc}" for t, l, loc in new_jobs])
        send_email("📬 New LinkedIn Internship Listings", body)
        print(' ──────────────────────────────────────────────────────── SEND ────────────────────────────────────────────────────────')
        print(f"✅✅✅  Sent {len(new_jobs)} new jobs via email.")
        print(' ──────────────────────────────────────────────────────── SEND ────────────────────────────────────────────────────────\n')
    else:
        print("🔍 No new keyword-matched jobs found.")

# ─── SCHEDULE ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 LinkedIn Job Notifier is running (checks every 10 mins)...")
    while True:
        check_and_notify()
        print(' ──────────────────────────────────────────────────────── END ────────────────────────────────────────────────────────\n')
        time.sleep(300)