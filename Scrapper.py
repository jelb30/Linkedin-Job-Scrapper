
import os
import time
import requests
from bs4 import BeautifulSoup
import smtplib, ssl
from email.mime.text import MIMEText

# ─── CONFIG ──────────────────────────────────────────────────────────
EMAIL_ADDRESS = "internshipnotifications7@gmail.com"
EMAIL_PASSWORD = "bbcl giix mcax nmvp"
TO_EMAIL      = "officialjelb@gmail.com"

SEEN_FILE     = "seen_jobs.txt"
PAGES_TO_SCRAPE = 1  # each page ~25 jobs

KEYWORDS = [
    "Software Developer Intern",
    "Software Developer Internship",
    "Software Development Intern",
    "Software Development Internship",
    "Software Engineer Intern",
    "Software Engineer Internship",
    "Software Eng Intern",
    "SWE Intern",
    "SWE Internship",
    "SDE Intern",
    "SDE Internship",
    "Developer Intern",
    "Developer Internship",
    "Software Dev Intern",
    "Software Dev Internship",
    "Backend Developer Intern",
    "Backend Developer Internship",
    "Intern, Software Developer",
    "Intern – Software Engineer",
    "Intern / Software Engineer",

    # — Java-specific —
    "Java Developer Intern",
    "Java Developer Internship",
    "Java Development Intern",
    "Java Development Internship",
    "Java Software Developer Intern",
    "Java Software Developer Internship",
    "Intern, Java Developer",

    # — Data Engineering & Analytics —
    "Data Engineer Intern",
    "Data Engineer Internship",
    "Data Engineering Intern",
    "Data Engineering Internship",
    "Big Data Engineer Intern",
    "Big Data Engineer Internship",
    "Data Analytics Intern",
    "Data Analytics Internship",
    "Data Analyst Intern",
    "Data Analyst Internship",
    "Data Analysis Intern",
    "Data Analysis Internship",
    "Business Intelligence Intern",
    "Business Intelligence Internship",
    "BI Developer Intern",
    "BI Developer Internship",
    "Intern, Data Engineer",
    "Intern, Data Analyst",
    "Data & Analytics Intern - Summer 2025",
    "Data & Analytics Intern",
    "Intern, Data Visualization & Analytics"

    # — Cloud & DevOps —
    "Cloud Engineer Intern",
    "Cloud Engineer Internship",
    "Cloud Engineering Intern",
    "Cloud Engineering Internship",
    "Cloud Infrastructure Intern",
    "Cloud Infrastructure Internship",
    "DevOps Intern",
    "DevOps Internship",
    "DevOps Engineer Intern",
    "DevOps Engineer Internship",
    "Cloud Operations Intern",
    "Cloud Operations Internship",
    "Intern, Cloud Engineer",

    # — Miscellaneous variants & order flips —
    "Intern – Data Analytics",
    "Intern, Data Analytics",
    "Intern / Cloud Engineering",
    "Intern: Software Dev",
    "Intern – Data Engineer",
    "Summer Software Intern",
    "Summer Data Intern",
    "Summer Cloud Intern",
    "Fall Software Intern",
    "Fall Data Intern",
    "Fall Cloud Intern"
]

US_LOCATIONS = [
    'United States','USA','US','Remote',
    'TX','CA','NY','AZ','IL','FL','WA','MA','PA','GA','OH','NC','MI','NJ','VA',
    'CO','TN','MO','IN','MD','WI','MN','SC','AL','LA','KY','OR','OK','CT','IA',
    'UT','NV','KS','NM','NE','WV','ID','HI','ME','NH','RI','MT','DE','SD','ND',
    'VT','WY','AR','MS', 'alabama','alaska','arizona','arkansas','california','colorado',
    'connecticut','delaware','florida','georgia','hawaii','idaho',
    'illinois','indiana','iowa','kansas','kentucky','louisiana','maine',
    'maryland','massachusetts','michigan','minnesota','mississippi',
    'missouri','montana','nebraska','nevada','new hampshire','new jersey',
    'new mexico','new york','north carolina','north dakota','ohio','oklahoma',
    'oregon','pennsylvania','rhode island','south carolina','south dakota',
    'tennessee','texas','utah','vermont','virginia','washington',
    'west virginia','wisconsin','wyoming',
    
    # Major cities with tech hubs
    'new york city','san francisco','seattle','austin','boston','chicago',
    'los angeles','atlanta','denver','dallas','research triangle park'
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
        url = f'https://www.linkedin.com/jobs/search/?f_E=1%2C2&f_JT=I&f_TPR=r7200&geoId=103644278&keywords=intern&location=United%20States&sortBy=DD&start={i*25}'
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        cards = soup.find_all('div', class_='base-card')
        print(f"[DEBUG] Page {i+1}: found {len(cards)} job cards")
        for card in cards:
            a = card.select_one('a.base-card__full-link')
            if not a:
                continue
            title = a.get_text(strip=True)
            link = a['href'].split('?')[0]
            all_links.add(link)

            loc_el = (card.select_one('span.job-search-card__location') or
                      card.select_one('span.base-search-card__location') or
                      card.find('span', class_='job-result-card__location'))
            loc = loc_el.get_text(strip=True) if loc_el else ''

            print(f"🔹 {title} | {loc}\n🔗 {link}")

            loc_lower = loc.strip().lower()
            if not any(loc_key in loc_lower for loc_key in US_LOCATIONS):
                print(f"🚫 Location filter: {loc}\n")
                continue
            
            # Case-insensitive keyword check
            title_lower = title.lower()
            if not any(k.lower() in title_lower for k in KEYWORDS):
                print(f"🚫 Keyword filter: {title}\n")
                continue

            results.append((title, link, loc))
            print(f"✅✅✅  Description Matched!!\n")
        time.sleep(1)
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
        print(f"✅✅✅  Sent {len(new_jobs)} new jobs via email.")
    else:
        print("🔍 No new keyword-matched jobs found.")

# ─── SCHEDULE ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 LinkedIn Job Notifier is running (checks every 10 mins)...")
    while True:
        check_and_notify()
        time.sleep(300)
