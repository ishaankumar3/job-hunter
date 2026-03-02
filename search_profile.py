#!/usr/bin/env python3
"""
ISHAAN KUMAR - PRECISE JOB PROFILE
Indian National | 3.5 Years | Water Design Engineer | Needs Visa Sponsorship
"""

# ═══════════════════════════════════════════════════════════════════
#  HARD REQUIREMENTS - Title MUST match one of these patterns
# ═══════════════════════════════════════════════════════════════════

REQUIRED_TITLE_PATTERNS = [
    # Pattern 1: Water + Design (EXACT match)
    ("water", "design"),
    ("water", "designer"),
    
    # Pattern 2: Hydraulic + Design (EXACT match)
    ("hydraulic", "design"),
    ("hydraulic", "model"),
    
    # Pattern 3: Specific tools (EXACT match)
    ("watergems",),
    ("infoworks",),
    
    # Pattern 4: NAV/Self-Lay (EXACT match)
    ("nav", "engineer"),
    ("self-lay",),
    ("self lay",),
    
    # Pattern 5: Water Network (NOT "network engineer" alone)
    ("water network",),
    ("water distribution",),
    ("water infrastructure",),
    ("water mains",),
]

# ═══════════════════════════════════════════════════════════════════
#  HARD BLOCKS - Instant rejection
# ═══════════════════════════════════════════════════════════════════

BLOCKED_TITLE_TERMS = [
    # SENIORITY - Check these FIRST (most specific to least)
    "graduate ", " graduate", "grad ",  # catches "graduate engineer", "engineer graduate"
    "junior ", " junior",
    "senior ", " senior",
    "principal ", " principal",
    "lead ", " lead",
    "chief ", " chief",
    "director", "head of", "associate director",
    "apprentice", "trainee", "intern",
    "entry level", "entry-level",
    
    # CONSTRUCTION/SITE - You're DESIGN, not construction
    "site engineer", "site agent", "site manager", "site supervisor",
    "resident engineer", "construction engineer", "construction manager",
    "contracts engineer", "field engineer", "commissioning engineer",
    "installation engineer", "project engineer",  # too vague
    
    # IT/TELECOMS - Not water networks
    "network engineer",  # IT role (we allow "water network engineer")
    "network administrator", "network architect", "network technician",
    "it engineer", "systems engineer", "systems administrator",
    "software engineer", "software developer", "devops", "cloud engineer",
    "linux engineer", "unix engineer", "windows engineer",
    "telecoms engineer", "telecommunications", "fiber engineer",
    "data engineer", "database engineer",
    
    # ELECTRICAL/POWER
    "electrical engineer", "electrical design", "electrician",
    "power engineer", "power systems", "hv engineer", "lv engineer",
    "substation", "switchgear", "control engineer", "c&i engineer",
    "scada engineer", "instrumentation", "automation engineer",
    
    # PLUMBING/HVAC/MEP
    "plumber", "plumbing engineer", "plumbing design",
    "hvac engineer", "hvac design", "heating engineer",
    "m&e engineer", "mep engineer", "building services",
    "mechanical engineer",  # unless water-specific
    
    # OPERATIONS/MAINTENANCE - You're DESIGN, not operations
    "operator", "plant operator", "process operator",
    "water treatment operator", "wwtw operator", "wtp operator",
    "maintenance engineer", "maintenance technician", "mechanic",
    "technician", "fitter", "welder", "fabricator",
    
    # WASTEWATER TREATMENT - Different from network design
    "wastewater treatment plant", "sewage treatment", "wwtw", "wtp",
    "treatment plant engineer", "process engineer",  # unless design
    
    # COMMERCIAL/MANAGEMENT
    "quantity surveyor", "qs ", " qs", "cost consultant", "estimator",
    "commercial manager", "procurement", "contracts manager",
    "programme manager",  # unless technical
    
    # WRONG INFRASTRUCTURE
    "highways engineer", "road engineer", "transport engineer",
    "railway engineer", "rail engineer", "bridge engineer",
    "structural engineer", "geotechnical engineer", "tunnelling",
    
    # BUILDING SYSTEMS
    "escalator", "lift engineer", "elevator", "fire engineer",
    "sprinkler", "security systems", "access control",
    
    # MANUFACTURING/MATERIALS
    "composite engineer", "materials engineer", "manufacturing engineer",
    "production engineer", "quality engineer", "test engineer",
]

# ═══════════════════════════════════════════════════════════════════
#  POSITIVE KEYWORDS - Scoring
# ═══════════════════════════════════════════════════════════════════

WATER_DESIGN_KEYWORDS = {
    # Software/Tools (50 points each)
    "watergems": 50, "infoworks": 50, "infowater": 50,
    "autocad": 30, "civil 3d": 30, "revit": 30,
    "arcgis": 20, "microstation": 20,
    
    # Design work (40 points)
    "water network design": 40, "water mains design": 40,
    "hydraulic modelling": 40, "hydraulic design": 40,
    "pipe network design": 30, "distribution network": 30,
    
    # UK Specific (30 points)
    "section 104": 30, "section 185": 30, "section 38": 30,
    "sewers for adoption": 30, "sfa": 30, "wras": 30,
    "nav": 30, "self-lay": 30, "self lay": 30,
    "developer services": 30,
    
    # AMP Programmes (25 points)
    "amp7": 25, "amp8": 25, "amp 7": 25, "amp 8": 25,
    
    # Water Companies (20 points each)
    "thames water": 20, "affinity water": 20, "severn trent": 20,
    "anglian water": 20, "united utilities": 20, "yorkshire water": 20,
    "southern water": 20, "south west water": 20,
    
    # General water terms (15 points)
    "water distribution": 15, "water supply": 15, "potable water": 15,
    "clean water": 15, "water infrastructure": 15,
    
    # Technical (10 points)
    "pressure analysis": 10, "flow analysis": 10, "fire flow": 10,
    "pipe sizing": 10, "network calibration": 10,
    "dwi": 10, "ofwat": 10, "cdm": 10,
}

# ═══════════════════════════════════════════════════════════════════
#  WORLDWIDE SEARCH - Countries + Queries
# ═══════════════════════════════════════════════════════════════════

COUNTRIES = [
    # English-speaking (high priority)
    ("UK", "United Kingdom"),
    ("Australia", "Australia"),
    ("Canada", "Canada"),
    ("New Zealand", "New Zealand"),
    ("Ireland", "Ireland"),
    ("Singapore", "Singapore"),
    
    # Middle East (visa sponsorship common)
    ("UAE", "United Arab Emirates"),
    ("Qatar", "Qatar"),
    ("Saudi Arabia", "Saudi Arabia"),
    ("Oman", "Oman"),
    ("Bahrain", "Bahrain"),
    
    # Europe (Blue Card)
    ("Germany", "Germany"),
    ("Netherlands", "Netherlands"),
    ("Belgium", "Belgium"),
    ("Switzerland", "Switzerland"),
    ("Norway", "Norway"),
    ("Sweden", "Sweden"),
    
    # USA (H1B)
    ("USA", "United States"),
]

SEARCH_QUERIES = [
    # Core searches (all countries)
    "water design engineer",
    "water network design engineer",
    "hydraulic design engineer",
    "hydraulic modeller",
    "watergems engineer",
    "water distribution engineer",
    "water infrastructure design",
    
    # With visa keywords
    "water engineer visa sponsorship",
    "hydraulic engineer visa sponsorship",
    "water design engineer sponsorship",
    "water engineer international",
    "water engineer relocation",
    
    # NAV/UK specific
    "NAV design engineer",
    "self-lay engineer",
    "developer services water",
    "section 104 engineer",
    
    # Country-specific
    "water engineer Australia",
    "water engineer Canada",
    "water engineer Singapore",
    "water engineer UAE",
    "water engineer Germany",
    "water engineer New Zealand",
]

# ═══════════════════════════════════════════════════════════════════
#  VISA SPONSORSHIP KEYWORDS (bonus points)
# ═══════════════════════════════════════════════════════════════════

SPONSORSHIP_KEYWORDS = [
    "visa sponsorship", "tier 2 sponsorship", "skilled worker visa",
    "relocation assistance", "relocation package", "international candidates",
    "overseas candidates", "global candidates", "work permit",
    "skilled migration", "sponsorship available", "sponsorship provided",
]
