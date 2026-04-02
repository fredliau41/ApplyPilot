"""Reconcile file-backed artifacts with the jobs database."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from applypilot.config import COVER_LETTER_DIR, TAILORED_DIR
from applypilot.database import get_connection

log = logging.getLogger(__name__)


def _parse_key_value_file(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    return metadata


def _load_json_file(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key).lower(): str(value) for key, value in data.items() if value is not None}


def _first_non_empty(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _collect_tailored_records() -> tuple[dict[str, dict], dict[str, str], int]:
    records: dict[str, dict] = {}
    prefix_to_url: dict[str, str] = {}
    unmatched = 0

    if not TAILORED_DIR.exists():
        return records, prefix_to_url, unmatched

    prefixes = set()
    for job_path in TAILORED_DIR.glob("*_JOB.txt"):
        prefixes.add(job_path.name[:-len("_JOB.txt")])
    for txt_path in TAILORED_DIR.glob("*.txt"):
        if txt_path.name.endswith("_JOB.txt") or txt_path.name.endswith("_CL.txt"):
            continue
        prefixes.add(txt_path.stem)

    for prefix in sorted(prefixes):
        txt_path = TAILORED_DIR / f"{prefix}.txt"
        job_path = TAILORED_DIR / f"{prefix}_JOB.txt"
        report_path = TAILORED_DIR / f"{prefix}_REPORT.json"

        metadata: dict[str, str] = {}
        if job_path.exists():
            metadata.update(_parse_key_value_file(job_path))
        if report_path.exists():
            metadata.update(_load_json_file(report_path))

        url = _first_non_empty(
            metadata.get("url"),
            metadata.get("job_url"),
            metadata.get("source_url"),
            metadata.get("application_url"),
        )

        if not url:
            unmatched += 1
            continue

        prefix_to_url[prefix] = url
        records[url] = {
            "prefix": prefix,
            "path": txt_path if txt_path.exists() else None,
            "mtime": _mtime_iso(txt_path) if txt_path.exists() else None,
        }

    return records, prefix_to_url, unmatched


def _collect_cover_records(tailored_prefix_to_url: dict[str, str]) -> tuple[dict[str, dict], int]:
    records: dict[str, dict] = {}
    unmatched = 0

    if not COVER_LETTER_DIR.exists():
        return records, unmatched

    prefixes = set()
    for job_path in COVER_LETTER_DIR.glob("*_JOB.txt"):
        prefixes.add(job_path.name[:-len("_JOB.txt")])
    for cl_path in COVER_LETTER_DIR.glob("*_CL.txt"):
        prefixes.add(cl_path.name[:-len("_CL.txt")])

    for prefix in sorted(prefixes):
        cl_path = COVER_LETTER_DIR / f"{prefix}_CL.txt"
        job_path = COVER_LETTER_DIR / f"{prefix}_JOB.txt"

        metadata: dict[str, str] = {}
        if job_path.exists():
            metadata.update(_parse_key_value_file(job_path))

        url = _first_non_empty(
            metadata.get("url"),
            metadata.get("job_url"),
            metadata.get("source_url"),
            metadata.get("application_url"),
            tailored_prefix_to_url.get(prefix),
        )

        if not url:
            unmatched += 1
            continue

        records[url] = {
            "prefix": prefix,
            "path": cl_path if cl_path.exists() else None,
            "mtime": _mtime_iso(cl_path) if cl_path.exists() else None,
        }

    return records, unmatched


def _apply_field_change(updates: dict[str, object], row: dict, field: str, value: object) -> None:
    if row[field] != value:
        updates[field] = value


def reconcile_file_backed_artifacts(dry_run: bool = False) -> dict[str, int]:
    """Update jobs rows to reflect the current filesystem state.

    The command is file-driven: if a tailored resume or cover letter exists,
    the corresponding path and timestamp are refreshed in the database. If a
    file is gone, the related DB fields are cleared.
    """
    conn = get_connection()

    tailored_by_url, tailored_prefix_to_url, tailored_unmatched = _collect_tailored_records()
    cover_by_url, cover_unmatched = _collect_cover_records(tailored_prefix_to_url)

    rows = conn.execute(
        "SELECT url, tailored_resume_path, tailored_at, cover_letter_path, cover_letter_at FROM jobs"
    ).fetchall()

    updated_rows = 0
    tailored_refreshed = 0
    tailored_cleared = 0
    cover_refreshed = 0
    cover_cleared = 0

    for row in rows:
        updates: dict[str, object] = {}
        url = row["url"]

        tailored = tailored_by_url.get(url)
        if tailored is not None:
            tailored_path = tailored["path"]
            tailored_mtime = tailored["mtime"]
            if tailored_path is None:
                if row["tailored_resume_path"] is not None or row["tailored_at"] is not None:
                    updates["tailored_resume_path"] = None
                    updates["tailored_at"] = None
                    tailored_cleared += 1
            else:
                _apply_field_change(updates, row, "tailored_resume_path", str(tailored_path))
                _apply_field_change(updates, row, "tailored_at", tailored_mtime)
                if "tailored_resume_path" in updates or "tailored_at" in updates:
                    tailored_refreshed += 1
        else:
            current_path = row["tailored_resume_path"]
            if current_path and not Path(current_path).exists():
                updates["tailored_resume_path"] = None
                updates["tailored_at"] = None
                tailored_cleared += 1

        cover = cover_by_url.get(url)
        if cover is not None:
            cover_path = cover["path"]
            cover_mtime = cover["mtime"]
            if cover_path is None:
                if row["cover_letter_path"] is not None or row["cover_letter_at"] is not None:
                    updates["cover_letter_path"] = None
                    updates["cover_letter_at"] = None
                    cover_cleared += 1
            else:
                _apply_field_change(updates, row, "cover_letter_path", str(cover_path))
                _apply_field_change(updates, row, "cover_letter_at", cover_mtime)
                if "cover_letter_path" in updates or "cover_letter_at" in updates:
                    cover_refreshed += 1
        else:
            current_path = row["cover_letter_path"]
            if current_path and not Path(current_path).exists():
                updates["cover_letter_path"] = None
                updates["cover_letter_at"] = None
                cover_cleared += 1

        if updates:
            updated_rows += 1
            if not dry_run:
                assignments = ", ".join(f"{field}=?" for field in updates)
                conn.execute(
                    f"UPDATE jobs SET {assignments} WHERE url=?",
                    (*updates.values(), url),
                )

    if not dry_run:
        conn.commit()

    return {
        "rows_updated": updated_rows,
        "tailored_refreshed": tailored_refreshed,
        "tailored_cleared": tailored_cleared,
        "cover_refreshed": cover_refreshed,
        "cover_cleared": cover_cleared,
        "tailored_unmatched_files": tailored_unmatched,
        "cover_unmatched_files": cover_unmatched,
    }