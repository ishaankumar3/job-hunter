#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================
 Daily Job Search Automation — Ishaan Kumar
====================================================
 Searches 12+ UK & EU job portals daily
 Sends 20 best-matched jobs to ishaankumar3@gmail.com
 Runs automatically at 8am via GitHub Actions
====================================================
"""

import os, json, hashlib, smtplib, time, logging, re, sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode, quote_plus

import requests
import feedparser

# ── Suppress SSL warnings in some environments ─────────────────────────────
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  CONFIGURATION — edit only if needed
# ═══════════════════════════════════════════════════════════════════

EMAIL_TO         = "ishaankumar3@gmail.com"
EMAIL_FROM       = os.environ.get("EMAIL_FROM", "")          # Your Gmail address
EMAIL_PASSWORD   = os.environ.get("EMAIL_PASSWORD", "")      # Gmail App Password (16-char)
ADZUNA_APP_ID    = os.environ.get("ADZUNA_APP_ID", "")       # Free from api.adzuna.com
ADZUNA_APP_KEY   = os.environ.get("ADZUNA_APP_KEY", "")      # Free from api.adzuna.com
REED_API_KEY     = os.environ.get("REED_API_KEY", "")        # Free from reed.co.uk/developers
SEEN_JOBS_FILE   = "seen_jobs.json"
JOBS_PER_EMAIL   = 50
FETCH_POOL_SIZE  = 300  # fetch this many before filtering to guarantee 50 after
SALARY_MIN       = 42000
SALARY_MAX       = 55000

# ── Target job titles (high priority first) ────────────────────────
HIGH_PRIORITY = [
    "Water Design Engineer",
    "Clean Water Engineer",
    "Water Infrastructure Engineer",
    "Developer Services Engineer",
    "NAV Design Engineer",
    "Self-Lay Design Engineer",
    "Water Network Design Engineer",
    "Hydraulic Engineer",
    "Hydraulic Modeller",
    "Water Asset Design Engineer",
    "Utilities Design Engineer",
    "Civil Engineer Water",
    "Water Engineering Consultant",
    "Water Projects Engineer",
    "Water Network Engineer",
]

SECONDARY = [
    "Wastewater Design Engineer",
    "Drainage Engineer",
    "SuDS Design Engineer",
    "Infrastructure Engineer",
    "Multi-Utility Design Engineer",
    "Civil Infrastructure Design Engineer",
    "Utilities Coordination Engineer",
    "Water Technical Engineer",
    "Water Engineer",
]

ALL_TITLES = HIGH_PRIORITY + SECONDARY

# ── Keywords extracted from Ishaan's CV (used for scoring) ─────────
SKILL_KEYWORDS = [
    "watergems", "autocad", "revit", "civil 3d", "arcgis",
    "hydraulic", "water network", "water distribution", "water mains",
    "nav", "self-lay", "self lay", "developer services",
    "thames water", "affinity water", "south east water", "wessex water",
    "amp7", "amp8", "amp 7", "amp 8",
    "water infrastructure", "cdm", "eusr", "wras", "dwi", "ofwat",
    "section 104", "section 185", "section 38",
    "sewers for adoption", "sfa",
    "pumping station", "drainage", "suds", "water mains design",
    "pipe design", "pressure", "navisworks", "infraworks",
    "miet", "ceng", "chartered engineer",
    "water utility", "utilities", "infrastructure",
]

# ── Search query terms sent to APIs/RSS feeds ──────────────────────
SEARCH_QUERIES = [
    "water design engineer",
    "water network engineer",
    "hydraulic engineer water",
    "water infrastructure engineer",
    "developer services engineer",
    "NAV water engineer",
    "clean water engineer",
    "drainage engineer",
    "water modeller WaterGEMS",
    "utilities design engineer water",
    "self-lay engineer",
    "water asset engineer",
]

# ── Target locations ───────────────────────────────────────────────
UK_LOCATIONS   = ["London", "Surrey", "Kent", "Essex", "Hertfordshire", "Berkshire", "Hampshire"]
EU_LOCATIONS   = [
    ("Spain", "es"),
    ("Germany", "de"),
    ("Netherlands", "nl"),
    ("Ireland", "ie"),
    ("Portugal", "pt"),
]


# ═══════════════════════════════════════════════════════════════════
#  SEEN-JOBS PERSISTENCE  (avoid emailing duplicates across days)
# ═══════════════════════════════════════════════════════════════════

def load_seen() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE) as f:
                data = json.load(f)
                return set(data.get("ids", []))
        except Exception:
            pass
    return set()


def save_seen(ids: set):
    # Keep only the last 2000 to prevent unbounded growth
    trimmed = list(ids)[-2000:]
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump({"ids": trimmed, "updated": datetime.now().isoformat()}, f, indent=2)


def job_id(title: str, company: str, url: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{url.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════
#  RELEVANCE SCORING
# ═══════════════════════════════════════════════════════════════════

def score_job(title: str, description: str, salary_min=None, salary_max=None,
              rejected_patterns: dict = None) -> int:
    score = 0
    text = f"{title} {description}".lower()
    title_lower = title.lower()

    # Title priority score
    for t in HIGH_PRIORITY:
        if t.lower() in text or any(w in text for w in t.lower().split()):
            score += 30
            break
    for t in SECONDARY:
        if t.lower() in text:
            score += 15
            break

    # Skill keyword hits
    for kw in SKILL_KEYWORDS:
        if kw.lower() in text:
            score += 5

    # Salary match
    if salary_min and salary_max:
        if SALARY_MIN <= salary_max and salary_min <= SALARY_MAX:
            score += 20
    elif salary_min and salary_min >= SALARY_MIN:
        score += 10

    # ── Penalty from your "Not Applied" feedback ──────────────────
    # Jobs you marked No teach the bot what to avoid
    if rejected_patterns:
        title_words = rejected_patterns.get("title_words", {})
        bad_companies = rejected_patterns.get("companies", set())

        # Penalise words that appear frequently in jobs you rejected
        # Only penalise words seen in 2+ rejected jobs (avoids noise)
        penalty = 0
        for word, count in title_words.items():
            if count >= 2 and word in title_lower:
                penalty += 10 * count   # stronger penalty the more you reject it
        if penalty > 0:
            log.debug("[SCORE] Penalty -%d for '%s' (matches rejected title patterns)", penalty, title)
            score -= penalty

        # Hard skip flag for companies you consistently reject
        company_lower = description.lower()  # company name may appear in description
        for bad_co in bad_companies:
            if bad_co in title_lower or bad_co in company_lower:
                score -= 50  # pushes it to bottom of list
                log.debug("[SCORE] Company penalty for '%s' (previously rejected)", bad_co)
                break

    return score


# ═══════════════════════════════════════════════════════════════════
#  SOURCE 1 — ADZUNA API  (UK + EU)
# ═══════════════════════════════════════════════════════════════════

def fetch_adzuna_uk() -> list:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        log.warning("Adzuna API keys not set — skipping Adzuna UK")
        return []

    jobs = []
    base = "https://api.adzuna.com/v1/api/jobs/gb/search/1"

    for query in SEARCH_QUERIES[:10]:  # use 10 queries for larger pool
        try:
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": 100,
                "what": query,
                "where": "London",
                "distance": 60,
                "salary_min": SALARY_MIN,
                "salary_max": SALARY_MAX,
                "sort_by": "date",
                "content-type": "application/json",
            }
            r = requests.get(base, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            for item in data.get("results", []):
                sal_min = item.get("salary_min")
                sal_max = item.get("salary_max")
                jobs.append({
                    "title":       item.get("title", ""),
                    "company":     item.get("company", {}).get("display_name", "Unknown"),
                    "location":    item.get("location", {}).get("display_name", "UK"),
                    "description": item.get("description", ""),
                    "url":         item.get("redirect_url", ""),
                    "salary":      _fmt_salary(sal_min, sal_max),
                    "salary_min":  sal_min,
                    "salary_max":  sal_max,
                    "source":      "Adzuna UK",
                    "posted":      item.get("created", ""),
                })
            pass  # removed sleep
        except Exception as e:
            log.error(f"Adzuna UK error for '{query}': {e}")

    log.info(f"Adzuna UK: {len(jobs)} jobs fetched")
    return jobs


def fetch_adzuna_eu() -> list:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    jobs = []
    country_map = {"ie": "Ireland", "de": "Germany", "nl": "Netherlands"}

    for country_code, country_name in [("ie", "Ireland"), ("de", "Germany"), ("nl", "Netherlands")]:
        base = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
        try:
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": 25,
                "what": "water engineer",
                "sort_by": "date",
                "content-type": "application/json",
            }
            r = requests.get(base, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            for item in data.get("results", []):
                jobs.append({
                    "title":       item.get("title", ""),
                    "company":     item.get("company", {}).get("display_name", "Unknown"),
                    "location":    f"{item.get('location', {}).get('display_name', country_name)}, {country_name}",
                    "description": item.get("description", ""),
                    "url":         item.get("redirect_url", ""),
                    "salary":      _fmt_salary(item.get("salary_min"), item.get("salary_max")),
                    "salary_min":  item.get("salary_min"),
                    "salary_max":  item.get("salary_max"),
                    "source":      f"Adzuna {country_name}",
                    "posted":      item.get("created", ""),
                })
            pass  # removed sleep
        except Exception as e:
            log.error(f"Adzuna {country_name} error: {e}")

    log.info(f"Adzuna EU: {len(jobs)} jobs fetched")
    return jobs


# ═══════════════════════════════════════════════════════════════════
#  SOURCE 2 — REED UK API
# ═══════════════════════════════════════════════════════════════════

def fetch_reed() -> list:
    if not REED_API_KEY:
        log.warning("Reed API key not set — skipping Reed")
        return []

    jobs = []
    base = "https://www.reed.co.uk/api/1.0/search"
    queries = ["water engineer", "hydraulic engineer", "water network", "developer services engineer"]

    for query in queries:
        try:
            params = {
                "keywords": query,
                "locationName": "London",
                "distancefromLocation": 50,
                "minimumSalary": SALARY_MIN,
                "maximumSalary": SALARY_MAX,
                "resultsToTake": 100,
            }
            r = requests.get(base, params=params, auth=(REED_API_KEY, ""), timeout=15)
            r.raise_for_status()
            data = r.json()

            for item in data.get("results", []):
                jobs.append({
                    "title":       item.get("jobTitle", ""),
                    "company":     item.get("employerName", "Unknown"),
                    "location":    item.get("locationName", "UK"),
                    "description": item.get("jobDescription", ""),
                    "url":         item.get("jobUrl", ""),
                    "salary":      _fmt_salary(item.get("minimumSalary"), item.get("maximumSalary")),
                    "salary_min":  item.get("minimumSalary"),
                    "salary_max":  item.get("maximumSalary"),
                    "source":      "Reed UK",
                    "posted":      item.get("date", ""),
                })
            pass  # removed sleep
        except Exception as e:
            log.error(f"Reed error for '{query}': {e}")

    log.info(f"Reed UK: {len(jobs)} jobs fetched")
    return jobs


# ═══════════════════════════════════════════════════════════════════
#  SOURCE 3 — RSS FEEDS (Indeed, Totaljobs, CV-Library, CWJobs,
#              Jobsite, Guardian Jobs, New Civil Engineer)
# ═══════════════════════════════════════════════════════════════════

RSS_FEEDS = [
    # Indeed UK
    ("Indeed UK",      "https://www.indeed.co.uk/rss?q=water+design+engineer&l=London&radius=50&sort=date"),
    ("Indeed UK",      "https://www.indeed.co.uk/rss?q=hydraulic+engineer+water&l=London&radius=50&sort=date"),
    ("Indeed UK",      "https://www.indeed.co.uk/rss?q=developer+services+engineer&l=London&radius=50&sort=date"),
    ("Indeed UK",      "https://www.indeed.co.uk/rss?q=NAV+water+engineer&l=London&radius=50&sort=date"),
    ("Indeed UK",      "https://www.indeed.co.uk/rss?q=water+network+engineer&l=South+East+England&radius=50&sort=date"),

    # Totaljobs
    ("Totaljobs",      "https://www.totaljobs.com/SearchResults/rss?Keywords=water+design+engineer&Location=London&Radius=50"),
    ("Totaljobs",      "https://www.totaljobs.com/SearchResults/rss?Keywords=hydraulic+engineer&Location=London&Radius=50"),
    ("Totaljobs",      "https://www.totaljobs.com/SearchResults/rss?Keywords=water+infrastructure+engineer&Location=London"),

    # CV-Library
    ("CV-Library",     "https://www.cv-library.co.uk/jobs/rss?q=water+engineer&loc=London&rad=50&salary_min=40000"),
    ("CV-Library",     "https://www.cv-library.co.uk/jobs/rss?q=hydraulic+engineer&loc=London&rad=50"),

    # CWJobs
    ("CWJobs",         "https://www.cwjobs.co.uk/SearchResults/rss?Keywords=water+engineer&Location=London&Radius=50"),

    # Jobsite
    ("Jobsite",        "https://www.jobsite.co.uk/jobs/rss?keywords=water+design+engineer&location=London&radius=50"),

    # Guardian Jobs
    ("Guardian Jobs",  "https://jobs.theguardian.com/jobs/engineering/water/?format=rss"),

    # New Civil Engineer Jobs
    ("New Civil Engineer", "https://jobs.newcivilengineer.com/jobs/feed/?s=water+engineer&location=London"),

    # Indeed Ireland
    ("Indeed Ireland", "https://ie.indeed.com/rss?q=water+engineer&l=Dublin&sort=date"),

    # Indeed Germany
    ("Indeed Germany", "https://de.indeed.com/rss?q=water+engineer&l=Germany&sort=date"),

    # Indeed Netherlands
    ("Indeed Netherlands", "https://nl.indeed.com/rss?q=water+engineer&l=Netherlands&sort=date"),

    # Indeed Spain
    ("Indeed Spain",   "https://es.indeed.com/rss?q=water+engineer&l=Spain&sort=date"),

    # Indeed Portugal
    ("Indeed Portugal","https://pt.indeed.com/rss?q=water+engineer&l=Portugal&sort=date"),
]


def _fetch_feed_safe(url: str, timeout: int = 8) -> list:
    """Fetch an RSS feed with a hard timeout using requests first, then feedparser."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"}
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        return feed.entries
    except Exception as e:
        log.warning(f"Feed fetch failed [{url[:60]}]: {e}")
        return []


def fetch_rss_feeds() -> list:
    jobs = []
    for source_name, url in RSS_FEEDS:
        try:
            entries = _fetch_feed_safe(url, timeout=8)
            count = 0
            for entry in entries:
                title   = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                link    = entry.get("link", "")
                company = _extract_company(entry)
                location= _extract_location(entry, source_name)

                if not title or not link:
                    continue

                combined = f"{title} {summary}".lower()
                if not any(k in combined for k in ["water", "hydraulic", "drainage", "utility", "utilities", "infrastructure", "engineer"]):
                    continue

                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    location,
                    "description": _clean_html(summary)[:500],
                    "url":         link,
                    "salary":      _extract_salary_from_text(summary),
                    "salary_min":  None,
                    "salary_max":  None,
                    "source":      source_name,
                    "posted":      entry.get("published", ""),
                })
                count += 1

            log.info(f"{source_name}: {count} items")

        except Exception as e:
            log.error(f"RSS error [{source_name}]: {e}")

    log.info(f"RSS total: {len(jobs)} jobs")
    return jobs


# ═══════════════════════════════════════════════════════════════════
#  SOURCE 4 — ADDITIONAL SPECIALIST BOARDS
# ═══════════════════════════════════════════════════════════════════

SPECIALIST_FEEDS = [
    ("Environment Jobs",  "https://www.environmentjob.co.uk/jobs.rss?keywords=water+engineer"),
    ("Utility People",    "https://www.utilitypeople.co.uk/jobs/feed/?keywords=water+engineer"),
]


def fetch_specialist_boards() -> list:
    jobs = []
    for source_name, url in SPECIALIST_FEEDS:
        try:
            entries = _fetch_feed_safe(url, timeout=8)
            for entry in entries:
                title   = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                link    = entry.get("link", "")
                if not title or not link:
                    continue
                jobs.append({
                    "title":       title,
                    "company":     _extract_company(entry),
                    "location":    _extract_location(entry, source_name),
                    "description": _clean_html(summary)[:500],
                    "url":         link,
                    "salary":      _extract_salary_from_text(summary),
                    "salary_min":  None,
                    "salary_max":  None,
                    "source":      source_name,
                    "posted":      entry.get("published", ""),
                })
            log.info(f"{source_name}: {len(entries)} items")
        except Exception as e:
            log.error(f"Specialist board error [{source_name}]: {e}")

    return jobs


# ═══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def _fmt_salary(sal_min, sal_max) -> str:
    if sal_min and sal_max:
        return f"£{int(sal_min):,} – £{int(sal_max):,}"
    elif sal_min:
        return f"From £{int(sal_min):,}"
    elif sal_max:
        return f"Up to £{int(sal_max):,}"
    return "Not specified"


def _clean_html(text: str) -> str:
    try:
        from html.parser import HTMLParser
        class MLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.reset()
                self.fed = []
            def handle_data(self, d):
                self.fed.append(d)
            def get_data(self):
                return " ".join(self.fed)
        s = MLStripper()
        s.feed(text)
        return re.sub(r"\s+", " ", s.get_data()).strip()
    except Exception:
        return re.sub(r"<[^>]+>", " ", text).strip()


def _extract_company(entry) -> str:
    for field in ["author", "author_detail", "tags"]:
        if field in entry:
            v = entry[field]
            if isinstance(v, str) and v:
                return v
            if isinstance(v, dict) and v.get("name"):
                return v["name"]
    title = entry.get("title", "")
    # Many RSS feeds format as "Job Title - Company Name"
    if " - " in title:
        return title.split(" - ")[-1].strip()
    return "Unknown"


def _extract_location(entry, source: str) -> str:
    for tag in ["location", "georss_point", "tags"]:
        if tag in entry:
            val = entry[tag]
            if isinstance(val, str) and val:
                return val
    summary = entry.get("summary", "")
    # Try to extract from description
    loc_match = re.search(r"Location[:\s]+([A-Za-z ,]+)", summary)
    if loc_match:
        return loc_match.group(1).strip()
    # Infer from source
    for country in ["Ireland", "Germany", "Netherlands", "Spain", "Portugal"]:
        if country in source:
            return country
    return "UK"


def _extract_salary_from_text(text: str) -> str:
    patterns = [
        r"£([\d,]+)\s*[-–to]+\s*£([\d,]+)",
        r"£([\d,]+)k?\s*[-–to]+\s*£?([\d,]+)k?",
        r"salary[:\s]+£([\d,]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                lo = int(m.group(1).replace(",", ""))
                hi = int(m.group(2).replace(",", "")) if len(m.groups()) > 1 else lo
                if lo < 1000:  # Handle "k" notation
                    lo, hi = lo * 1000, hi * 1000
                return f"£{lo:,} – £{hi:,}"
            except Exception:
                pass
    return "See listing"


# ═══════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════

def run():
    log.info("=" * 60)
    log.info(" Job Hunter — Daily Run Starting")
    log.info(f" Date: {datetime.now().strftime('%A %d %B %Y, %H:%M UTC')}")
    log.info("=" * 60)

    # Load already-sent job IDs from Excel tracker
    try:
        from job_tracker import load_sent_ids, load_rejected_patterns
        seen = load_sent_ids()
        rejected_patterns = load_rejected_patterns()
    except Exception as e:
        log.warning("[TRACKER] Could not load tracker (%s) — falling back to seen_jobs.json", e)
        seen = load_seen()
        rejected_patterns = {"title_words": {}, "companies": set()}
    log.info("Previously sent jobs (in tracker): %d", len(seen))
    log.info("[TRACKER] Rejected patterns loaded: %d title words, %d companies to avoid",
             len(rejected_patterns["title_words"]), len(rejected_patterns["companies"]))

    # ── Collect from all sources ─────────────────────────────────
    all_jobs = []
    all_jobs += fetch_adzuna_uk()
    all_jobs += fetch_adzuna_eu()
    all_jobs += fetch_reed()
    all_jobs += fetch_rss_feeds()
    all_jobs += fetch_specialist_boards()

    log.info(f"Total raw jobs collected: {len(all_jobs)}")

    # ── Deduplicate against tracker ──────────────────────────────
    fresh_jobs = []
    seen_this_run = set()
    for job in all_jobs:
        jid = job_id(job["title"], job["company"], job["url"])
        if jid not in seen and jid not in seen_this_run:
            job["_id"] = jid
            fresh_jobs.append(job)
            seen_this_run.add(jid)

    log.info("Fresh jobs (not yet sent): %d", len(fresh_jobs))

    # ── Score & rank (with feedback penalty from tracker) ───────
    for job in fresh_jobs:
        job["_score"] = score_job(
            job["title"],
            job["description"],
            job.get("salary_min"),
            job.get("salary_max"),
            rejected_patterns=rejected_patterns,
        )

    fresh_jobs.sort(key=lambda j: j["_score"], reverse=True)

    # ── Filter jobs based on your "Why No" feedback ─────────────
    try:
        from job_tracker import load_rejection_reasons, should_skip_job
        rejections = load_rejection_reasons()
        if rejections:
            before = len(fresh_jobs)
            filtered = []
            for job in fresh_jobs:
                skip, reason = should_skip_job(job, rejections)
                if skip:
                    log.info("[FILTER] Skipping: %s @ %s — %s", job["title"], job["company"], reason)
                else:
                    filtered.append(job)
            fresh_jobs = filtered
            log.info("[FILTER] Removed %d jobs based on your rejection feedback (%d remain)",
                     before - len(fresh_jobs), len(fresh_jobs))
        else:
            log.info("[FILTER] No rejection reasons in tracker yet — showing all jobs")
    except Exception as e:
        log.warning("[FILTER] Could not apply rejection filter: %s", e)

    # ── Sponsorship license filter ────────────────────────────────
    log.info("Running sponsorship license checks...")
    try:
        from sponsorship_check import filter_by_sponsorship
        fresh_jobs = filter_by_sponsorship(fresh_jobs, include_unknown=True, target_count=FETCH_POOL_SIZE)
        log.info(f"After sponsorship filter: {len(fresh_jobs)} jobs remain")
    except Exception as e:
        log.error(f"Sponsorship check failed (continuing without): {e}")

    # ── Guarantee exactly 20 jobs ────────────────────────────────
    # If sponsorship filter reduced the pool below 20, backfill from
    # the original scored list (excluding already-included job IDs)
    if len(fresh_jobs) < JOBS_PER_EMAIL:
        already_in = {j.get("_id") for j in fresh_jobs}
        # Re-add UNKNOWN-status jobs we may have excluded, scored highest first
        backfill = [j for j in fresh_jobs if j.get("_id") not in already_in]
        fresh_jobs = (fresh_jobs + backfill)[:JOBS_PER_EMAIL]
        log.info(f"Backfilled to {len(fresh_jobs)} jobs")

    top_jobs = fresh_jobs[:JOBS_PER_EMAIL]
    log.info(f"Top jobs selected for email: {len(top_jobs)}")

    if not top_jobs:
        log.warning("No new jobs found today — skipping email")
        return

    # ── Generate tailored CV + cover letter for ALL 20 jobs ─────
    application_packs = []
    zip_path = None

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    log.info("=" * 50)
    log.info("[CV] Starting application pack generation")
    log.info("[CV] ANTHROPIC_API_KEY present: %s (length=%d)", bool(api_key), len(api_key))
    log.info("[CV] Jobs to process: %d", len(top_jobs))
    log.info("=" * 50)

    if not api_key:
        log.warning("[CV] ANTHROPIC_API_KEY not set in GitHub Secrets - no CVs generated")
    else:
        log.info("[CV] Step A: Importing tailor_cv module...")
        generate_application_pack = None
        try:
            from tailor_cv import generate_application_pack
            log.info("[CV] Step A: tailor_cv imported OK")
        except Exception as import_err:
            import traceback as _tb
            log.error("[CV] Step A FAILED - cannot import tailor_cv: %s", import_err)
            log.error(_tb.format_exc())

        if generate_application_pack is not None:
            pack_dir = "application_packs"
            os.makedirs(pack_dir, exist_ok=True)
            log.info("[CV] Step B: Output dir: %s", os.path.abspath(pack_dir))

            log.info("[CV] Step C: Generating packs one by one...")
            for idx, job in enumerate(top_jobs, 1):
                log.info("[CV] %d/%d: %s @ %s", idx, len(top_jobs), job["title"], job["company"])
                try:
                    pack = generate_application_pack(job, output_dir=pack_dir)
                    if pack:
                        pack["job_number"] = idx
                        application_packs.append(pack)
                        log.info("[CV] %d/%d DONE", idx, len(top_jobs))
                    else:
                        log.warning("[CV] %d/%d returned None", idx, len(top_jobs))
                except Exception as pack_err:
                    import traceback as _tb
                    log.error("[CV] %d/%d CRASHED: %s", idx, len(top_jobs), pack_err)
                    log.error(_tb.format_exc())

            log.info("[CV] Step C done: %d packs generated", len(application_packs))

            if application_packs:
                log.info("[CV] Step D: Building ZIP...")
                import zipfile as _zf
                today_str = datetime.now().strftime("%Y-%m-%d")
                zip_path = "Ishaan_Kumar_Applications_" + today_str + ".zip"
                files_added = 0
                try:
                    with _zf.ZipFile(zip_path, "w", _zf.ZIP_DEFLATED) as zf:
                        for pack in application_packs:
                            num = int(pack.get("job_number") or 0)
                            safe = re.sub(r"[^\w]", "_", pack.get("company", "Unknown"))[:20]
                            folder = "%02d_%s" % (num, safe)
                            cv = pack.get("cv_path", "")
                            cl = pack.get("cl_path", "")
                            if cv and os.path.exists(cv):
                                zf.write(cv, folder + "/CV_Ishaan_Kumar.docx")
                                files_added += 1
                                log.info("[ZIP] + %s/CV", folder)
                            else:
                                log.warning("[ZIP] CV missing: %s", cv)
                            if cl and os.path.exists(cl):
                                zf.write(cl, folder + "/Cover_Letter_Ishaan_Kumar.docx")
                                files_added += 1
                                log.info("[ZIP] + %s/CL", folder)
                            else:
                                log.warning("[ZIP] CL missing: %s", cl)
                    mb = os.path.getsize(zip_path) / (1024 * 1024)
                    log.info("[CV] Step D DONE: %s (%d files, %.1fMB)", zip_path, files_added, mb)
                except Exception as zip_err:
                    import traceback as _tb
                    log.error("[CV] Step D FAILED: %s", zip_err)
                    log.error(_tb.format_exc())
                    zip_path = None
            else:
                log.warning("[CV] No packs generated - ZIP skipped")

    log.info("[CV] COMPLETE: packs=%d zip=%s", len(application_packs), zip_path)
    log.info("=" * 50)
    # ── Send email ────────────────────────────────────────────────
    send_email(top_jobs, application_packs, zip_path)

    # ── Save sent jobs to Excel tracker ──────────────────────────
    try:
        from job_tracker import append_jobs_to_tracker
        added, skipped = append_jobs_to_tracker(top_jobs)
        log.info("[TRACKER] %d jobs logged to tracker (%d already existed)", len(added), skipped)
    except Exception as e:
        log.error("[TRACKER] Could not update tracker (%s) — falling back to seen_jobs.json", e)
        seen.update(seen_this_run)
        save_seen(seen)

    log.info("[DONE] Complete.")


# ═══════════════════════════════════════════════════════════════════
#  EMAIL BUILDER — beautiful HTML digest
# ═══════════════════════════════════════════════════════════════════

def build_email_html(jobs: list, application_packs: list = None) -> str:
    application_packs = application_packs or []
    today = datetime.now().strftime("%A %d %B %Y")

    # Source pills
    source_counts = {}
    for j in jobs:
        source_counts[j["source"]] = source_counts.get(j["source"], 0) + 1
    source_pills = " ".join(
        '<span style="background:#e8f4fd;color:#1a6fa8;padding:2px 8px;'
        'border-radius:12px;font-size:11px;margin:2px;display:inline-block">'
        + s + " (" + str(c) + ")</span>"
        for s, c in source_counts.items()
    )

    # Sponsorship badge styles
    SPONS = {
        "CONFIRMED": ("VISA SPONSOR CONFIRMED", "#276749", "#c6f6d5", "#38a169"),
        "LIKELY":    ("LIKELY SPONSOR",          "#744210", "#fefcbf", "#d69e2e"),
        "UNKNOWN":   ("VERIFY SPONSORSHIP",      "#7b3a3a", "#fff5f5", "#c53030"),
    }

    # Build job cards
    cards_html = ""
    for i, job in enumerate(jobs, 1):
        # Priority badge
        is_high = job["title"] in HIGH_PRIORITY or any(
            t.lower() in job["title"].lower() for t in HIGH_PRIORITY
        )
        pri_label = "HIGH PRIORITY" if is_high else "Secondary"
        pri_color = "#1a6fa8"       if is_high else "#6c757d"
        pri_badge = (
            '<span style="font-size:10px;font-weight:700;color:' + pri_color +
            ';text-transform:uppercase;letter-spacing:0.5px">' + pri_label + "</span>"
        )

        # Source badge
        src_badge = (
            '<span style="background:#f0f4f8;color:#5a6473;font-size:10px;'
            'padding:2px 7px;border-radius:10px;font-weight:600">'
            + job["source"] + "</span>"
        )

        # Sponsorship badge
        status  = job.get("sponsorship_status", "UNKNOWN")
        reason  = job.get("sponsorship_reason", "")
        s_label, s_text, s_bg, s_border = SPONS.get(status, SPONS["UNKNOWN"])
        reason_safe = reason[:90].replace("<", "&lt;").replace(">", "&gt;")
        spons_html = (
            '<div style="margin:6px 0 8px">'
            '<span style="background:' + s_bg + ';color:' + s_text +
            ';border:1px solid ' + s_border +
            ';padding:3px 10px;border-radius:12px;font-size:10px;font-weight:800">'
            + s_label + "</span>"
            + ('<span style="font-size:10px;color:#6b7280;margin-left:8px">'
               + reason_safe + ("..." if len(reason) > 90 else "") + "</span>"
               if reason_safe else "")
            + "</div>"
        )

        # Description
        desc = job["description"][:220].strip().replace("<", "&lt;").replace(">", "&gt;")
        if len(job["description"]) > 220:
            desc += "..."

        # Has application pack?
        has_pack = any(
            p.get("job_number") == i or
            (p.get("job_title","").lower() == job["title"].lower() and
             p.get("company","").lower() == job["company"].lower())
            for p in application_packs
        )
        pack_tag = (
            '<span style="background:#c6f6d5;color:#276749;font-size:10px;'
            'padding:2px 8px;border-radius:10px;font-weight:700;margin-left:8px">'
            "CV + Cover Letter Ready</span>" if has_pack else ""
        )

        cards_html += (
            '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
            'padding:20px;margin-bottom:16px;border-left:4px solid ' + s_border + ';">'
            '<div style="display:flex;justify-content:space-between;align-items:flex-start;'
            'flex-wrap:wrap;gap:6px;margin-bottom:4px">'
            '<span style="font-size:13px;font-weight:800;color:#1a2636">'
            "#" + str(i) + " &middot; " + job["title"] + pack_tag + "</span>"
            + src_badge + "</div>"
            '<div style="font-size:12px;color:#374151;margin-bottom:2px">'
            "<strong>" + job["company"] + "</strong> &nbsp;|&nbsp; " + job["location"] + "</div>"
            '<div style="font-size:12px;color:#374151;margin-bottom:4px">'
            "<strong>" + job["salary"] + "</strong> &nbsp;|&nbsp; " + pri_badge + "</div>"
            + spons_html
            + '<p style="font-size:11px;color:#5a6473;margin:0 0 12px;line-height:1.5">'
            + desc + "</p>"
            '<a href="' + job["url"] + '" style="background:#1a6fa8;color:#ffffff;'
            'padding:8px 18px;border-radius:6px;text-decoration:none;'
            'font-size:12px;font-weight:700;display:inline-block">'
            "View &amp; Apply &rarr;</a></div>"
        )

    # Application packs summary bar
    if application_packs:
        packs_bar = (
            '<div style="background:#f0fff4;border:1px solid #68d391;border-radius:10px;'
            'padding:16px 20px;margin-bottom:20px">'
            '<div style="font-size:13px;font-weight:800;color:#22543d;margin-bottom:8px">'
            "&#x1F4CE; Your Application Pack ZIP is attached — "
            + str(len(application_packs)) + " tailored CVs &amp; Cover Letters ready to send!</div>"
            '<div style="font-size:11px;color:#276749">'
            "Open the ZIP, find the folder for each job, review the Word docs, and hit send. "
            "Each CV and cover letter is uniquely tailored to that specific role.</div></div>"
        )
    else:
        packs_bar = (
            '<div style="background:#f7faff;border:1px solid #bee3f8;border-radius:8px;'
            'padding:14px 18px;margin-bottom:20px;font-size:12px;color:#2c5282">'
            "<strong>CV Tailoring:</strong> Add <code>ANTHROPIC_API_KEY</code> "
            "to GitHub Secrets to receive 20 tailored CVs and cover letters daily.</div>"
        )

    # Assemble full HTML using list join to avoid all string issues
    parts = []
    parts.append("<!DOCTYPE html><html lang='en'><head>")
    parts.append('<meta charset="UTF-8">')
    parts.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    parts.append("<title>Daily Job Digest " + today + "</title>")
    parts.append("</head>")
    parts.append('<body style="margin:0;padding:0;background:#f4f7fb;font-family:Arial,sans-serif">')
    parts.append('<div style="max-width:680px;margin:30px auto">')

    # Header
    parts.append('<div style="background:linear-gradient(135deg,#1a3a5c 0%,#1a6fa8 100%);border-radius:12px 12px 0 0;padding:28px 32px 22px">')
    parts.append('<div style="color:#7ec8e3;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Daily Job Digest</div>')
    parts.append('<h1 style="color:#ffffff;margin:0 0 4px;font-size:22px;font-weight:800">Ishaan Kumar &mdash; Water Engineering Jobs</h1>')
    parts.append('<div style="color:#a8d8f0;font-size:13px">' + today + ' &nbsp;|&nbsp; ' + str(len(jobs)) + ' new opportunities &nbsp;|&nbsp; London &amp; South East + EU</div>')
    parts.append('</div>')

    # Stats bar
    parts.append('<div style="background:#1a3a5c;padding:12px 32px;display:flex;flex-wrap:wrap;gap:6px;align-items:center">')
    parts.append('<span style="color:#7ec8e3;font-size:11px;font-weight:700;margin-right:6px">SOURCES TODAY:</span>')
    parts.append(source_pills)
    parts.append('</div>')

    # Body
    parts.append('<div style="background:#f4f7fb;padding:24px">')

    # Tip box
    parts.append('<div style="background:#fff8e7;border:1px solid #ffd966;border-radius:8px;padding:14px 18px;margin-bottom:20px;font-size:12px;color:#7a5a00">')
    parts.append('<strong>30-Day Tip:</strong> Green = confirmed UK sponsor register. Yellow = likely sponsor. Red = verify before applying. Grey jobs removed automatically.</div>')

    # Packs bar
    parts.append(packs_bar)

    # Job cards
    parts.append(cards_html)

    # Footer note
    parts.append('<div style="background:#e8f4fd;border-radius:8px;padding:14px 18px;margin-top:8px;font-size:12px;color:#1a3a5c">')
    parts.append('<strong>Application tip:</strong> Lead every cover letter with your <strong>NAV &amp; Self-Lay end-to-end experience</strong>, <strong>first-time Thames Water/Affinity Water approvals</strong>, and your <strong>&pound;20M portfolio</strong>. These are rare differentiators.</div>')
    parts.append('</div>')

    # Footer
    parts.append('<div style="background:#2d3748;border-radius:0 0 12px 12px;padding:16px 32px;text-align:center">')
    parts.append('<p style="color:#8896a7;font-size:11px;margin:0">Auto-generated daily at 8am &middot; Adzuna &middot; Reed &middot; Indeed &middot; Totaljobs &middot; CV-Library &middot; CWJobs &middot; New Civil Engineer</p>')
    parts.append('</div></div></body></html>')

    return "".join(parts)



def send_email(jobs: list, application_packs: list = None, zip_path: str = None):
    application_packs = application_packs or []

    if not EMAIL_FROM or not EMAIL_PASSWORD:
        log.error("EMAIL_FROM or EMAIL_PASSWORD not set — cannot send email")
        with open("email_preview.html", "w") as f:
            f.write(build_email_html(jobs, application_packs))
        log.info("Email preview saved to email_preview.html")
        return

    today = datetime.now().strftime("%d %B %Y")
    pack_count = len(application_packs)
    zip_size   = ""
    if zip_path and os.path.exists(zip_path):
        mb = os.path.getsize(zip_path) / (1024 * 1024)
        zip_size = f" ({mb:.1f}MB)"

    subject = (
        f"[JOBS] {len(jobs)} Water Engineering Jobs + {pack_count} Tailored CVs & Cover Letters — {today}"
        if pack_count else
        f"[JOBS] {len(jobs)} New Water Engineering Jobs — {today}"
    )

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO

    # ── Plain text body ───────────────────────────────────────────
    plain_lines = [f"Your Daily Job Digest — {today}", "=" * 50]
    for i, job in enumerate(jobs, 1):
        plain_lines.append(f"\n#{i} {job['title']} @ {job['company']}")
        plain_lines.append(f"   Location: {job['location']}  |  Salary: {job['salary']}")
        plain_lines.append(f"   Sponsor:  {job.get('sponsorship_status','?')} — {job.get('sponsorship_reason','')[:60]}")
        plain_lines.append(f"   Link:     {job['url']}")
    if pack_count:
        plain_lines += ["", "=" * 50,
                        f"ATTACHED: {zip_path or 'application_packs.zip'}{zip_size}",
                        f"Contains {pack_count} tailored CVs + {pack_count} cover letters.",
                        "Each folder = one job. Open in Word, review, then send!"]

    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText("\n".join(plain_lines), "plain"))
    body_part.attach(MIMEText(build_email_html(jobs, application_packs), "html"))
    msg.attach(body_part)

    # ── Attach single ZIP file ────────────────────────────────────
    from email.mime.base import MIMEBase
    from email import encoders

    if zip_path and os.path.exists(zip_path):
        try:
            with open(zip_path, "rb") as f:
                part = MIMEBase("application", "zip")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment",
                            filename=os.path.basename(zip_path))
            msg.attach(part)
            log.info(f"[ATTACHED] {zip_path}{zip_size}")
        except Exception as e:
            log.error(f"Failed to attach ZIP: {e}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        log.info(f"[OK] Email sent to {EMAIL_TO} — {pack_count} packs in ZIP{zip_size}")
    except Exception as e:
        log.error(f"Failed to send email: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    run()
