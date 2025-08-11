import os
import tempfile
import random
import time
import requests
from bs4 import BeautifulSoup
import smtplib, ssl
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime

from job_filters import is_relevant_title  # your regex-based filter

# ─── CONFIG ──────────────────────────────────────────────────────────
load_dotenv()

EMAIL_ADDRESS = os.getenv("JOBBOT_EMAIL")
EMAIL_PASSWORD = os.getenv("JOBBOT_APP_PASSWORD")
TO_EMAIL = os.getenv("JOBBOT_TO", EMAIL_ADDRESS)

SEEN_FILE = "seen_jobs.txt"
ALREADY_SEEN = set()
PAGES_TO_SCRAPE = 3                   # ~25 jobs per page
CHECK_INTERVAL_SECONDS = 300          # 5 minutes

# ─── PRINT HELPERS (no logging module; terminal prints only) ─────────
def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def info(msg):  print(f"[{_ts()}] INFO  {msg}")
def warn(msg):  print(f"[{_ts()}] WARN  {msg}")
def error(msg): print(f"[{_ts()}] ERROR {msg}")

def print_job_match(title, company, loc, link):
    print(
        "\n"
        "──────────────────────────────────────────────────────────────────────────────\n"
        f"Title   : {title}\n"
        f"Company : {company or '-'}\n"
        f"Location: {loc or '-'}\n"
        f"Link    : {link}\n"
        "──────────────────────────────────────────────────────────────────────────────"
    )

# ─── EMAIL ───────────────────────────────────────────────────────────
def send_email(subject, body):
    context = ssl.create_default_context()
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_EMAIL

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.send_message(msg)

        info(f"Email sent | subject='{subject}' | to={TO_EMAIL} | bytes={len(body.encode('utf-8'))}")
    except Exception as e:
        error(f"❌ Email failed | reason={e}")

# ─── LOAD / SAVE STATE ───────────────────────────────────────────────
def load_seen() -> set:
    if not os.path.exists(SEEN_FILE):
        info("Seen file not found; starting fresh.")
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            seen = set(f.read().splitlines())
        info(f"Loaded seen set | count={len(seen)}")
        return seen
    except Exception as e:
        warn(f"Failed to read seen file; continuing with empty set. reason={e}")
        return set()

def save_seen(seen: set):
    fd, tmp = tempfile.mkstemp(prefix="seen_", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(seen)))
        os.replace(tmp, SEEN_FILE)
        info(f"Saved seen set | count={len(seen)}")
    except Exception as e:
        warn(f"Failed to save seen file. reason={e}")
    finally:
        try: os.remove(tmp)
        except OSError: pass

# ─── SCRAPER ─────────────────────────────────────────────────────────
def scrape_linkedin():
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Full-time only (no internships), Entry/Associate, last 24h
    base = (
        "https://www.linkedin.com/jobs/search/"
        "?f_JT=F&f_E=1%2C2&f_TPR=r86400"
        "&geoId=103644278"
        "&keywords=software%20engineer%20OR%20software%20developer%20OR%20data%20analyst%20OR%20data%20engineer%20OR%20cloud%20engineer%20OR%20devops%20engineer"
        "&location=United%20States&origin=JOB_SEARCH_PAGE_JOB_FILTER&sortBy=DD"
    )

    results = []
    all_links = set()

    for i in range(PAGES_TO_SCRAPE):
        url = base + (f"&start={i*25}" if i else "")
        try:
            res = requests.get(url, headers=headers, timeout=(5, 30))
            res.raise_for_status()
        except requests.RequestException as e:
            warn(f"⚠️ Page {i+1}: request failed. reason={e}")
            time.sleep(1.0 + random.random())
            continue

        soup = BeautifulSoup(res.text, 'html.parser')
        cards = soup.find_all('div', class_='base-card')
        info(f"Page {i+1}: parsed {len(cards)} job cards.")

        for card in cards:
            a = (card.select_one("a.base-card__full-link")
                 or card.find("a", href=lambda h: h and "/jobs/view/" in h))
            if not a:
                continue

            title = a.get_text(strip=True)
            link = a["href"].partition("?")[0]

            if link in ALREADY_SEEN:
                continue
            ALREADY_SEEN.add(link)
            all_links.add(link)

            loc_el = (card.select_one('span.job-search-card__location')
                      or card.select_one('span.base-search-card__location')
                      or card.find('span', class_='job-result-card__location'))
            loc = loc_el.get_text(strip=True) if loc_el else ''

            comp_el = (card.select_one('h4.base-search-card__subtitle')
                       or card.select_one('h3.base-search-card__subtitle'))
            company = comp_el.get_text(strip=True) if comp_el else ''

            # Regex-based title filter (intern/co-op/senior excluded inside job_filters)
            if not is_relevant_title(title):
                continue

            # Print only accepted matches
            print_job_match(title, company, loc, link)
            results.append((title, link, loc))

        time.sleep(0.7 + random.random() * 0.8)

    info(f"Scrape complete | accepted={len(results)} | discovered_links={len(all_links)}")
    return results, all_links

# ─── MAIN CHECK ──────────────────────────────────────────────────────
def check_and_notify():
    info("Cycle start.")
    seen = load_seen()

    new_jobs = []
    scraped_jobs, _ = scrape_linkedin()

    for title, link, loc in scraped_jobs:
        if link not in seen:
            new_jobs.append((title, link, loc))

    # Update seen file with all unique job links we just processed
    seen.update(link for _, link, _ in scraped_jobs)
    save_seen(seen)

    if new_jobs:
        body = "\n\n".join([f"{t}\n{l}\nLocation: {loc}" for t, l, loc in new_jobs])
        send_email("📬 New Job Listings", body)
        info(f"📬 Email sent | new_jobs={len(new_jobs)}")
    else:
        info("No new matches this cycle.")

    info("Cycle end.\n")

# ─── SCHEDULE ────────────────────────────────────────────────────────
if __name__ == "__main__":
    info("🚀 LinkedIn Job Notifier starting | interval={CHECK_INTERVAL_SECONDS}s | pages={PAGES_TO_SCRAPE}")
    while True:
        try:
            check_and_notify()
        except Exception as e:
            error(f"Unhandled error in cycle. reason={e}")
        time.sleep(CHECK_INTERVAL_SECONDS)
