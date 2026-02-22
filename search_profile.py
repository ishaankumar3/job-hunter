#!/usr/bin/env python3
"""
Ishaan Kumar's exact job profile - strict matching only.
Based on CV V10: Water Design Engineer (NAV/Self-Lay specialist).
"""

# ═══════════════════════════════════════════════════════════════════
#  WHITELIST - Job title MUST contain at least ONE of these
# ═══════════════════════════════════════════════════════════════════

REQUIRED_TITLE_TERMS = [
    # Core water terms
    "water design", "water network", "water distribution", "water infrastructure",
    "water engineer", "water supply", "water mains", "water utilities",
    "clean water", "potable water",
    
    # Hydraulic terms  
    "hydraulic engineer", "hydraulic model", "hydraulic design",
    "watergems", "infoworks",
    
    # NAV/Developer Services
    "nav engineer", "nav design", "self-lay", "self lay", "slp engineer",
    "developer services",
    
    # Utilities (ONLY if water is also mentioned)
    "utilities design engineer", "utilities engineer",
    
    # Civil (ONLY if water context clear)
    "civil engineer water", "civil water", "utilities civil",
]

# ═══════════════════════════════════════════════════════════════════
#  HARD BLOCK - Job is REJECTED if title contains ANY of these
# ═══════════════════════════════════════════════════════════════════

BLOCKED_TITLE_TERMS = [
    # Electrical/Power
    "electrical", "electrician", "power engineer", "hv engineer", "lv engineer",
    "substation", "switchgear", "transformer", "generator",
    "control & instrumentation", "c&i engineer", "scada", "plc", "automation",
    
    # Plumbing/HVAC/MEP
    "plumber", "plumbing", "hvac", "heating", "ventilation", "air conditioning",
    "m&e engineer", "mep engineer", "mechanical engineer", "building services",
    
    # IT/Software
    "software", "linux", "devops", "cloud", "network engineer", "systems engineer",
    "it engineer", "data engineer", "full stack", "backend", "frontend",
    
    # Wrong infrastructure
    "highways", "road", "transport", "railway", "rail", "bridge", "structural",
    "geotechnical", "tunnelling", "mining",
    
    # Wrong water type
    "wastewater treatment plant", "sewage treatment", "water treatment operator",
    "wwtw operator", "wtp operator", "treatment plant operator",
    
    # Materials/Manufacturing
    "composite", "materials engineer", "manufacturing", "production engineer",
    "r&d engineer", "test engineer", "quality engineer",
    
    # Building systems
    "escalator", "lift engineer", "elevator", "fire systems", "sprinkler",
    "security systems", "access control", "building automation",
    
    # Commercial
    "quantity surveyor", "qs ", " qs", "cost consultant", "estimator",
    "commercial manager", "procurement", "contracts manager",
    
    # Operations/Maintenance
    "maintenance engineer", "maintenance technician", "mechanic", "fitter",
    "pipe fitter", "welder", "fabricator", "operator", "technician",
    
    # Too junior
    "apprentice", "intern", "trainee", "graduate trainee", "work experience",
    
    # Management (too senior or wrong focus)
    "construction manager", "site manager", "project manager",
    "programme manager", "director", "head of",
]

# ═══════════════════════════════════════════════════════════════════
#  POSITIVE KEYWORDS - Boost score if these appear in description
# ═══════════════════════════════════════════════════════════════════

WATER_ENGINEERING_KEYWORDS = [
    # Software/Tools
    "watergems", "infoworks", "autocad", "revit", "civil 3d", "arcgis",
    "microstation", "navisworks", "infraworks",
    
    # Technical
    "hydraulic modelling", "hydraulic analysis", "network modelling",
    "pressure analysis", "flow analysis", "fire flow", "hazen williams",
    "pipe sizing", "pipe network", "network calibration", "demand allocation",
    "bulk supply", "service reservoir", "pumping station",
    
    # UK Water Companies
    "thames water", "affinity water", "south east water", "wessex water",
    "anglian water", "united utilities", "yorkshire water", "severn trent",
    "southern water", "south west water", "northumbrian water", "welsh water",
    
    # Regulatory
    "section 104", "section 185", "section 38", "section 278",
    "sewers for adoption", "sfa", "water for adoption", "wras", "dwi", "ofwat",
    "cdm 2015", "developer services", "technical approval", "water uk",
    
    # Project types
    "nav", "self-lay", "self lay", "slp", "new appointments", "variations",
    "water adoption", "asset adoption", "new connections",
    "amp7", "amp8", "amp programme", "capital delivery",
    
    # Design work
    "water network design", "water distribution", "water mains design",
    "concept design", "detailed design", "feasibility", "optioneering",
    "technical approval", "construction drawings", "as-built",
    
    # Development types
    "residential", "housing", "mixed-use", "development", "infrastructure upgrade",
]

# ═══════════════════════════════════════════════════════════════════
#  SEARCH QUERIES - Only water-specific searches
# ═══════════════════════════════════════════════════════════════════

WATER_SEARCH_QUERIES = [
    # Core exact matches
    "water design engineer",
    "water network engineer",
    "water distribution engineer",
    "water infrastructure engineer",
    
    # Hydraulic specialist
    "hydraulic engineer water",
    "hydraulic modeller water",
    "watergems engineer",
    "water network modeller",
    
    # NAV/Developer Services
    "NAV engineer water",
    "NAV design engineer",
    "self-lay engineer",
    "self-lay operator",
    "developer services water",
    
    # AMP programmes
    "AMP8 water engineer",
    "AMP7 water engineer",
    "AMP water engineer",
    "capital delivery water",
    
    # Specific work types
    "water mains design",
    "section 104 engineer",
    "section 185 water",
    "water adoption engineer",
    
    # Company-specific
    "thames water engineer",
    "affinity water engineer",
    "water utilities engineer",
    
    # UK water roles
    "clean water engineer UK",
    "potable water engineer",
    "water supply engineer",
]

