"""Prompt builder for the autonomous job application agent.

Constructs the full instruction prompt that tells Claude Code / the AI agent
how to fill out a job application form using Playwright MCP tools. All
personal data is loaded from the user's profile -- nothing is hardcoded.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from applypilot import config

logger = logging.getLogger(__name__)


def _build_profile_summary(profile: dict) -> str:
    """Format the applicant profile section of the prompt."""
    p = profile["personal"]
    w = profile["work_authorization"]
    c = profile["compensation"]
    e = profile.get("experience", {})
    
    return f"""Name: {p['full_name']} | Email: {p['email']} | Phone: {p['phone']}
Location: {p.get('city','')}, {p.get('province_state','')} {p.get('postal_code','')} {p.get('country','')}
Links: LinkedIn: {p.get('linkedin_url','')} | GitHub: {p.get('github_url','')} | Portfolio: {p.get('portfolio_url','')}
Work Auth: {w.get('legally_authorized_to_work', 'Yes')} | Sponsor: {w.get('require_sponsorship', 'No')}
Salary: ${c['salary_expectation']} {c.get('salary_currency', 'USD')}
Exp: {e.get('years_of_experience_total')} yrs | Edu: {e.get('education_level')}"""


def _build_location_check(profile: dict, search_config: dict) -> str:
    """Build the location eligibility check section of the prompt."""
    p = profile["personal"]
    loc = search_config.get("location", {})
    accept = loc.get("accept_patterns", [])
    city_list = ", ".join(accept) if accept else p.get("city", "your city")

    return f"- Location: '{p.get('city','')}' or remote = OK. Else RESULT:FAILED:location."


def _build_salary_section(profile: dict) -> str:
    """Build the salary negotiation instructions."""
    c = profile["compensation"]
    return f"- Salary: Use ${c['salary_expectation']} {c.get('salary_currency', 'USD')}. Use midpoint if range provided"


def _build_screening_section(profile: dict) -> str:
    """Build the screening questions guidance section."""
    return f"- Screening: Assume YES for tools matching role. Tell truth for work auth/clearance. 1-2 brief sentences for open questions.\n- EEO: \"Decline to self-identify\" for all."


def _build_hard_rules(profile: dict) -> str:
    """Build the hard rules section."""
    from applypilot.config import load_blocked_sso
    blocked_sso = ",".join(load_blocked_sso())
    return f"- NEVER DO THESE (output RESULT:FAILED): give SSN/bank info, grant camera/location, login to SSO ({blocked_sso}), do selfie checks/biometrics, signup for freelancing."


def _build_captcha_section() -> str:
    """Build the CAPTCHA detection and solving instructions."""
    config.load_env()
    key = os.environ.get("CAPSOLVER_API_KEY", "")
    fpath = config.APP_DIR / "captcha_guide.txt"
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    fpath.write_text(f"""API Key: {key}
To solve CAPTCHA:
1. DETECT: run browser_evaluate to find sitekey/type (hcaptcha, turnstile, recaptchav2/v3, funcaptcha).
2. SOLVE: POST to https://api.capsolver.com/createTask with type & sitekey. Poll getTaskResult.
3. INJECT: Inject token into inputs and DOM structures.
""", encoding="utf-8")
    return f"- CAPTCHA: If blocked, read {fpath} for CapSolver API logic."


def build_prompt(job: dict, tailored_resume: str,
                 cover_letter: str | None = None,
                 dry_run: bool = False) -> str:
    """Build the full instruction prompt for the apply agent.

    Loads the user profile and search config internally. All personal data
    comes from the profile -- nothing is hardcoded.

    Args:
        job: Job dict from the database (must have url, title, site,
             application_url, fit_score, tailored_resume_path).
        tailored_resume: Plain-text content of the tailored resume.
        cover_letter: Optional plain-text cover letter content.
        dry_run: If True, tell the agent not to click Submit.

    Returns:
        Complete prompt string for the AI agent.
    """
    profile = config.load_profile()
    search_config = config.load_search_config()
    personal = profile["personal"]

    # --- Resolve resume PDF path ---
    resume_path = job.get("tailored_resume_path")
    if not resume_path:
        raise ValueError(f"No tailored resume for job: {job.get('title', 'unknown')}")

    src_pdf = Path(resume_path).with_suffix(".pdf").resolve()
    if not src_pdf.exists():
        raise ValueError(f"Resume PDF not found: {src_pdf}")

    # Copy to a clean filename for upload (recruiters see the filename)
    full_name = personal["full_name"]
    name_slug = full_name.replace(" ", "_")
    dest_dir = config.APPLY_WORKER_DIR / "current"
    dest_dir.mkdir(parents=True, exist_ok=True)
    upload_pdf = dest_dir / f"{name_slug}_Resume.pdf"
    shutil.copy(str(src_pdf), str(upload_pdf))
    pdf_path = str(upload_pdf)

    # --- Cover letter handling ---
    cover_letter_text = cover_letter or ""
    cl_upload_path = ""
    cl_path = job.get("cover_letter_path")
    if cl_path and Path(cl_path).exists():
        cl_src = Path(cl_path)
        # Read text from .txt sibling (PDF is binary)
        cl_txt = cl_src.with_suffix(".txt")
        if cl_txt.exists():
            cover_letter_text = cl_txt.read_text(encoding="utf-8")
        elif cl_src.suffix == ".txt":
            cover_letter_text = cl_src.read_text(encoding="utf-8")
        # Upload must be PDF
        cl_pdf_src = cl_src.with_suffix(".pdf")
        if cl_pdf_src.exists():
            cl_upload = dest_dir / f"{name_slug}_Cover_Letter.pdf"
            shutil.copy(str(cl_pdf_src), str(cl_upload))
            cl_upload_path = str(cl_upload)

    # --- Build all prompt sections ---
    profile_summary = _build_profile_summary(profile)
    location_check = _build_location_check(profile, search_config)
    salary_section = _build_salary_section(profile)
    screening_section = _build_screening_section(profile)
    hard_rules = _build_hard_rules(profile)
    captcha_section = _build_captcha_section()

    # Cover letter fallback text
    city = personal.get("city", "the area")
    if not cover_letter_text:
        cl_display = (
            f"None available. Skip if optional. If required, write 2 factual "
            f"sentences: (1) relevant experience from the resume that matches "
            f"this role, (2) available immediately and based in {city}."
        )
    else:
        cl_display = cover_letter_text

    # Phone digits only (for fields with country prefix)
    phone_digits = "".join(c for c in personal.get("phone", "") if c.isdigit())

    # SSO domains the agent cannot sign into (loaded from config/sites.yaml)
    from applypilot.config import load_blocked_sso
    blocked_sso = load_blocked_sso()

    # Preferred display name
    preferred_name = personal.get("preferred_name", full_name.split()[0])
    last_name = full_name.split()[-1] if " " in full_name else ""
    display_name = f"{preferred_name} {last_name}".strip()

    # Dry-run: override submit instruction
    if dry_run:
        submit_instruction = "IMPORTANT: Do NOT click the final Submit/Apply button. Output RESULT:APPLIED (dry run)."
    else:
        submit_instruction = "Click Submit."

    prompt = f"""MISSION: Submit job application Fill the job application with necessary information.

[TARGET]
URL: {job.get('application_url') or job['url']}
Role: {job['title']}
Resume: {pdf_path}
CL: {cl_upload_path or "N/A"}

[PROFILE]
{profile_summary}

[RULES]
{location_check}
{salary_section}
{screening_section}
{hard_rules}
{captcha_section}

[FLOW]
1. Navigate and fill the job application with necessary information.
2. {submit_instruction}
3. Finish codes: RESULT:APPLIED, RESULT:EXPIRED, RESULT:CAPTCHA, RESULT:LOGIN_ISSUE, RESULT:FAILED:<reason>.

--- RESUME TEXT ---
{tailored_resume}

--- COVER LETTER TEXT ---
{cl_display}
"""

    return prompt
