# LinkedIn and ATS Job Scrapers

Automated local job scrapers built to solve a practical problem: finding fresh software, data, infrastructure, and SRE jobs as early as possible without manually refreshing LinkedIn and company career pages all day.

This project was designed and coded around a real job-search workflow. Instead of relying on one source, it combines:

- LinkedIn search scraping for broad discovery
- Direct ATS board scraping for cleaner and often faster company-side job discovery
- local deduplication and filtering so only relevant new jobs are emailed

The goal is simple: automate the repetitive part of job hunting so new openings reach you in near real time with less noise.

## Why This Exists

Manually checking LinkedIn every few minutes is slow, repetitive, and noisy. A lot of results are reposted, promoted, duplicated, or come from agencies and aggregators.

This project was built to improve that workflow by:

- checking for new jobs automatically
- filtering low-signal postings out
- keeping a local seen-job history
- emailing only new matches
- separating LinkedIn discovery from ATS discovery

It is not a generic scraping demo. It is a working local automation tool built specifically to make job searching faster and more efficient.

## What It Does

- Scrapes LinkedIn job search pages for fresh full-time roles
- Polls configured ATS job boards directly
- Filters out reposted and promoted LinkedIn jobs
- Filters out agencies, staffing firms, and junk aggregators
- Focuses on software engineering, SDE, data, platform, cloud, DevOps, infrastructure, and SRE-style roles
- Deduplicates by both job link and normalized job signature
- Tracks seen jobs locally so the same posting is not emailed repeatedly
- Emails only newly discovered jobs

## Sources Covered

### LinkedIn

Used for broad discovery and real-time scanning of public job search results.

### Direct ATS boards

Used for cleaner company-side discovery. The current ATS pipeline supports public boards from:

- Greenhouse
- Ashby
- Lever
- SmartRecruiters
- Workable

This gives better coverage than relying on LinkedIn alone.

## How It Works

### LinkedIn flow

`FinalScrapper.py` and `FinalScrapperIndia.py` run the LinkedIn pipeline.

Each cycle:

1. Builds a LinkedIn search query using the configured keywords and freshness window
2. Fetches the search-result pages
3. Extracts title, company, location, and job link from each card
4. Rejects reposted and promoted cards
5. Applies title, company, and location filters
6. Deduplicates results
7. Compares them against local seen-job history
8. Emails only jobs that were not seen before

### ATS flow

`ATSScrapper.py` and `ATSScrapperIndia.py` run the ATS pipeline.

Each cycle:

1. Loads ATS target boards from `config/ats_targets.json`
2. Calls the public job-board endpoints for each configured company
3. Normalizes jobs into one shared internal format
4. Applies freshness, title, company, and location filters
5. Tracks bad ATS targets that repeatedly 404
6. Deduplicates results
7. Compares them against local seen-job history
8. Emails only new jobs

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

The real shared logic lives in `jobnotifier/`. That keeps the code maintainable and avoids duplicating the same filtering, emailing, deduping, and parsing logic across multiple scripts.

## Supported Runners

### US / North America

- `FinalScrapper.py`
- `ATSScrapper.py`

### India

- `FinalScrapperIndia.py`
- `ATSScrapperIndia.py`

The US/North America scripts are the default path. India is kept separate so you can run it intentionally without changing flags every time.

## Quick Start

```bash
git clone https://github.com/jelb30/Linkedin-Job-Scrapper.git
cd Linkedin-Job-Scrapper
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Then:

1. Fill in `.env`
2. Edit `config/ats_targets.json`
3. Run a one-time test

```bash
python3 FinalScrapper.py --run-once
python3 ATSScrapper.py --run-once
```

## Full Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3. Create your `.env`

```bash
cp .env.example .env
```

Fill in at least:

- `EMAIL_USER`
- `EMAIL_PASS`
- `EMAIL_TO`

`.env.example` is the tracked template for the repo. `.env` is your private local file and is ignored by git.

### 4. Configure ATS targets

Edit:

- `config/ats_targets.json`

This file controls which company ATS boards are checked. The ATS scraper only checks the company boards you explicitly list there.

## Environment Variables

Common settings in `.env`:

- `EMAIL_USER`: sender Gmail address
- `EMAIL_PASS`: Gmail app password
- `EMAIL_TO`: recipient email address
- `EMAIL_TO_AS`: optional second recipient
- `LINKEDIN_PAGES_TO_SCRAPE`: number of LinkedIn pages per cycle
- `CHECK_INTERVAL_SECONDS`: LinkedIn polling interval
- `LINKEDIN_MAX_AGE_SECONDS`: LinkedIn freshness window
- `ATS_CHECK_INTERVAL_SECONDS`: ATS polling interval
- `ATS_MAX_AGE_HOURS`: ATS freshness window
- `ATS_INVALID_TARGET_THRESHOLD`: number of repeated 404s before a bad ATS target is skipped

## How To Run

### One-time test run

Use this when you want to verify scraping, filtering, and email delivery without leaving the process running.

```bash
python3 FinalScrapper.py --run-once
python3 ATSScrapper.py --run-once
python3 FinalScrapperIndia.py --run-once
python3 ATSScrapperIndia.py --run-once
```

### Continuous mode

Use this when you want the scrapers to keep polling forever using the configured intervals.

```bash
python3 FinalScrapper.py
python3 ATSScrapper.py
python3 FinalScrapperIndia.py
python3 ATSScrapperIndia.py
```

## What Gets Filtered

The filters in `jobnotifier/job_filters.py` currently focus on:

- software engineer and software developer roles
- SDE roles
- frontend, backend, and full-stack roles
- data engineer, data analyst, and data scientist roles
- cloud, DevOps, infrastructure, and SRE roles

The filters also reject:

- internships and co-ops
- clearly senior or managerial roles
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
4. Review the logs and emails
5. Start the continuous runners you want
6. Let the local state files prevent duplicates over time

## Troubleshooting

### No ATS jobs found

Check:

- `config/ats_targets.json` contains real public board slugs
- the boards are public and valid
- your freshness window is not too strict
- the jobs are in your allowed market

### Email fails

Check:

- `EMAIL_USER` is correct
- `EMAIL_PASS` is a Gmail app password, not your regular Gmail password
- the recipient fields are set correctly

### The script exits immediately

That usually means you ran it with `--run-once`. Remove that flag if you want the process to keep polling.

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
