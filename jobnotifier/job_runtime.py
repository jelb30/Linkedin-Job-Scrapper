import json
import os
import smtplib
import ssl
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .job_filters import classify_job_market, normalize_company, normalize_title

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
CONFIG_DIR = PROJECT_ROOT / "config"
STATE_DIR = PROJECT_ROOT / "data" / "state"


load_dotenv(PROJECT_ROOT / ".env")


def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def info(msg):
    print(f"[{_ts()}] INFO  {msg}")


def warn(msg):
    print(f"[{_ts()}] WARN  {msg}")


def error(msg):
    print(f"[{_ts()}] ERROR {msg}")


def getenv_first(*names):
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def split_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def default_ats_targets_path():
    configured = getenv_first("JOBBOT_ATS_TARGETS_FILE")
    if configured:
        return Path(configured)
    preferred = CONFIG_DIR / "ats_targets.json"
    if preferred.exists():
        return preferred
    legacy = PROJECT_ROOT / "ats_targets.json"
    if legacy.exists():
        return legacy
    return preferred


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Job:
    title: str
    company: str
    loc: str
    link: str
    source: str
    source_type: str
    posted_at: str = ""

    @property
    def signature(self):
        return "|".join(
            [
                normalize_title(self.title),
                normalize_company(self.company),
                normalize_title(self.loc),
            ]
        )


def print_job_match(job):
    print(
        "\n"
        "──────────────────────────────────────────────────────────────────────────────\n"
        f"Title   : {job.title}\n"
        f"Company : {job.company or '-'}\n"
        f"Location: {job.loc or '-'}\n"
        f"Source  : {job.source}\n"
        f"Link    : {job.link}\n"
        "──────────────────────────────────────────────────────────────────────────────"
    )


def format_jobs_email(jobs, heading=None):
    lines = [heading or "Here are the new matching jobs:", ""]
    for job in jobs:
        lines.append(f"Title: {job.title}")
        lines.append(f"Company: {job.company or '-'}")
        lines.append(f"Location: {job.loc or '-'}")
        lines.append(f"Source: {job.source}")
        if job.posted_at:
            lines.append(f"Posted: {job.posted_at}")
        lines.append(f"Link: {job.link}")
        lines.append("-" * 40)
    return "\n".join(lines)


def split_jobs_by_market(jobs):
    grouped = {"north_america": [], "india": []}
    for job in jobs:
        market = classify_job_market(job.loc)
        if market in grouped:
            grouped[market].append(job)
    return grouped


def send_market_emails(notifier_label, jobs):
    delivered = []
    grouped = split_jobs_by_market(jobs)
    market_specs = [
        (
            "north_america",
            f"📬 New {notifier_label} Jobs | US + North America",
            f"New {notifier_label} matches for US/North America.",
        ),
        (
            "india",
            f"🇮🇳 New {notifier_label} Jobs | India",
            f"New {notifier_label} matches for India.",
        ),
    ]

    for key, subject, heading in market_specs:
        market_jobs = grouped[key]
        if not market_jobs:
            continue
        if send_email(subject, format_jobs_email(market_jobs, heading=heading)):
            delivered.extend(market_jobs)
    return delivered


def send_email(subject, body):
    email_address = getenv_first("JOBBOT_EMAIL", "EMAIL_USER")
    email_password = getenv_first("JOBBOT_APP_PASSWORD", "EMAIL_PASS")
    primary_to = getenv_first("JOBBOT_TO", "EMAIL_TO") or email_address
    secondary_to = getenv_first("JOBBOT_TO_AS")
    recipients = [value for value in dict.fromkeys([primary_to, secondary_to]) if value]

    if not email_address or not email_password or not recipients:
        error("❌ Email skipped | missing email configuration")
        return False

    context = ssl.create_default_context()
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = email_address
        msg["To"] = ", ".join(recipients)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(email_address, email_password)
            smtp.send_message(msg)

        info(
            f"Email sent | subject='{subject}' | recipients={len(recipients)} "
            f"| bytes={len(body.encode('utf-8'))}"
        )
        return True
    except Exception as exc:
        error(f"❌ Email failed | reason={exc}")
        return False


def build_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0 Safari/537.36"
            )
        }
    )
    retries = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def dedupe_jobs(jobs):
    deduped = []
    seen_links = set()
    seen_signatures = set()
    for job in jobs:
        if not job.link or not job.title:
            continue
        if job.link in seen_links or job.signature in seen_signatures:
            continue
        seen_links.add(job.link)
        seen_signatures.add(job.signature)
        deduped.append(job)
    return deduped


def load_ats_targets():
    path = default_ats_targets_path()
    payload = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            warn(f"Failed to read ATS targets file '{path}'. reason={exc}")

    def merged(key, env_name):
        values = []
        values.extend(payload.get(key, []))
        values.extend(split_csv(os.getenv(env_name)))
        return list(dict.fromkeys(value for value in values if value))

    targets = {
        "greenhouse_boards": merged("greenhouse_boards", "GREENHOUSE_BOARDS"),
        "ashby_boards": merged("ashby_boards", "ASHBY_BOARDS"),
        "lever_sites": merged("lever_sites", "LEVER_SITES"),
        "smartrecruiters_companies": merged(
            "smartrecruiters_companies",
            "SMARTRECRUITERS_COMPANIES",
        ),
        "workable_subdomains": merged("workable_subdomains", "WORKABLE_SUBDOMAINS"),
    }
    total_targets = sum(len(values) for values in targets.values())
    if total_targets == 0:
        warn(
            "No ATS targets configured. Add ats_targets.json or set one of "
            "GREENHOUSE_BOARDS, ASHBY_BOARDS, LEVER_SITES, "
            "SMARTRECRUITERS_COMPANIES, WORKABLE_SUBDOMAINS."
        )
    else:
        info(f"Loaded ATS targets | total={total_targets}")
    return targets


class InvalidAtsTargetTracker:
    def __init__(self, path=STATE_DIR / "invalid_ats_targets.json", threshold=3):
        self.path = Path(path)
        self.threshold = threshold
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            warn(f"Failed to read invalid ATS target tracker '{self.path}'. reason={exc}")
            return {}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as exc:
            warn(f"Failed to save invalid ATS target tracker '{self.path}'. reason={exc}")

    def should_skip(self, source_key, target):
        item = self.data.get(source_key, {}).get(target, {})
        return item.get("not_found_count", 0) >= self.threshold

    def record_not_found(self, source_key, target):
        source_bucket = self.data.setdefault(source_key, {})
        item = source_bucket.setdefault(target, {})
        item["not_found_count"] = item.get("not_found_count", 0) + 1
        item["last_error_at"] = utc_now_iso()
        if item["not_found_count"] >= self.threshold:
            warn(
                f"Target marked as invalid after repeated 404s "
                f"| source={source_key} | target={target}"
            )
        self._save()

    def record_success(self, source_key, target):
        source_bucket = self.data.get(source_key, {})
        if target in source_bucket:
            del source_bucket[target]
            if not source_bucket:
                self.data.pop(source_key, None)
            self._save()


class LocalFileStateStore:
    def __init__(
        self,
        links_path=STATE_DIR / "seen_jobs.txt",
        signatures_path=STATE_DIR / "seen_job_signatures.txt",
    ):
        self.links_path = links_path
        self.signatures_path = signatures_path
        self.links = self._load_set(links_path, "seen-links")
        self.signatures = self._load_set(signatures_path, "seen-signatures")

    def _load_set(self, path, label):
        if not os.path.exists(path):
            info(f"{label} file not found; starting fresh.")
            return set()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                values = set(handle.read().splitlines())
            info(f"Loaded {label} set | count={len(values)}")
            return values
        except Exception as exc:
            warn(f"Failed to read {label} file; continuing with empty set. reason={exc}")
            return set()

    def _save_set(self, path, values, label):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="seen_", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("\n".join(sorted(values)))
            os.replace(tmp, path)
            info(f"Saved {label} set | count={len(values)}")
        except Exception as exc:
            warn(f"Failed to save {label} file. reason={exc}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    def contains(self, job):
        return job.link in self.links or job.signature in self.signatures

    def mark_many(self, jobs):
        if not jobs:
            return
        self.links.update(job.link for job in jobs)
        self.signatures.update(job.signature for job in jobs)
        self._save_set(self.links_path, self.links, "seen-links")
        self._save_set(self.signatures_path, self.signatures, "seen-signatures")
