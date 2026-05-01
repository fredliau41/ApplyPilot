import re

def update_scorer():
    with open('src/applypilot/scoring/scorer.py', 'r') as f:
        content = f.read()

    # Find SCORE_PROMPT definition
    old_prompt = """RESPOND IN EXACTLY THIS FORMAT (no other text):
SCORE: [1-10]
KEYWORDS: [comma-separated ATS keywords from the job description that match or could match the candidate]
REASONING: [2-3 sentences explaining the score]\"\"\""""

    new_prompt = """RESPOND IN EXACTLY THIS FORMAT (no other text):
SCORE: [0-10]
KEYWORDS: [comma-separated ATS keywords from the job description that match or could match the candidate]
REASONING: [2-3 sentences explaining the score]\"\"\""""

    content = content.replace(old_prompt, new_prompt)

    # In _parse_score_response:
    # score = max(1, min(10, score))
    content = content.replace('score = max(1, min(10, score))', 'score = max(0, min(10, score))')

    # Change score_job to take filter_req
    old_score_job = """def score_job(resume_text: str, job: dict) -> dict:
    \"\"\"Score a single job against the resume.

    Args:
        resume_text: The candidate's full resume text.
        job: Job dict with keys: title, site, location, full_description.

    Returns:
        {"score": int, "keywords": str, "reasoning": str}
    \"\"\"
    job_text = (
        f"TITLE: {job['title']}\\n"
        f"COMPANY: {job['site']}\\n"
        f"LOCATION: {job.get('location', 'N/A')}\\n\\n"
        f"DESCRIPTION:\\n{(job.get('full_description') or '')[:6000]}"
    )

    messages = [
        {"role": "system", "content": SCORE_PROMPT},
        {"role": "user", "content": f"RESUME:\\n{resume_text}\\n\\n---\\n\\nJOB POSTING:\\n{job_text}"},
    ]"""

    new_score_job = """def score_job(resume_text: str, job: dict, filter_req: str = "") -> dict:
    \"\"\"Score a single job against the resume.

    Args:
        resume_text: The candidate's full resume text.
        job: Job dict with keys: title, site, location, full_description.
        filter_req: Additional requirement that must be fulfilled (returns 0 if not).

    Returns:
        {"score": int, "keywords": str, "reasoning": str}
    \"\"\"
    job_text = (
        f"TITLE: {job['title']}\\n"
        f"COMPANY: {job['site']}\\n"
        f"LOCATION: {job.get('location', 'N/A')}\\n\\n"
        f"DESCRIPTION:\\n{(job.get('full_description') or '')[:6000]}"
    )

    system_content = SCORE_PROMPT
    if filter_req:
        system_content += f"\\n\\nADDITIONAL REQUIREMENT: {filter_req}\\nRETURN A SCORE OF 0 IF THE ADDITIONAL REQUIREMENT IS NOT FULFILLED."

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"RESUME:\\n{resume_text}\\n\\n---\\n\\nJOB POSTING:\\n{job_text}"},
    ]"""

    content = content.replace(old_score_job, new_score_job)

    # In run_scoring:
    old_def_run = """def run_scoring(limit: int = 0, rescore: bool = False, workers: int = 1) -> dict:"""
    new_def_run = """def run_scoring(limit: int = 0, rescore: bool = False, workers: int = 1) -> dict:"""
    
    # Needs to load config and pass filter
    old_run = """    workers = max(1, workers)
    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    conn = get_connection()"""

    new_run = """    workers = max(1, workers)
    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    conn = get_connection()
    from applypilot.config import load_search_config
    search_cfg = load_search_config()
    filter_req = search_cfg.get("filter", "")"""

    content = content.replace(old_run, new_run)

    old_score_one = """    def _score_one(job: dict) -> dict:
        result = score_job(resume_text, job)
        return {"""
    
    new_score_one = """    def _score_one(job: dict) -> dict:
        result = score_job(resume_text, job, filter_req)
        return {"""

    content = content.replace(old_score_one, new_score_one)

    with open('src/applypilot/scoring/scorer.py', 'w') as f:
        f.write(content)

update_scorer()
