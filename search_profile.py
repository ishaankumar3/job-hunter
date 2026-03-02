#!/usr/bin/env python3
"""
BLACKLIST-ONLY approach: Block garbage, score everything else.
Get 40-50 jobs instead of 9.
"""

# ═══════════════════════════════════════════════════════════════════
#  HARD BLOCK - These are NEVER relevant
# ═══════════════════════════════════════════════════════════════════

BLOCKED_TITLE_TERMS = [
    # Electrical/Power (unless explicitly water-related)
    "electrical design engineer", "electrical engineer", "electrician",
    "power engineer", "hv engineer", "lv engineer", "substation",
    "c&i engineer", "scada engineer", "plc engineer", "controls engineer",
    
    # Plumbing/HVAC (unless explicitly water network design)
    "plumber", "plumbing engineer", "plumbing design",
    "hvac engineer", "hvac design", "heating engineer",
    "m&e engineer", "mep engineer", "mep design",
    "mechanical engineer", "mechanical design engineer",
    "building services engineer",
    
    # IT/Software
    "software engineer", "software developer", "linux engineer",
    "devops engineer", "cloud engineer", "it engineer",
    "it systems engineer", "systems administrator", "sysadmin", "it network engineer", "network administrator", "data engineer",
    "full stack", "backend", "frontend",
    
    # Wrong infrastructure type
    "highways engineer", "road engineer", "transport engineer",
    "railway engineer", "rail engineer", "bridge engineer",
    "structural engineer", "geotechnical engineer",
    
    # Building systems
    "escalator engineer", "lift engineer", "elevator engineer",
    "fire engineer", "fire systems", "sprinkler engineer",
    "security engineer", "access control",
    
    # Manufacturing/Materials
    "composite engineer", "materials engineer", "composites engineer",
    "manufacturing engineer", "production engineer",
    "process engineer", "r&d engineer", "test engineer",
    
    # Commercial/Construction Management
    "quantity surveyor", " qs ", "cost consultant", "estimator",
    "commercial manager", "contracts manager", "procurement",
    "project manager", "programme manager", "construction manager",
    "site manager",
    
    # Operations/Maintenance
    "maintenance engineer", "maintenance technician", "mechanic",
    "pipe fitter", "fitter", "welder", "fabricator",
    "operator", "plant operator", "technician",
    
    # Too junior
    "apprentice", "trainee", "intern", "graduate trainee",
    "graduate engineer", "graduate water", "graduate civil",
    "graduate hydraulic", "graduate design", "graduate role",
    "junior engineer", "junior water", "junior designer",
    "junior hydraulic", "junior civil",
    
    # Too senior (3.5 years experience = mid-level, not senior)
    "senior engineer", "senior water", "senior civil", "senior design",
    "senior hydraulic", "senior infrastructure", "senior utilities",
    "senior designer", "senior modeller", "senior consultant",
    "principal engineer", "principal water", "principal civil",
    "lead engineer", "lead water", "lead designer",
    "chief engineer", "chief water", "chief hydraulic", "head of", "director", "associate director",
]

# ═══════════════════════════════════════════════════════════════════
#  POSITIVE SCORING - Water engineering keywords
# ═══════════════════════════════════════════════════════════════════

WATER_KEYWORDS_HIGH = [
    # Direct water design (50 points each)
    "water design", "water network design", "water mains design",
    "water distribution", "water infrastructure design",
    "hydraulic design", "hydraulic modelling", "watergems",
    "nav engineer", "self-lay", "developer services water",
]

WATER_KEYWORDS_MEDIUM = [
    # Water context (25 points each)
    "water engineer", "water network", "water supply", "water infrastructure",
    "hydraulic engineer", "hydraulic", "clean water", "potable water",
    "water utilities", "water asset", "water mains",
    "section 104", "section 185", "section 38", "amp7", "amp8",
]

WATER_KEYWORDS_LOW = [
    # Technical terms (10 points each)
    "watergems", "infoworks", "water modelling", "pipe network",
    "pressure analysis", "flow analysis", "fire flow",
    "thames water", "affinity water", "severn trent",
    "anglian water", "united utilities", "yorkshire water",
    "sewers for adoption", "sfa", "wras", "dwi",
    "nav", "self lay", "adoption", "technical approval",
]

# Combine for iteration
ALL_WATER_KEYWORDS = WATER_KEYWORDS_HIGH + WATER_KEYWORDS_MEDIUM + WATER_KEYWORDS_LOW

# ═══════════════════════════════════════════════════════════════════
#  SEARCH QUERIES - Cast wide net
# ═══════════════════════════════════════════════════════════════════

WATER_SEARCH_QUERIES = [
    # Core searches
    "water engineer UK",
    "water design engineer",
    "water network engineer",
    "hydraulic engineer UK",
    "hydraulic engineer water",
    "watergems engineer",
    
    # Civil/utilities with water
    "civil engineer water",
    "utilities engineer water",
    "infrastructure engineer water",
    "design engineer water",
    
    # NAV/Developer Services
    "NAV engineer",
    "self-lay engineer",
    "developer services engineer",
    
    # Specific companies
    "thames water engineer",
    "affinity water engineer",
    "severn trent engineer",
    "anglian water engineer",
    "united utilities engineer",
    "yorkshire water engineer",
    "southern water engineer",
    
    # AMP programmes
    "AMP8 engineer",
    "AMP7 engineer",
    "water capital delivery",
    
    # Technical roles
    "water infrastructure",
    "water distribution",
    "section 104 engineer",
    "water adoption",
    
    # Broader searches (to get more results)
    "water UK",
    "hydraulic UK",
    "utilities water",
    "civil water",
]
