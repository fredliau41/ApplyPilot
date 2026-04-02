"""Shared filename helpers for tailored resumes and cover letters."""

from __future__ import annotations

from hashlib import sha1
import re
from typing import Mapping


def _clean_component(value: str, limit: int) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value).strip().replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:limit] or "unknown"


def job_source_url(job: Mapping[str, object]) -> str:
    """Return the canonical URL used to identify a job row."""
    value = job.get("application_url") or job.get("url") or ""
    return str(value)


def build_job_file_prefix(job: Mapping[str, object]) -> str:
    """Build a stable, collision-resistant filename prefix for a job."""
    safe_site = _clean_component(str(job.get("site") or "unknown"), 20)
    safe_title = _clean_component(str(job.get("title") or "untitled"), 50)
    source_url = job_source_url(job)
    digest = sha1(source_url.encode("utf-8")).hexdigest()[:8] if source_url else "unknown"
    return f"{safe_site}_{safe_title}_{digest}"