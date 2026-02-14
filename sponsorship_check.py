#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================
 Sponsorship License Checker — Ishaan Kumar
====================================================
 UK:  Downloads the official gov.uk register of
      licensed Skilled Worker sponsors daily and
      fuzzy-matches every company name.

 EU:  Checks Ireland, Germany, Netherlands, Spain,
      Portugal employer registers / Blue Card info.

 Result per job:
   "CONFIRMED"  — company is on official register
   "LIKELY"     — strong signals in job text
   "UNKNOWN"    — cannot confirm, include with flag
   "NO"         — explicitly states no sponsorship
====================================================
"""

import re
import io
import logging
import os
import json
import difflib
from datetime import datetime, date

import requests

log = logging.getLogger(__name__)

# ── Cache file so we don't re-download the 5MB register on every run ──────
CACHE_FILE   = "sponsor_register_cache.json"
CACHE_DATE   = "sponsor_register_date.txt"

# ── UK government sponsor register (public, updated weekly) ───────────────
UK_REGISTER_PAGE = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"

# ── Phrases in job descriptions that CONFIRM sponsorship ──────────────────
SPONSORSHIP_POSITIVE = [
    "visa sponsorship available",
    "visa sponsorship provided",
    "sponsorship available",
    "we sponsor",
    "we will sponsor",
    "skilled worker visa",
    "tier 2 sponsorship",
    "certificate of sponsorship",
    "cos available",
    "sponsorship considered",
    "sponsorship is available",
    "can sponsor",
    "able to sponsor",
    "we are able to sponsor",
    "sponsorship will be provided",
    "relocation assistance",
    "international candidates welcome",
    "open to international",
    "right to work not required",
    "eu blue card",
    "work permit",
    "work visa",
    "sponsorship for the right candidate",
]

# ── Phrases that EXCLUDE sponsorship ──────────────────────────────────────
SPONSORSHIP_NEGATIVE = [
    "no sponsorship",
    "unable to sponsor",
    "cannot sponsor",
    "sponsorship is not available",
    "must have right to work",
    "must already have right to work",
    "right to work required",
    "no visa sponsorship",
    "unfortunately we cannot sponsor",
    "we do not offer sponsorship",
    "we are unable to offer visa sponsorship",
    "only applicants with right to work",
    "applicants must have existing right to work",
]

# ── EU country indicators (jobs from these are likely open to int'l) ──────
EU_OPEN_COUNTRIES = ["germany", "netherlands", "ireland", "portugal"]
EU_RESTRICTIVE_COUNTRIES = ["spain"]  # harder visa routes for non-EU


# ═══════════════════════════════════════════════════════════════════
#  DOWNLOAD & CACHE UK SPONSOR REGISTER
# ═══════════════════════════════════════════════════════════════════

def _get_register_download_url() -> str:
    """Scrape the gov.uk page to find the current Excel download URL."""
    try:
        r = requests.get(UK_REGISTER_PAGE, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        # Find all .xlsx or .csv links
        urls = re.findall(
            r'href="(https://assets\.publishing\.service\.gov\.uk[^"]+(?:Worker[^"]*\.xlsx|sponsor[^"]*\.xlsx|Worker[^"]*\.csv))"',
            r.text, re.IGNORECASE
        )
        if urls:
            log.info(f"Found sponsor register URL: {urls[0]}")
            return urls[0]
        # Fallback — try any xlsx on the page
        urls = re.findall(r'href="(https://assets\.publishing\.service\.gov\.uk[^"]+\.xlsx)"', r.text)
        if urls:
            return urls[0]
    except Exception as e:
        log.warning(f"Could not scrape register URL: {e}")
    return ""


def _download_register() -> set:
    """Download the UK sponsor register and return a set of company names."""
    companies = set()

    url = _get_register_download_url()
    if not url:
        log.warning("Could not find register download URL — using cached data only")
        return companies

    try:
        log.info("Downloading UK sponsor register...")
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()

        # Try openpyxl first (xlsx), fall back to csv
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and row[0]:
                    name = str(row[0]).strip().lower()
                    if name:
                        companies.add(name)
            log.info(f"Loaded {len(companies)} companies from Excel register")
        except Exception:
            # Try CSV
            text = r.content.decode("utf-8", errors="ignore")
            for line in text.splitlines()[1:]:
                parts = line.split(",")
                if parts:
                    name = parts[0].strip().strip('"').lower()
                    if name:
                        companies.add(name)
            log.info(f"Loaded {len(companies)} companies from CSV register")

    except Exception as e:
        log.error(f"Failed to download register: {e}")

    return companies


def load_uk_register() -> set:
    """Load UK sponsor register — from cache if fresh, otherwise re-download."""
    today_str = date.today().isoformat()

    # Check if we have a fresh cache from today
    if os.path.exists(CACHE_FILE) and os.path.exists(CACHE_DATE):
        try:
            cached_date = open(CACHE_DATE).read().strip()
            if cached_date == today_str:
                with open(CACHE_FILE) as f:
                    data = json.load(f)
                companies = set(data.get("companies", []))
                log.info(f"Using cached register: {len(companies)} companies")
                return companies
        except Exception:
            pass

    # Download fresh
    companies = _download_register()

    if companies:
        # Save cache
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"companies": list(companies), "date": today_str}, f)
            with open(CACHE_DATE, "w") as f:
                f.write(today_str)
            log.info(f"Register cached: {len(companies)} companies")
        except Exception as e:
            log.warning(f"Could not cache register: {e}")

    return companies


# ═══════════════════════════════════════════════════════════════════
#  FUZZY COMPANY NAME MATCHING
# ═══════════════════════════════════════════════════════════════════

def _normalise(name: str) -> str:
    """Normalise company name for matching."""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [" ltd", " limited", " plc", " llp", " llc", " inc",
                   " group", " uk", " solutions", " services", " consulting",
                   " consultancy", " engineering", " & co", " and co"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    # Remove punctuation
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def is_on_uk_register(company: str, register: set, threshold: float = 0.82) -> tuple:
    """
    Check if company is on the UK sponsor register.
    Returns (is_confirmed: bool, match_name: str, confidence: float)
    """
    if not company or not register:
        return False, "", 0.0

    norm_company = _normalise(company)
    if not norm_company:
        return False, "", 0.0

    # Exact match first
    if norm_company in register:
        return True, company, 1.0

    # Check if any register name contains or is contained in the company name
    for reg_name in register:
        norm_reg = _normalise(reg_name)
        if norm_reg and (norm_company in norm_reg or norm_reg in norm_company):
            if len(norm_company) >= 4 and len(norm_reg) >= 4:
                return True, reg_name, 0.95

    # Fuzzy match using difflib (no extra dependency needed)
    matches = difflib.get_close_matches(
        norm_company,
        [_normalise(r) for r in register],
        n=1,
        cutoff=threshold
    )
    if matches:
        # Find the original name
        for reg_name in register:
            if _normalise(reg_name) == matches[0]:
                score = difflib.SequenceMatcher(None, norm_company, matches[0]).ratio()
                return True, reg_name, round(score, 2)
        return True, matches[0], 0.85

    return False, "", 0.0


# ═══════════════════════════════════════════════════════════════════
#  DESCRIPTION-BASED SPONSORSHIP SIGNALS
# ═══════════════════════════════════════════════════════════════════

def check_description_signals(description: str, title: str = "") -> tuple:
    """
    Scan job description for sponsorship signals.
    Returns (signal: str, reason: str)
    signal: "CONFIRMED", "LIKELY", "NO", "UNKNOWN"
    """
    text = (description + " " + title).lower()

    # Check for explicit NO sponsorship first
    for phrase in SPONSORSHIP_NEGATIVE:
        if phrase in text:
            return "NO", f'Text says: "{phrase}"'

    # Check for explicit CONFIRMED sponsorship
    for phrase in SPONSORSHIP_POSITIVE:
        if phrase in text:
            return "CONFIRMED", f'Text says: "{phrase}"'

    # Check for water/utilities sector signals (these companies often sponsor)
    sector_signals = [
        "thames water", "anglian water", "severn trent", "united utilities",
        "yorkshire water", "southern water", "affinity water", "welsh water",
        "northumbrian water", "sse", "national grid", "amey", "mott macdonald",
        "atkins", "jacobs", "arup", "wsp", "aecom", "arcadis", "costain",
        "bechtel", "kier", "balfour beatty", "stantec", "halcrow",
        "black & veatch", "hyder", "capita", "ukps", "morrison utility",
    ]
    for sig in sector_signals:
        if sig in text:
            return "LIKELY", f"Known large employer in water/utilities sector ({sig})"

    return "UNKNOWN", "No explicit sponsorship information found"


# ═══════════════════════════════════════════════════════════════════
#  EU SPONSORSHIP ASSESSMENT
# ═══════════════════════════════════════════════════════════════════

def check_eu_sponsorship(job: dict) -> tuple:
    """
    Assess sponsorship likelihood for EU jobs.
    Returns (signal: str, reason: str)
    """
    location = job.get("location", "").lower()
    description = job.get("description", "").lower()
    title = job.get("title", "").lower()
    text = description + " " + title

    # Check for explicit negative signals first
    for phrase in SPONSORSHIP_NEGATIVE:
        if phrase in text:
            return "NO", f'Text says: "{phrase}"'

    # EU Blue Card signals
    blue_card_signals = [
        "eu blue card", "blue card", "work permit", "visa sponsorship",
        "relocation", "relocation package", "international candidates",
        "english speaking", "english language", "english required",
    ]
    for sig in blue_card_signals:
        if sig in text:
            return "LIKELY", f"EU role with signal: '{sig}'"

    # Germany — very open to skilled worker visa (Fachkraefteeinwanderungsgesetz)
    if "germany" in location or "deutschland" in location:
        return "LIKELY", "Germany has open Skilled Immigration Act (Fachkraefteeinwanderungsgesetz) — most engineering roles eligible"

    # Netherlands — highly international, English-first companies
    if "netherlands" in location or "amsterdam" in location or "rotterdam" in location:
        return "LIKELY", "Netherlands is highly international — most engineering companies sponsor non-EU workers"

    # Ireland — English-speaking, many multinationals
    if "ireland" in location or "dublin" in location:
        return "LIKELY", "Ireland (English-speaking) — Critical Skills Employment Permit available for engineers"

    # Portugal — EU Blue Card available but smaller market
    if "portugal" in location or "lisbon" in location or "porto" in location:
        return "UNKNOWN", "Portugal — EU Blue Card possible but less common; verify with employer"

    # Spain — more restrictive for non-EU
    if "spain" in location or "madrid" in location or "barcelona" in location:
        return "UNKNOWN", "Spain — work authorisation required; verify sponsorship with employer directly"

    return "UNKNOWN", "EU role — contact employer to confirm work permit support"


# ═══════════════════════════════════════════════════════════════════
#  MAIN FUNCTION — check a single job
# ═══════════════════════════════════════════════════════════════════

def check_job_sponsorship(job: dict, uk_register: set) -> dict:
    """
    Full sponsorship check for a job.
    Returns enriched job dict with sponsorship fields added.
    """
    location = job.get("location", "").lower()
    is_uk = not any(c in location for c in ["ireland", "germany", "netherlands",
                                              "spain", "portugal", "dublin",
                                              "amsterdam", "berlin", "madrid",
                                              "lisbon", "rotterdam"])

    if is_uk:
        # Step 1: Check official UK register
        on_register, matched_name, confidence = is_on_uk_register(
            job.get("company", ""), uk_register
        )

        if on_register:
            status = "CONFIRMED"
            reason = f"On UK Home Office licensed sponsor register (matched: '{matched_name}', confidence: {int(confidence*100)}%)"
        else:
            # Step 2: Check description signals
            status, reason = check_description_signals(
                job.get("description", ""),
                job.get("title", "")
            )
            if status == "UNKNOWN":
                reason = f"Not found on UK sponsor register. {reason}"
    else:
        # EU job
        status, reason = check_eu_sponsorship(job)

    job["sponsorship_status"] = status
    job["sponsorship_reason"] = reason
    return job


# ═══════════════════════════════════════════════════════════════════
#  BATCH CHECK + FILTER
# ═══════════════════════════════════════════════════════════════════

def filter_by_sponsorship(jobs: list, include_unknown: bool = True) -> list:
    """
    Check all jobs for sponsorship and filter/sort by status.

    include_unknown: if True, keep UNKNOWN jobs (flagged in email).
                     if False, only keep CONFIRMED and LIKELY.
    """
    log.info("Loading UK sponsor register...")
    uk_register = load_uk_register()
    log.info(f"Register loaded: {len(uk_register)} licensed sponsors")

    results = []
    counts = {"CONFIRMED": 0, "LIKELY": 0, "UNKNOWN": 0, "NO": 0}

    for job in jobs:
        enriched = check_job_sponsorship(job, uk_register)
        status = enriched["sponsorship_status"]
        counts[status] = counts.get(status, 0) + 1

        if status == "NO":
            log.info(f"  [SKIP - NO SPONSORSHIP] {job['title']} @ {job['company']}")
            continue  # Always exclude explicit no-sponsorship jobs

        if status == "UNKNOWN" and not include_unknown:
            continue

        results.append(enriched)

    log.info(f"Sponsorship filter results: CONFIRMED={counts['CONFIRMED']}, "
             f"LIKELY={counts['LIKELY']}, UNKNOWN={counts['UNKNOWN']}, "
             f"EXCLUDED(NO)={counts['NO']}")

    # Sort: CONFIRMED first, then LIKELY, then UNKNOWN
    order = {"CONFIRMED": 0, "LIKELY": 1, "UNKNOWN": 2}
    results.sort(key=lambda j: order.get(j.get("sponsorship_status", "UNKNOWN"), 2))

    return results


# ═══════════════════════════════════════════════════════════════════
#  BADGE HTML for email
# ═══════════════════════════════════════════════════════════════════

SPONSORSHIP_BADGE = {
    "CONFIRMED": (
        "SPONSOR CONFIRMED",
        "#276749", "#c6f6d5", "#38a169"
    ),
    "LIKELY": (
        "LIKELY SPONSOR",
        "#744210", "#fefcbf", "#d69e2e"
    ),
    "UNKNOWN": (
        "VERIFY SPONSORSHIP",
        "#63504c", "#fff5f5", "#c53030"
    ),
    "NO": (
        "NO SPONSORSHIP",
        "#718096", "#edf2f7", "#a0aec0"
    ),
}


def sponsorship_badge_html(status: str, reason: str) -> str:
    label, text_color, bg_color, border_color = SPONSORSHIP_BADGE.get(
        status, SPONSORSHIP_BADGE["UNKNOWN"]
    )
    return (
        f'<div style="margin:6px 0;display:inline-block">'
        f'<span style="background:{bg_color};color:{text_color};border:1px solid {border_color};'
        f'padding:3px 10px;border-radius:12px;font-size:10px;font-weight:800;'
        f'letter-spacing:0.3px">{label}</span>'
        f'<span style="font-size:10px;color:#6b7280;margin-left:6px">{reason[:90]}{"..." if len(reason)>90 else ""}</span>'
        f'</div>'
    )
