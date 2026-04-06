import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from bs4 import BeautifulSoup
import requests

from .job_filters import (
    is_allowed_location,
    is_blocked_card_text,
    is_blocked_company,
    is_entry_level_title,
)
from .job_runtime import Job, build_session, info, load_ats_targets, parse_int, print_job_match, warn


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _format_dt(value):
    parsed = _parse_dt(value)
    if not parsed:
        return ""
    return parsed.astimezone(timezone.utc).isoformat()


def _is_recent_enough(posted_at, max_age_hours):
    if not max_age_hours:
        return True
    parsed = _parse_dt(posted_at)
    if not parsed:
        return True
    return parsed >= datetime.now(timezone.utc) - timedelta(hours=max_age_hours)


def _candidate_job(
    title,
    company,
    loc,
    link,
    source,
    source_type,
    posted_at="",
    include_india=False,
):
    if not title or not link:
        return None
    if not is_entry_level_title(title):
        return None
    if is_blocked_company(company):
        return None
    if not is_allowed_location(loc, include_india=include_india):
        return None
    return Job(
        title=title.strip(),
        company=(company or "").strip(),
        loc=(loc or "").strip(),
        link=link.strip(),
        source=source.strip(),
        source_type=source_type.strip(),
        posted_at=(posted_at or "").strip(),
    )

def scrape_linkedin_jobs(session=None, pages_to_scrape=5, include_india=False):
    session = session or build_session()
    max_age_seconds = parse_int(os.getenv("LINKEDIN_MAX_AGE_SECONDS"), 86400)
    search_queries = [
        {
            "geoId": "103644278",
            "location": "United States",
        },
    ]
    if include_india:
        search_queries.append(
            {
                "geoId": "102713980",
                "location": "India",
            }
        )
    shared_query = {
        "f_JT": "F",
        "f_E": "1,2",
        "f_TPR": f"r{max_age_seconds}",
        "keywords": (
            "software engineer OR software developer OR software development engineer "
            "OR sde OR site reliability engineer OR infrastructure engineer "
            "OR devops engineer OR cloud engineer OR data analyst "
            "OR data engineer OR data scientist"
        ),
        "origin": "JOB_SEARCH_PAGE_JOB_FILTER",
        "sortBy": "DD",
    }

    jobs = []
    for search in search_queries:
        for page in range(pages_to_scrape):
            query = dict(shared_query)
            query.update(search)
            if page:
                query["start"] = page * 25
            url = f"https://www.linkedin.com/jobs/search/?{urlencode(query)}"
            try:
                response = session.get(url, timeout=(5, 30))
                response.raise_for_status()
            except requests.RequestException as exc:
                warn(
                    f"⚠️ LinkedIn page {page + 1} failed "
                    f"| market={search['location']} | reason={exc}"
                )
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_="base-card")
            info(
                f"LinkedIn page {page + 1}: parsed {len(cards)} job cards. "
                f"| market={search['location']}"
            )

            for card in cards:
                anchor = (
                    card.select_one("a.base-card__full-link")
                    or card.find("a", href=lambda href: href and "/jobs/view/" in href)
                )
                if not anchor:
                    continue

                title = anchor.get_text(strip=True)
                link = anchor.get("href", "").partition("?")[0]
                loc_el = (
                    card.select_one("span.job-search-card__location")
                    or card.select_one("span.base-search-card__location")
                    or card.find("span", class_="job-result-card__location")
                )
                company_el = (
                    card.select_one("h4.base-search-card__subtitle")
                    or card.select_one("h3.base-search-card__subtitle")
                )
                loc = loc_el.get_text(strip=True) if loc_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                card_text = card.get_text(" ", strip=True)

                candidate = _candidate_job(
                    title=title,
                    company=company,
                    loc=loc,
                    link=link,
                    source="linkedin",
                    source_type="linkedin",
                    include_india=include_india,
                )
                if not candidate:
                    continue
                if is_blocked_card_text(card_text):
                    continue

                print_job_match(candidate)
                jobs.append(candidate)

    info(f"LinkedIn scrape complete | accepted={len(jobs)}")
    return jobs


def fetch_greenhouse_jobs(session, board, max_age_hours, include_india=False):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    response = session.get(url, timeout=(5, 30))
    response.raise_for_status()
    payload = response.json()

    entries = payload.get("jobs", [])
    jobs = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        posted_at = _format_dt(entry.get("updated_at") or entry.get("created_at"))
        if not _is_recent_enough(posted_at, max_age_hours):
            continue
        candidate = _candidate_job(
            title=entry.get("title", ""),
            company=payload.get("meta", {}).get("board_name", board),
            loc=(entry.get("location") or {}).get("name", ""),
            link=entry.get("absolute_url", ""),
            source=f"greenhouse:{board}",
            source_type="greenhouse",
            posted_at=posted_at,
            include_india=include_india,
        )
        if candidate:
            jobs.append(candidate)
    return jobs, len(entries)


def fetch_ashby_jobs(session, board, max_age_hours, include_india=False):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    response = session.get(url, timeout=(5, 30))
    response.raise_for_status()
    payload = response.json()

    jobs = []
    total_available = 0
    company = payload.get("company")
    company_name = (
        company.get("name") if isinstance(company, dict) else None
    ) or payload.get("companyName") or payload.get("name") or board
    sections = []
    job_board = payload.get("jobBoard")
    if isinstance(job_board, list):
        sections.extend(job_board)
    elif isinstance(job_board, dict):
        sections.extend(job_board.get("departments", []))
        if job_board.get("jobPostings"):
            sections.append(job_board)
    sections.extend(payload.get("departments", []))

    top_level_jobs = payload.get("jobPostings", []) or payload.get("jobs", [])
    for entry in top_level_jobs:
        sections.append({"jobPostings": [entry]})

    for section in sections:
        entries = section.get("jobPostings", []) if isinstance(section, dict) else []
        total_available += len(entries)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            location = entry.get("location") or {}
            if not isinstance(location, dict):
                location = {"name": str(location), "locationName": str(location)}
            posted_at = _format_dt(entry.get("publishedAt") or entry.get("updatedAt"))
            if not _is_recent_enough(posted_at, max_age_hours):
                continue
            link = (
                entry.get("jobUrl")
                or entry.get("url")
                or entry.get("absoluteUrl")
                or entry.get("applyUrl")
            )
            if not link and entry.get("id"):
                link = f"https://jobs.ashbyhq.com/{board}/{entry['id']}"
            candidate = _candidate_job(
                title=entry.get("title", ""),
                company=company_name,
                loc=location.get("locationName") or location.get("name", ""),
                link=link or "",
                source=f"ashby:{board}",
                source_type="ashby",
                posted_at=posted_at,
                include_india=include_india,
            )
            if candidate:
                jobs.append(candidate)
    return jobs, total_available


def fetch_lever_jobs(session, site, max_age_hours, include_india=False):
    url = f"https://api.lever.co/v0/postings/{site}?mode=json&limit=100"
    response = session.get(url, timeout=(5, 30))
    response.raise_for_status()
    payload = response.json()

    jobs = []
    total_available = len(payload)
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        posted_at = _format_dt(entry.get("createdAt"))
        if not _is_recent_enough(posted_at, max_age_hours):
            continue
        categories = entry.get("categories") or {}
        if not isinstance(categories, dict):
            categories = {}
        candidate = _candidate_job(
            title=entry.get("text", ""),
            company=site,
            loc=categories.get("location", ""),
            link=entry.get("hostedUrl") or entry.get("applyUrl", ""),
            source=f"lever:{site}",
            source_type="lever",
            posted_at=posted_at,
            include_india=include_india,
        )
        if candidate:
            jobs.append(candidate)
    return jobs, total_available


def fetch_smartrecruiters_jobs(session, company, max_age_hours, include_india=False):
    url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100&offset=0"
    response = session.get(url, timeout=(5, 30))
    response.raise_for_status()
    payload = response.json()

    entries = payload.get("content", [])
    jobs = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        posted_at = _format_dt(entry.get("releasedDate"))
        if not _is_recent_enough(posted_at, max_age_hours):
            continue
        location = entry.get("location") or {}
        if not isinstance(location, dict):
            location = {}
        loc = ", ".join(
            value
            for value in [location.get("city"), location.get("region"), location.get("country")]
            if value
        )
        candidate = _candidate_job(
            title=entry.get("name", ""),
            company=((entry.get("company") or {}) if isinstance(entry.get("company"), dict) else {}).get("name", company),
            loc=loc,
            link=entry.get("ref") or "",
            source=f"smartrecruiters:{company}",
            source_type="smartrecruiters",
            posted_at=posted_at,
            include_india=include_india,
        )
        if candidate:
            jobs.append(candidate)
    return jobs, len(entries)


def fetch_workable_jobs(session, subdomain, max_age_hours, include_india=False):
    url = f"https://www.workable.com/api/accounts/{subdomain}"
    response = session.get(url, timeout=(5, 30))
    response.raise_for_status()
    payload = response.json()

    entries = payload.get("jobs", []) if isinstance(payload, dict) else []
    jobs = []
    account_name = payload.get("name", subdomain) if isinstance(payload, dict) else subdomain
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        posted_at = _format_dt(
            entry.get("published")
            or entry.get("published_on")
            or entry.get("created_at")
            or entry.get("updated_at")
        )
        if not _is_recent_enough(posted_at, max_age_hours):
            continue
        location = entry.get("location") or entry.get("full_location") or ""
        link = entry.get("url") or entry.get("shortlink") or entry.get("apply_url") or ""
        shortcode = entry.get("shortcode")
        if not link and shortcode:
            link = f"https://apply.workable.com/{subdomain}/j/{shortcode}"
        candidate = _candidate_job(
            title=entry.get("title") or entry.get("name", ""),
            company=account_name,
            loc=location,
            link=link,
            source=f"workable:{subdomain}",
            source_type="workable",
            posted_at=posted_at,
            include_india=include_india,
        )
        if candidate:
            jobs.append(candidate)
    return jobs, len(entries)


def scrape_direct_ats_jobs(
    session=None,
    targets=None,
    max_age_hours=72,
    include_india=False,
    invalid_tracker=None,
):
    session = session or build_session()
    targets = targets or load_ats_targets()
    jobs = []
    stats = {
        "total_available": 0,
        "accepted": 0,
        "sources": [],
    }

    fetchers = [
        ("greenhouse_boards", fetch_greenhouse_jobs),
        ("ashby_boards", fetch_ashby_jobs),
        ("lever_sites", fetch_lever_jobs),
        ("smartrecruiters_companies", fetch_smartrecruiters_jobs),
        ("workable_subdomains", fetch_workable_jobs),
    ]

    for key, fetcher in fetchers:
        for target in targets.get(key, []):
            if invalid_tracker and invalid_tracker.should_skip(key, target):
                info(f"Skipping invalid ATS target | source={key} | target={target}")
                continue
            try:
                source_jobs, total_available = fetcher(
                    session,
                    target,
                    max_age_hours,
                    include_india=include_india,
                )
            except requests.RequestException as exc:
                warn(f"⚠️ ATS fetch failed | source={key} | target={target} | reason={exc}")
                response = getattr(exc, "response", None)
                if invalid_tracker and response is not None and response.status_code == 404:
                    invalid_tracker.record_not_found(key, target)
                continue
            except ValueError as exc:
                warn(f"⚠️ ATS parse failed | source={key} | target={target} | reason={exc}")
                continue
            except Exception as exc:
                warn(
                    f"⚠️ ATS unexpected parser failure | source={key} "
                    f"| target={target} | reason={type(exc).__name__}: {exc}"
                )
                continue

            if invalid_tracker:
                invalid_tracker.record_success(key, target)
            stats["total_available"] += total_available
            stats["accepted"] += len(source_jobs)
            stats["sources"].append(
                {
                    "source_key": key,
                    "target": target,
                    "total_available": total_available,
                    "accepted": len(source_jobs),
                }
            )
            info(
                f"ATS source {key}:{target} | total_available={total_available} "
                f"| accepted={len(source_jobs)}"
            )
            for job in source_jobs:
                print_job_match(job)
            jobs.extend(source_jobs)

    info(
        f"ATS scrape complete | total_available={stats['total_available']} "
        f"| accepted={len(jobs)}"
    )
    return jobs, stats
