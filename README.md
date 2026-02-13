# 🔎 Ishaan Kumar — Daily Job Search Automation

Automated job hunter that searches **12+ UK & European job portals daily**
and emails you **20 best-matched water engineering jobs at 8am every morning**
for 30 days — fully automated via GitHub Actions (free).

---

## 📋 What It Searches

| Portal | Type | Coverage |
|---|---|---|
| **Adzuna UK** | API | UK-wide, salary filter |
| **Adzuna EU** | API | Ireland, Germany, Netherlands |
| **Reed UK** | API | UK-wide, salary filter |
| **Indeed UK** | RSS | London + South East |
| **Totaljobs** | RSS | UK-wide |
| **CV-Library** | RSS | UK-wide |
| **CWJobs** | RSS | UK-wide |
| **Jobsite** | RSS | UK-wide |
| **Guardian Jobs** | RSS | Engineering section |
| **New Civil Engineer** | RSS | UK engineering specialist |
| **Indeed Ireland** | RSS | Dublin + Ireland |
| **Indeed Germany** | RSS | Germany-wide |
| **Indeed Netherlands** | RSS | Netherlands-wide |
| **Indeed Spain** | RSS | Spain-wide |
| **Indeed Portugal** | RSS | Portugal-wide |
| **Environment Job** | RSS | UK Environmental |
| **Utility People** | RSS | UK Utilities |

---

## ⚙️ Setup — Step by Step

Follow these steps **in order**. The whole setup takes about 20–30 minutes.

---

### STEP 1 — Create a Free GitHub Account

1. Go to **https://github.com/signup**
2. Create a free account (use any email)
3. Verify your email address

---

### STEP 2 — Create a New Private Repository

1. Click the **+** button → "New repository"
2. Name it: `job-hunter` (or anything you like)
3. Set it to **Private** ✅
4. Click **Create repository**

---

### STEP 3 — Upload These Files to Your Repository

Upload all 4 files into your repo root and the workflow into the correct folder:

```
job-hunter/
├── job_search.py                          ← Main script
├── requirements.txt                       ← Python packages
├── README.md                              ← This file
└── .github/
    └── workflows/
        └── daily_jobs.yml                 ← Schedule config
```

**How to upload:**
- On GitHub repo page → click **Add file** → **Upload files**
- For the `.github/workflows/` folder: click **Add file** → **Create new file**,
  type `.github/workflows/daily_jobs.yml` in the filename box, paste the content

---

### STEP 4 — Get Free API Keys (takes ~5 minutes each)

#### 4a. Adzuna API (most important — UK + EU jobs)

1. Go to **https://developer.adzuna.com**
2. Click **Sign Up** → create free account
3. Go to **Dashboard** → **API Access Details**
4. Copy your **App ID** and **App Key**

#### 4b. Reed UK API

1. Go to **https://www.reed.co.uk/developers/jobseeker**
2. Register for free
3. Copy your **API Key**

---

### STEP 5 — Set Up Gmail for Sending Emails

You need a Gmail account to send the daily digest.
*(You can use your existing ishaankumar3@gmail.com)*

1. Go to your Google Account → **Security** → **2-Step Verification** → Turn ON
2. Go to **Security** → **App passwords** (search for it)
3. Select App: **Mail**, Device: **Other** → type "Job Hunter"
4. Click **Generate** → copy the **16-character password** (e.g. `abcd efgh ijkl mnop`)
5. Keep this safe — you'll need it in the next step

---

### STEP 6 — Add Secrets to GitHub (keeps your passwords safe)

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each of these:

| Secret Name | Value |
|---|---|
| `EMAIL_FROM` | Your Gmail address (e.g. `ishaankumar3@gmail.com`) |
| `EMAIL_PASSWORD` | The 16-char App Password from Step 5 |
| `ADZUNA_APP_ID` | Your Adzuna App ID from Step 4a |
| `ADZUNA_APP_KEY` | Your Adzuna App Key from Step 4a |
| `REED_API_KEY` | Your Reed API Key from Step 4b |

> ⚠️ **Never paste these into your code files** — GitHub Secrets keeps them encrypted and hidden.

---

### STEP 7 — Enable GitHub Actions

1. Go to your repo → click **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. You should now see **"🔎 Daily Job Search — Ishaan Kumar"** in the workflows list

---

### STEP 8 — Test It Right Now (don't wait until 8am!)

1. Go to **Actions** tab → click **"🔎 Daily Job Search — Ishaan Kumar"**
2. Click **"Run workflow"** → **"Run workflow"**
3. Wait ~2 minutes
4. Check your inbox at **ishaankumar3@gmail.com**
5. You should receive a beautiful email with 20 water engineering jobs!

If the email doesn't arrive:
- Check your **Spam/Junk** folder
- Go back to Actions → click the workflow run → check the logs for errors

---

### STEP 9 — Sit Back and Let It Run

From now on, the script runs **automatically at 8am every morning**.
You don't need to do anything else.

**30-day timeline:**
- Days 1–10: Build application momentum (3 apps/day minimum)
- Days 11–20: Follow up on earlier applications
- Days 21–30: Final push — target any roles that haven't responded

---

## 🎯 Job Scoring System

Jobs are scored and ranked before sending, so the **most relevant always appear first**:

| Factor | Points |
|---|---|
| High-priority title match | +30 |
| Secondary title match | +15 |
| Each skill keyword hit (WaterGEMS, AutoCAD, NAV, etc.) | +5 |
| Salary within £42k–£55k range | +20 |

---

## 🔧 Customisation

Open `job_search.py` to adjust:

| Variable | What to change |
|---|---|
| `SALARY_MIN / SALARY_MAX` | Salary filter range |
| `JOBS_PER_EMAIL` | Number of jobs per email (default: 20) |
| `HIGH_PRIORITY / SECONDARY` | Your target job titles |
| `SKILL_KEYWORDS` | Skills to boost job scores |
| `RSS_FEEDS` | Add/remove job portals |

---

## 📁 Files Summary

| File | Purpose |
|---|---|
| `job_search.py` | Main Python script — all logic here |
| `requirements.txt` | Python library dependencies |
| `.github/workflows/daily_jobs.yml` | GitHub Actions schedule (runs 8am daily) |
| `seen_jobs.json` | Auto-created — tracks already-sent jobs to avoid repeats |

---

## 🆘 Troubleshooting

**"Authentication failed" email error:**
→ Re-generate your Gmail App Password (Step 5) and update the secret

**"No jobs found" in logs:**
→ RSS feeds may be temporarily down — try running again the next day

**Email in spam:**
→ Add your Gmail sender address to your contacts / whitelist

**GitHub Actions not running:**
→ Check Actions tab is enabled; GitHub pauses scheduled workflows after 60 days of repo inactivity — just push any small change to re-activate

---

## 💡 Tips from Your CV Analysis

Your strongest selling points to highlight in every application:

1. **NAV & Self-Lay end-to-end** ownership (very rare at mid-level)
2. **First-time technical approvals** from Thames Water & Affinity Water
3. **£20M portfolio** managed concurrently at 3.5 years experience
4. **WaterGEMS hydraulic modelling** — practical project experience (not just theoretical)
5. **ProQual Level 5 Developer Services** — specialist qualification most candidates lack
6. **MIET + working toward CEng** — signals commitment to professional development

Good luck Ishaan — 30 days, let's get it! 🚀
