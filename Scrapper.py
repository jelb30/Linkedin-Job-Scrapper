import os, tempfile
import random
import time
import requests
from bs4 import BeautifulSoup, SoupStrainer
import smtplib, ssl
from email.mime.text import MIMEText
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
import random
from job_keywords import KEYWORDS_LC, BLOCKED_LC
from job_filters import is_relevant_title

# ─── CONFIG ──────────────────────────────────────────────────────────
load_dotenv()

EMAIL_ADDRESS = os.getenv("JOBBOT_EMAIL")
EMAIL_PASSWORD = os.getenv("JOBBOT_APP_PASSWORD")
TO_EMAIL = os.getenv("JOBBOT_TO", EMAIL_ADDRESS)

SEEN_FILE     = "seen_jobs.txt"
ALREADY_SEEN = set()
PAGES_TO_SCRAPE = 3  # each page ~25 jobs

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
    fd, tmp = tempfile.mkstemp(prefix="seen_", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(seen)))
        os.replace(tmp, SEEN_FILE)
    finally:
        try: os.remove(tmp)
        except OSError: pass

# ─── SCRAPER ─────────────────────────────────────────────────────────
def scrape_linkedin():
    headers = {'User-Agent': 'Mozilla/5.0'}
    base = f'https://www.linkedin.com/jobs/search/?currentJobId=4248921872&f_E=1%2C2&f_JT=F%2CI&f_TPR=r3600&geoId=103644278&keywords=software%20engineer%20OR%20software%20developer%20OR%20data%20analyst%20OR%20data%20engineer%20OR%20cloud%20engineer%20OR%20devops%20engineer&location=United%20States&origin=JOB_SEARCH_PAGE_JOB_FILTER&sortBy=DD'
    results = []
    all_links = set()
    for i in range(PAGES_TO_SCRAPE):
        url = base + (f"&start={i*25}" if i else "")
        res = requests.get(url, headers=headers)
        
        soup = BeautifulSoup(res.text, 'html.parser')
        cards = soup.find_all('div', class_='base-card')
        print(f"[DEBUG] Page {i+1}: found {len(cards)} job cards")
        
        for card in cards:
            a = (card.select_one("a.base-card__full-link")
                 or card.find("a", href=lambda h: h and "/jobs/view/" in h))
            if not a:
                continue
            title = a.get_text(strip=True)
            link = a["href"].partition("?")[0]
            all_links.add(link)
            
            if link in ALREADY_SEEN:
                continue
            
            ALREADY_SEEN.add(link)
            all_links.add(link)

            loc_el = (card.select_one('span.job-search-card__location') or
                      card.select_one('span.base-search-card__location') or
                      card.find('span', class_='job-result-card__location'))
            loc = loc_el.get_text(strip=True) if loc_el else ''

            print(f"💼 {title} | {loc}\n🌐 {link}")
            
            # Case-insensitive keyword check
            title_lower = title.lower()
            if not is_relevant_title(title):
                print(f"🚫 Filtered by regex: {title}\n")
                continue
            
            results.append((title, link, loc))
            print(f"\n\n✅ ✅ Description Matched!!\n")
            
        time.sleep(0.7 + random.random() * 0.8)
        
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
        send_email("📬 New Jobs Listings", body)
        print(' ──────────────────────────────────────────────────────── SEND ────────────────────────────────────────────────────────')
        print(f"✅✅  Sent {len(new_jobs)} new jobs via email.")
    else:
        print("🔍 No new keyword-matched jobs found.")

# ─── SCHEDULE ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 LinkedIn Job Notifier is running (checks every 10 mins)...")
    while True:
        check_and_notify()
        print(' ──────────────────────────────────────────────────────── END ────────────────────────────────────────────────────────\n')
        time.sleep(300)