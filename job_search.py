#!/usr/bin/env python3
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
JOBS_PER_EMAIL   = 20
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

def score_job(title: str, description: str, salary_min=None, salary_max=None) -> int:
    score = 0
    text = f"{title} {description}".lower()

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

    for query in SEARCH_QUERIES[:6]:  # limit API calls
        try:
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": 20,
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
            time.sleep(1)
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
                "results_per_page": 10,
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
            time.sleep(1)
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
                "resultsToTake": 20,
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
            time.sleep(1)
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


def fetch_rss_feeds() -> list:
    jobs = []
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                title   = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                link    = entry.get("link", "")
                company = _extract_company(entry)
                location= _extract_location(entry, source_name)

                if not title or not link:
                    continue

                # Quick relevance filter — must contain at least one water/engineering keyword
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
            time.sleep(0.5)

        except Exception as e:
            log.error(f"RSS error [{source_name}]: {e}")

    log.info(f"RSS total: {len(jobs)} jobs")
    return jobs


# ═══════════════════════════════════════════════════════════════════
#  SOURCE 4 — ADDITIONAL SPECIALIST BOARDS (direct scraping)
# ═══════════════════════════════════════════════════════════════════

SPECIALIST_FEEDS = [
    # Water Utilities Jobs
    ("WaterUK Jobs",      "https://jobs.water.org.uk/jobs/feed/"),
    # Civil Engineering Jobs
    ("CE Jobs",           "https://www.civil.engineering.com/jobs/rss?keywords=water+engineer&location=London"),
    # Environment Jobs
    ("Environment Jobs",  "https://www.environmentjob.co.uk/jobs.rss?keywords=water+engineer"),
    # Jobs in Water
    ("Jobs in Water",     "https://www.jobsinwater.com/rss/feed.php?search=water+engineer&location=UK"),
    # Utility Professionals
    ("Utility People",    "https://www.utilitypeople.co.uk/jobs/feed/?keywords=water+engineer"),
]


def fetch_specialist_boards() -> list:
    jobs = []
    for source_name, url in SPECIALIST_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
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
            log.info(f"{source_name}: {len(feed.entries)} items")
            time.sleep(0.5)
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

    seen = load_seen()
    log.info(f"Previously seen jobs: {len(seen)}")

    # ── Collect from all sources ─────────────────────────────────
    all_jobs = []
    all_jobs += fetch_adzuna_uk()
    all_jobs += fetch_adzuna_eu()
    all_jobs += fetch_reed()
    all_jobs += fetch_rss_feeds()
    all_jobs += fetch_specialist_boards()

    log.info(f"Total raw jobs collected: {len(all_jobs)}")

    # ── Deduplicate ───────────────────────────────────────────────
    fresh_jobs = []
    new_ids = set()
    for job in all_jobs:
        jid = job_id(job["title"], job["company"], job["url"])
        if jid not in seen and jid not in new_ids:
            job["_id"] = jid
            fresh_jobs.append(job)
            new_ids.add(jid)

    log.info(f"Fresh (unseen) jobs: {len(fresh_jobs)}")

    # ── Score & rank ──────────────────────────────────────────────
    for job in fresh_jobs:
        job["_score"] = score_job(
            job["title"],
            job["description"],
            job.get("salary_min"),
            job.get("salary_max"),
        )

    fresh_jobs.sort(key=lambda j: j["_score"], reverse=True)

    top_jobs = fresh_jobs[:JOBS_PER_EMAIL]
    log.info(f"Top jobs selected for email: {len(top_jobs)}")

    if not top_jobs:
        log.warning("No new jobs found today — skipping email")
        return

    # ── Send email ────────────────────────────────────────────────
    send_email(top_jobs)

    # ── Update seen jobs ──────────────────────────────────────────
    seen.update(new_ids)
    save_seen(seen)

    log.info("✅ Done! Email sent and seen_jobs.json updated.")


# ═══════════════════════════════════════════════════════════════════
#  EMAIL BUILDER — beautiful HTML digest
# ═══════════════════════════════════════════════════════════════════

def build_email_html(jobs: list) -> str:
    today = datetime.now().strftime("%A %d %B %Y")
    day_number = datetime.now().day  # approximate day in 30-day plan

    source_counts = {}
    for j in jobs:
        source_counts[j["source"]] = source_counts.get(j["source"], 0) + 1

    source_pills = " ".join(
        f'<span style="background:#e8f4fd;color:#1a6fa8;padding:2px 8px;border-radius:12px;font-size:11px;margin:2px;display:inline-block">{s} ({c})</span>'
        for s, c in source_counts.items()
    )

    cards = ""
    for i, job in enumerate(jobs, 1):
        priority = "⭐ HIGH PRIORITY" if job["title"] in HIGH_PRIORITY or any(t.lower() in job["title"].lower() for t in HIGH_PRIORITY) else "Secondary"
        priority_color = "#1a6fa8" if "HIGH" in priority else "#6c757d"
        priority_badge = f'<span style="font-size:10px;font-weight:700;color:{priority_color};text-transform:uppercase;letter-spacing:0.5px">{priority}</span>'

        source_badge = f'<span style="background:#f0f4f8;color:#5a6473;font-size:10px;padding:2px 7px;border-radius:10px;font-weight:600">{job["source"]}</span>'

        cards += f"""
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:20px;margin-bottom:16px;border-left:4px solid #1a6fa8;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px">
            <span style="font-size:13px;font-weight:800;color:#1a2636;line-height:1.3">#{i} · {job['title']}</span>
            {source_badge}
          </div>
          <div style="margin:6px 0 4px;font-size:13px;color:#374151">
            🏢 <strong>{job['company']}</strong> &nbsp;|&nbsp; 📍 {job['location']}
          </div>
          <div style="margin-bottom:8px;font-size:13px;color:#374151">
            💷 <strong>{job['salary']}</strong> &nbsp;|&nbsp; {priority_badge}
          </div>
          <p style="font-size:12px;color:#5a6473;margin:0 0 12px;line-height:1.5">
            {job['description'][:220].strip()}{'...' if len(job['description']) > 220 else ''}
          </p>
          <a href="{job['url']}" style="background:#1a6fa8;color:#ffffff;padding:8px 18px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:700;display:inline-block">
            View & Apply →
          </a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Your Daily Job Digest — {today}</title>
</head>
<body style="margin:0;padding:0;background:#f4f7fb;font-family:'Segoe UI',Arial,sans-serif">
  <div style="max-width:680px;margin:30px auto;background:#f4f7fb">

    <!-- HEADER -->
    <div style="background:linear-gradient(135deg,#1a3a5c 0%,#1a6fa8 100%);border-radius:12px 12px 0 0;padding:30px 32px 24px">
      <div style="color:#7ec8e3;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">
        🔎 Daily Job Digest
      </div>
      <h1 style="color:#ffffff;margin:0 0 4px;font-size:22px;font-weight:800">Ishaan Kumar — Water Engineering Jobs</h1>
      <div style="color:#a8d8f0;font-size:13px">{today} &nbsp;|&nbsp; {len(jobs)} new opportunities &nbsp;|&nbsp; London & South East + EU</div>
    </div>

    <!-- STATS BAR -->
    <div style="background:#1a3a5c;padding:12px 32px;display:flex;flex-wrap:wrap;gap:6px;align-items:center">
      <span style="color:#7ec8e3;font-size:11px;font-weight:700;margin-right:6px">SOURCES TODAY:</span>
      {source_pills}
    </div>

    <!-- BODY -->
    <div style="background:#f4f7fb;padding:24px 24px">

      <!-- TIPS BOX -->
      <div style="background:#fff8e7;border:1px solid #ffd966;border-radius:8px;padding:14px 18px;margin-bottom:20px;font-size:12px;color:#7a5a00">
        <strong>💡 30-Day Plan Tip:</strong> Focus your first application energy on the ⭐ HIGH PRIORITY roles — these match your NAV/Self-Lay profile most closely.
        Aim for <strong>3 applications per day</strong> to hit your 30-day target.
      </div>

      {cards}

      <!-- FOOTER NOTE -->
      <div style="background:#e8f4fd;border-radius:8px;padding:14px 18px;margin-top:8px;font-size:12px;color:#1a3a5c">
        <strong>🎯 Application tip for today:</strong> Customise your cover letter to mention your <strong>NAV & Self-Lay end-to-end experience</strong>,
        your track record of <strong>first-time Thames Water / Affinity Water approvals</strong>,
        and your <strong>£20M portfolio</strong>. These are rare differentiators.
      </div>
    </div>

    <!-- FOOTER -->
    <div style="background:#2d3748;border-radius:0 0 12px 12px;padding:16px 32px;text-align:center">
      <p style="color:#8896a7;font-size:11px;margin:0">
        Auto-generated by your personal Job Hunter bot · Runs daily at 8am UK time<br>
        Searching: Adzuna · Reed · Indeed · Totaljobs · CV-Library · CWJobs · Jobsite · Guardian Jobs · New Civil Engineer · Specialist Boards
      </p>
    </div>

  </div>
</body>
</html>"""
    return html


def send_email(jobs: list):
    if not EMAIL_FROM or not EMAIL_PASSWORD:
        log.error("EMAIL_FROM or EMAIL_PASSWORD not set — cannot send email")
        # Dump to file as fallback
        with open("email_preview.html", "w") as f:
            f.write(build_email_html(jobs))
        log.info("Email preview saved to email_preview.html")
        return

    today = datetime.now().strftime("%d %B %Y")
    subject = f"🔎 {len(jobs)} New Water Engineering Jobs — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO

    # Plain text fallback
    plain_lines = [f"Your Daily Job Digest — {today}\n{'='*50}"]
    for i, job in enumerate(jobs, 1):
        plain_lines.append(f"\n#{i} {job['title']}")
        plain_lines.append(f"  Company:  {job['company']}")
        plain_lines.append(f"  Location: {job['location']}")
        plain_lines.append(f"  Salary:   {job['salary']}")
        plain_lines.append(f"  Source:   {job['source']}")
        plain_lines.append(f"  Link:     {job['url']}")
    plain_text = "\n".join(plain_lines)

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(build_email_html(jobs), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        log.info(f"✅ Email sent to {EMAIL_TO}")
    except Exception as e:
        log.error(f"Failed to send email: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    run()
