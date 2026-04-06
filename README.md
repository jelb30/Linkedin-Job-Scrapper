# LinkedIn and ATS Job Scrapers

Local Python scrapers for finding recent software, data, infrastructure, and SRE jobs and emailing new matches.

This project has two main sources:

- LinkedIn search pages
- Direct ATS job boards such as Greenhouse, Ashby, Lever, SmartRecruiters, and Workable

It is built for local use first. Run it on your Mac, keep a local seen-job history, and get emailed only new matches.

## What It Does

- Scrapes LinkedIn job search results for fresh full-time roles
- Polls configured ATS company boards directly
- Filters out reposted and promoted LinkedIn jobs
- Filters out agencies, staffing firms, and low-signal aggregator postings
- Focuses on software engineering, data, platform, cloud, DevOps, and SRE-style roles
- Tracks seen links and job signatures so you do not get the same job repeatedly
- Emails only newly discovered matches

## How It Works

### LinkedIn flow

`FinalScrapper.py` and `FinalScrapperIndia.py` use the shared LinkedIn collector in `jobnotifier/job_sources.py`.

The LinkedIn runner:

1. Builds a search URL with your configured keywords and freshness window
2. Downloads the search-result pages
3. Extracts title, company, location, and link from each job card
4. Rejects reposted or promoted cards
5. Applies title, company, and location filters
6. Deduplicates results
7. Compares them against local seen-job files
8. Emails only jobs that have not been sent before

### ATS flow

`ATSScrapper.py` and `ATSScrapperIndia.py` use the direct ATS collectors in `jobnotifier/job_sources.py`.

The ATS runner:

1. Loads target companies and board slugs from `config/ats_targets.json`
2. Calls the public job-board endpoints for each configured ATS
3. Parses raw jobs into one shared internal format
4. Applies freshness, title, company, and location filters
5. Tracks repeated 404 targets and stops retrying permanently bad slugs after the configured threshold
6. Deduplicates and compares against local seen-job files
7. Emails only new jobs

## Project Layout

```text
.
├── jobnotifier/
│   ├── job_filters.py
│   ├── job_runtime.py
│   ├── job_sources.py
│   ├── linkedin_runner.py
│   ├── linkedin_india_runner.py
│   ├── ats_runner.py
│   └── ats_india_runner.py
├── config/
│   ├── ats_targets.json
│   └── examples/
│       └── ats_targets.example.json
├── data/
│   └── state/
├── FinalScrapper.py
├── FinalScrapperIndia.py
├── ATSScrapper.py
├── ATSScrapperIndia.py
├── requirements.txt
└── .env.example
```

## Why There Are Root Files And `jobnotifier/`

The root files are small launchers so you can run:

- `python3 FinalScrapper.py`
- `python3 ATSScrapper.py`
- `python3 FinalScrapperIndia.py`
- `python3 ATSScrapperIndia.py`

The real shared logic lives in `jobnotifier/`. That keeps the code maintainable and avoids copying the same filtering, emailing, deduping, and parsing logic into four separate scripts.

## Supported Runners

### US / North America

- `FinalScrapper.py`
- `ATSScrapper.py`

### India

- `FinalScrapperIndia.py`
- `ATSScrapperIndia.py`

The US/North America scripts are the default path. The India scripts are separate so you do not need to pass runtime flags just to switch markets.

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/jelb30/Linkedin-Job-Scrapper.git
cd Linkedin-Job-Scrapper
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 4. Create your `.env`

```bash
cp .env.example .env
```

Then fill in at least:

- `EMAIL_USER`
- `EMAIL_PASS`
- `EMAIL_TO`

### 5. Configure ATS targets

Edit:

- `config/ats_targets.json`

This file controls which company ATS boards are checked. The ATS scraper does not magically scan every company on the internet. It only checks the boards you list there.

## Environment Variables

Common settings in `.env`:

- `EMAIL_USER`: sender Gmail address
- `EMAIL_PASS`: Gmail app password
- `EMAIL_TO`: recipient email address
- `EMAIL_TO_AS`: optional second recipient
- `LINKEDIN_PAGES_TO_SCRAPE`: number of LinkedIn result pages per cycle
- `CHECK_INTERVAL_SECONDS`: LinkedIn polling interval
- `LINKEDIN_MAX_AGE_SECONDS`: LinkedIn freshness window
- `ATS_CHECK_INTERVAL_SECONDS`: ATS polling interval
- `ATS_MAX_AGE_HOURS`: ATS freshness window
- `ATS_INVALID_TARGET_THRESHOLD`: number of repeated 404s before a bad ATS target is skipped

## How To Run

### One-time test run

Use this when you want to verify scraping, filters, and email without leaving the process running.

```bash
python3 FinalScrapper.py --run-once
python3 ATSScrapper.py --run-once
python3 FinalScrapperIndia.py --run-once
python3 ATSScrapperIndia.py --run-once
```

### Continuous mode

Use this when you want the scraper to keep polling forever at the configured interval.

```bash
python3 FinalScrapper.py
python3 ATSScrapper.py
python3 FinalScrapperIndia.py
python3 ATSScrapperIndia.py
```

## What Gets Filtered

The filters in `jobnotifier/job_filters.py` currently focus on:

- software engineer / developer roles
- SDE roles
- frontend, backend, and full-stack roles
- data engineer / data analyst / data scientist roles
- cloud, DevOps, infrastructure, and SRE roles

The filters also reject:

- internships and co-ops
- obviously senior or managerial roles
- agency and recruiter-style companies
- known junk aggregators
- reposted and promoted LinkedIn cards

## Local State Files

These are created under `data/state/`:

- `seen_jobs.txt`: seen links
- `seen_job_signatures.txt`: normalized title/company/location signatures
- `invalid_ats_targets.json`: ATS targets that repeatedly returned 404s

These files are local runtime state and are ignored by git.

## Typical Workflow

1. Update `.env`
2. Update `config/ats_targets.json`
3. Run a one-time test
4. Review the logs
5. Start the continuous runners you want
6. Let the seen-state files prevent duplicates over time

## Troubleshooting

### No ATS jobs found

Check:

- `config/ats_targets.json` has real board slugs
- the boards are public and valid
- your freshness window is not too strict
- the jobs are in your allowed market

### Email fails

Check:

- `EMAIL_USER` is correct
- `EMAIL_PASS` is a Gmail app password, not your normal Gmail password
- the recipient fields are set correctly

### The script exits immediately

That usually happens because you used `--run-once`. Remove it if you want the process to keep polling.

## GitHub Desktop Workflow

This repository already has its Git remote configured:

- `origin -> https://github.com/jelb30/Linkedin-Job-Scrapper.git`

Recommended workflow:

1. Open `Linkedin-Job-Scrapper` in GitHub Desktop
2. Review the changed files
3. Commit with a clear message
4. Push

If you want to be conservative, create a branch first, for example:

```text
restructure-local-scrapers
```

## Notes

- This project is for personal and educational use
- Respect LinkedIn and each ATS provider’s terms of service
- Excessive scraping can lead to throttling or blocking
