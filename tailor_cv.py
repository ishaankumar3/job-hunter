#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CV & Cover Letter Tailoring Engine for Ishaan Kumar.
Called from job_search.py to generate Word docs for each job.
"""

import os
import re
import json
import logging
import traceback
from datetime import datetime

log = logging.getLogger(__name__)

# Import all heavy packages at MODULE level with clear error messages.
# If any fail, the module still loads but generate_application_pack returns None.
try:
    import anthropic as _anthropic_mod
    ANTHROPIC_OK = True
except ImportError as _e:
    _anthropic_mod = None
    ANTHROPIC_OK = False
    log.error("[IMPORT] anthropic MISSING: %s", _e)

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    DOCX_OK = True
except ImportError as _e:
    DOCX_OK = False
    log.error("[IMPORT] python-docx MISSING: %s", _e)

# ================================================================
#  DEPENDENCY CHECK
# ================================================================

def _check_dependencies():
    ok = True
    if ANTHROPIC_OK:
        log.info("[DEP] anthropic: OK")
    else:
        log.error("[DEP] anthropic: MISSING")
        ok = False
    if DOCX_OK:
        log.info("[DEP] python-docx: OK")
    else:
        log.error("[DEP] python-docx: MISSING")
        ok = False
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        log.info("[DEP] ANTHROPIC_API_KEY: present (len=%d)", len(key))
    else:
        log.error("[DEP] ANTHROPIC_API_KEY: NOT SET")
        ok = False
    return ok

# ================================================================
#  MASTER CV DATA
# ================================================================

MASTER_CV = {
    "name": "ISHAAN KUMAR",
    "contact": {
        "location": "London, United Kingdom",
        "phone": "+44 7586 603561",
        "email": "ishaankumar3@gmail.com",
        "linkedin": "linkedin.com/in/ishaankumar3",
    },
    "profile": (
        "Highly driven Water / Mechanical Design Engineer with 3.5+ years of professional experience, "
        "including 2+ years in the UK water and wastewater infrastructure sector. Experienced across "
        "concept, detailed design, and construction support, with strong capability in CAD/BIM delivery, "
        "multidisciplinary coordination, and regulatory compliance. Strong working knowledge of NAV sites, "
        "Section 38/104/106/185/278, and incumbent water company specifications (Thames Water, Affinity Water, "
        "South East Water, Wessex Water). Currently delivering end-to-end NAV and Self-Lay schemes with full "
        "technical approval responsibility for projects valued at over 20M GBP."
    ),
    "experience": [
        {
            "title": "Water Design Engineer",
            "company": "UKPS",
            "location": "London Area, United Kingdom",
            "dates": "Oct 2024 - Present",
            "bullets": [
                "Independently deliver end-to-end design for NAV and Self-Lay water infrastructure schemes from feasibility through technical approval and construction support",
                "Designed 100+ km of water distribution networks across 20+ residential and mixed-use development sites",
                "Managed concurrent project portfolio exceeding 20M GBP across 7-20 projects simultaneously",
                "Primary technical interface with Thames Water, Affinity Water, Icosa - securing first-submission technical approvals",
                "Prepare full technical approval packages: calculations, drawings, cost estimates, risk assessments, compliance documentation",
                "Ensure first-time compliance with SFA, Water UK, WRAS and company-specific technical standards",
                "Lead multidisciplinary coordination resolving clashes with electrical, gas, highways, drainage, MEP infrastructure",
                "Conduct site investigations to assess existing water infrastructure before network modification",
                "Produce formal Design Risk Assessments integrating safety, environmental, and constructability considerations",
                "Applied value engineering principles achieving consistent cost savings through material selection and routing optimisation",
                "Mentored junior engineers and standardised CAD templates and documentation formats",
                "Prepare technical drawings, layouts, sections and profiles using AutoCAD and Revit",
                "Support hydraulic and network design using WaterGEMS for pressure, flow and fire flow analysis",
            ],
        },
        {
            "title": "Assistant Water Design Engineer",
            "company": "UKPS",
            "location": "Greater London, United Kingdom",
            "dates": "Oct 2023 - Oct 2024",
            "bullets": [
                "Supported senior engineers in delivery of water network designs for NAV and Self-Lay schemes",
                "Produced CAD drawings, design documents and technical specifications to client and regulatory standards",
                "Assisted with design risk assessments, project coordination and document control",
                "Managed multiple work packages with strong time management and prioritisation",
                "Hands-on experience across AutoCAD, WaterGEMS and engineering documentation workflows",
                "Gained extensive knowledge of NAVs (New Appointments and Variations) and incumbent water supply operations",
            ],
        },
        {
            "title": "Design Engineer",
            "company": "Bellis Hardware Private Limited",
            "location": "Noida, India",
            "dates": "Sep 2021 - Jul 2022",
            "bullets": [
                "Designed architectural hardware components for global clients including Hafele Dubai and 5/7-star hotel projects",
                "Led the design department overseeing concept-to-production design activities",
                "Created detailed 3D models, prototypes and 2D manufacturing drawings using CREO and AutoCAD",
                "Developed Bills of Materials (BOMs) and supported cost estimation and manufacturing process selection",
            ],
        },
    ],
    "education": [
        {
            "degree": "MSc Advanced Mechanical Engineering",
            "institution": "Cranfield University, United Kingdom",
            "details": "Modules: Risk & Reliability Engineering, Structural Integrity, Fluid Mechanics, CFD, Engineering Project Management. Thesis: Assessing the Performance of Floating Solar Panels in Variable Wave Conditions",
        },
        {
            "degree": "BTech Mechanical Engineering",
            "institution": "Manipal University Jaipur, India",
            "details": "Core mechanical engineering, design, manufacturing and materials.",
        },
    ],
    "certifications": [
        "ProQual Level 5 - Understanding Developer Services for Water & Environmental Industries (Sep 2024)",
        "EUSR - Clean Water & Waste Water (UK Water Industry Safety Certification)",
        "AutoCAD 2D/3D Certification - CADD Centre (Aug 2022)",
        "Member - Institution of Engineering and Technology (MIET)",
        "Working towards Chartered Engineer (CEng) status",
        "ArcGIS Pro Essential Training (2026)",
        "Revit 2026 - LinkedIn Learning (Jan 2026)",
        "Power BI Essential Training (2026)",
        "Full UK driving licence",
    ],
    "languages": "German (conversational), Spanish (conversational)",
    "right_to_work": "Right to work in the UK (company-sponsored visa). Open to UK and international opportunities.",
}

# ================================================================
#  STEP 1 - CALL CLAUDE API
# ================================================================

def get_tailored_content(job):
    """Call Claude API and return tailored content as dict."""
    if not ANTHROPIC_OK:
        log.error("[API] anthropic not available")
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("[API] ANTHROPIC_API_KEY not set")
        return None

    client = _anthropic_mod.Anthropic(api_key=api_key)

    prompt = "\n".join([
        "You are an expert UK CV writer specialising in water engineering.",
        "",
        "Tailor a CV and cover letter for this job.",
        "",
        "JOB:",
        "Title: " + job.get("title", ""),
        "Company: " + job.get("company", ""),
        "Location: " + job.get("location", ""),
        "Salary: " + job.get("salary", ""),
        "Description: " + job.get("description", "")[:1500],
        "",
        "CANDIDATE:",
        json.dumps(MASTER_CV, indent=2),
        "",
        "Return ONLY valid JSON, no markdown fences, with this structure:",
        '{"cv":{"profile":"tailored profile","top_skills":["s1","s2","s3","s4","s5","s6","s7","s8"],',
        '"experience_bullets":{"Water Design Engineer":["b1","b2","b3","b4","b5","b6"],',
        '"Assistant Water Design Engineer":["b1","b2","b3"]},',
        '"relevant_certifications":["c1","c2","c3","c4"],"ats_keywords":["k1","k2","k3","k4","k5"]},',
        '"cover_letter":{"opening_paragraph":"opening","why_me_paragraph":"why me",',
        '"bullet_skills":[{"skill":"s","example":"e"},{"skill":"s","example":"e"},{"skill":"s","example":"e"},{"skill":"s","example":"e"}],',
        '"closing_paragraph":"closing","company_research_note":"note"}}',
        "",
        "Rules: ATS keywords from job description, UK English, action-led bullets, personal cover letter.",
    ])

    try:
        log.info("[API] Requesting tailored content for: %s @ %s", job.get("title"), job.get("company"))
        msg = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        data = json.loads(raw)
        log.info("[API] Success for: %s @ %s", job.get("title"), job.get("company"))
        return data
    except json.JSONDecodeError as e:
        log.error("[API] JSON error for %s: %s", job.get("title"), e)
        return None
    except Exception as e:
        log.error("[API] Error for %s: %s", job.get("title"), e)
        log.error(traceback.format_exc())
        return None

# ================================================================
#  DOCX HELPERS
# ================================================================

def _set_font(run, size=11, bold=False, color=None):
    run.font.name = "Calibri"
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)

def _add_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text.upper())
    _set_font(run, size=10, bold=True, color=(0, 70, 127))
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "00467F")
    pBdr.append(bottom)
    pPr.append(pBdr)

def _add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    _set_font(run, size=10)

def _clear_cell_borders(cell):
    tcBorders = OxmlElement("w:tcBorders")
    for side in ["top", "left", "bottom", "right"]:
        b = OxmlElement("w:" + side)
        b.set(qn("w:val"), "none")
        tcBorders.append(b)
    cell._tc.get_or_add_tcPr().append(tcBorders)

# ================================================================
#  STEP 2 - BUILD CV
# ================================================================

def build_cv_docx(job, tailored, output_path):
    if not DOCX_OK:
        raise ImportError("python-docx not available")

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Cm(1.5)
        sec.bottom_margin = Cm(1.5)
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)

    cv = tailored.get("cv", {})
    c = MASTER_CV["contact"]

    # Header
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(MASTER_CV["name"])
    _set_font(run, size=20, bold=True, color=(0, 70, 127))

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(6)
    run2 = p2.add_run(c["location"] + "  |  " + c["phone"] + "  |  " + c["email"] + "  |  " + c["linkedin"])
    _set_font(run2, size=9, color=(80, 80, 80))

    # Horizontal rule
    rp = doc.add_paragraph()
    rp.paragraph_format.space_before = Pt(0)
    rp.paragraph_format.space_after = Pt(8)
    pBdr = OxmlElement("w:pBdr")
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"), "single")
    bot.set(qn("w:sz"), "12")
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), "00467F")
    pBdr.append(bot)
    rp._p.get_or_add_pPr().append(pBdr)

    # Profile
    _add_heading(doc, "Professional Profile")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(cv.get("profile", MASTER_CV["profile"]))
    _set_font(run, size=10)

    # Skills (2 columns)
    _add_heading(doc, "Core Technical Skills")
    skills = cv.get("top_skills", [])
    if skills:
        mid = (len(skills) + 1) // 2
        col1, col2 = skills[:mid], skills[mid:]
        rows = max(len(col1), len(col2))
        tbl = doc.add_table(rows=rows, cols=2)
        tbl.style = "Table Grid"
        for row in tbl.rows:
            for cell in row.cells:
                _clear_cell_borders(cell)
        for i, sk in enumerate(col1):
            p = tbl.cell(i, 0).paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(">>  " + sk)
            _set_font(run, size=10)
        for i, sk in enumerate(col2):
            if i < rows:
                p = tbl.cell(i, 1).paragraphs[0]
                p.paragraph_format.space_after = Pt(2)
                run = p.add_run(">>  " + sk)
                _set_font(run, size=10)

    # Experience
    _add_heading(doc, "Professional Experience")
    exp_bullets = cv.get("experience_bullets", {})
    for exp in MASTER_CV["experience"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(1)
        r1 = p.add_run(exp["title"])
        _set_font(r1, size=11, bold=True, color=(0, 70, 127))
        r2 = p.add_run("  |  ")
        _set_font(r2, size=10)
        r3 = p.add_run(exp["company"])
        _set_font(r3, size=10, bold=True)

        lp = doc.add_paragraph()
        lp.paragraph_format.space_after = Pt(3)
        lr = lp.add_run(exp["location"] + "  |  " + exp["dates"])
        _set_font(lr, size=9, color=(100, 100, 100))
        lr.font.italic = True

        bullets = exp_bullets.get(exp["title"], exp["bullets"])
        for b in list(bullets)[:8]:
            _add_bullet(doc, b)

    # Education
    _add_heading(doc, "Education")
    for edu in MASTER_CV["education"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(edu["degree"])
        _set_font(run, size=10, bold=True)
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(2)
        r2 = p2.add_run(edu["institution"])
        _set_font(r2, size=10, color=(80, 80, 80))
        r2.font.italic = True
        p3 = doc.add_paragraph()
        p3.paragraph_format.space_after = Pt(4)
        r3 = p3.add_run(edu["details"])
        _set_font(r3, size=9, color=(100, 100, 100))

    # Certifications
    _add_heading(doc, "Certifications & Professional Membership")
    for cert in cv.get("relevant_certifications", MASTER_CV["certifications"][:6]):
        _add_bullet(doc, cert)

    # Additional
    _add_heading(doc, "Additional Information")
    p = doc.add_paragraph()
    run = p.add_run(MASTER_CV["right_to_work"] + "  |  Languages: " + MASTER_CV["languages"])
    _set_font(run, size=10)

    doc.save(output_path)
    log.info("[DOCX] CV saved: %s", output_path)

# ================================================================
#  STEP 3 - BUILD COVER LETTER
# ================================================================

def build_cover_letter_docx(job, tailored, output_path):
    if not DOCX_OK:
        raise ImportError("python-docx not available")

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
        sec.left_margin = Cm(2.5)
        sec.right_margin = Cm(2.5)

    cl = tailored.get("cover_letter", {})
    c = MASTER_CV["contact"]
    today = datetime.now().strftime("%d %B %Y")

    # Sender (right-aligned)
    for line in [MASTER_CV["name"], c["phone"], c["email"], c["linkedin"], c["location"]]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(line)
        _set_font(run, size=10)

    doc.add_paragraph()

    # Date
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(today)
    _set_font(run, size=10)

    # Recipient
    for line in ["Hiring Manager", job.get("company", ""), job.get("location", "")]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(line)
        _set_font(run, size=10)

    doc.add_paragraph()

    # Subject
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    run = p.add_run("Re: Application for " + job.get("title", ""))
    _set_font(run, size=11, bold=True, color=(0, 70, 127))

    # Salutation
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run("Dear Hiring Manager,")
    _set_font(run, size=11)

    # Opening + company note
    opening = cl.get("opening_paragraph", "")
    note = cl.get("company_research_note", "")
    if note:
        opening = opening + " " + note
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    run = p.add_run(opening)
    _set_font(run, size=11)

    # Why me
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    run = p.add_run(cl.get("why_me_paragraph", ""))
    _set_font(run, size=11)

    # 4 skill bullets
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run("In particular, I can bring the following to your team:")
    _set_font(run, size=11)

    for item in cl.get("bullet_skills", []):
        bp = doc.add_paragraph(style="List Bullet")
        bp.paragraph_format.left_indent = Inches(0.4)
        bp.paragraph_format.space_after = Pt(4)
        r1 = bp.add_run(item.get("skill", "") + ": ")
        _set_font(r1, size=11, bold=True)
        r2 = bp.add_run(item.get("example", ""))
        _set_font(r2, size=11)

    doc.add_paragraph()

    # Closing
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(16)
    run = p.add_run(cl.get("closing_paragraph", ""))
    _set_font(run, size=11)

    # Sign-off
    for line in ["Yours sincerely,", "", "", MASTER_CV["name"]]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(line)
        _set_font(run, size=11, bold=(line == MASTER_CV["name"]))

    doc.save(output_path)
    log.info("[DOCX] Cover letter saved: %s", output_path)

# ================================================================
#  MAIN ENTRY POINT
# ================================================================

def generate_application_pack(job, output_dir="."):
    """Generate tailored CV + cover letter. Returns dict or None."""
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    log.info("[PACK] Starting: %s @ %s", title, company)

    if not _check_dependencies():
        log.error("[PACK] Dependency check failed - aborting")
        return None

    os.makedirs(output_dir, exist_ok=True)
    safe = re.sub(r"[^\w]", "_", title + "_" + company)[:50]
    cv_path = os.path.join(output_dir, "CV_Ishaan_" + safe + ".docx")
    cl_path = os.path.join(output_dir, "CL_Ishaan_" + safe + ".docx")

    tailored = get_tailored_content(job)
    if not tailored:
        log.error("[PACK] API call failed - aborting")
        return None

    try:
        build_cv_docx(job, tailored, cv_path)
        log.info("[PACK] CV written: %s (%d bytes)", cv_path, os.path.getsize(cv_path))
    except Exception as e:
        log.error("[PACK] CV build error: %s", e)
        log.error(traceback.format_exc())
        return None

    try:
        build_cover_letter_docx(job, tailored, cl_path)
        log.info("[PACK] CL written: %s (%d bytes)", cl_path, os.path.getsize(cl_path))
    except Exception as e:
        log.error("[PACK] Cover letter build error: %s", e)
        log.error(traceback.format_exc())
        return None

    log.info("[PACK] DONE: %s @ %s", title, company)
    return {
        "job_title": title,
        "company": company,
        "cv_path": cv_path,
        "cl_path": cl_path,
        "ats_keywords": tailored.get("cv", {}).get("ats_keywords", []),
    }
