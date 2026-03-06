"""Google Sheets append/update row."""
import logging
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_header_row(service, spreadsheet_id: str, sheet_name: str) -> list[str]:
    """Return the first row of the sheet as column headers (strings)."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:ZZ1",
    ).execute()
    row = result.get("values", [[]])[0]
    return [str(c).strip() for c in row] if row else []


def get_row(service, spreadsheet_id: str, sheet_name: str, row_index: int) -> list[str]:
    """Return one row (1-based row_index) as a list of strings; length matches header."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A{row_index}:ZZ{row_index}",
    ).execute()
    row = result.get("values", [[]])[0]
    return [str(c).strip() if c else "" for c in row] if row else []


def find_row_by_url(service, spreadsheet_id: str, sheet_name: str, url_column: str, job_url: str) -> int | None:
    """Return 1-based row index if job_url found in url_column, else None."""
    if not job_url or not job_url.strip():
        return None
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A:ZZ",
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return None
    header = [str(c).strip().lower() for c in rows[0]]
    try:
        col_idx = header.index(url_column.strip().lower())
    except ValueError:
        return None
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > col_idx and (row[col_idx] or "").strip() == job_url.strip():
            return i
    return None


def append_row(service, spreadsheet_id: str, sheet_name: str, values: list) -> None:
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A:Z",
        valueInputOption="USER_ENTERED",
        body={"values": [values]},
    ).execute()


def update_row(service, spreadsheet_id: str, sheet_name: str, row: int, values: list, start_col: int = 0) -> None:
    """Update a row; values are written starting at column start_col (0-based)."""
    col_letter = chr(65 + start_col) if start_col < 26 else "A"
    range_name = f"'{sheet_name}'!{col_letter}{row}"
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body={"values": [values]},
    ).execute()


def build_row_by_headers(
    header_row: list[str],
    job_url: str | None,
    company: str,
    role: str,
    status: str,
    resume_link: str,
    cover_letter_link: str,
    notes_link: str,
    column_map: dict[str, str],
) -> list[Any]:
    """
    Build a row list matching header_row order, filling only columns that have a mapping.
    column_map: logical field name -> your sheet column header name (e.g. "company" -> "Company Name").
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    job_url_val = job_url or ""
    values_by_field = {
        "company": company,
        "role": role,
        "job_url": job_url_val,
        "status": status,
        "date_submitted": now,
        "resume_link": resume_link,
        "cover_link": cover_letter_link,
        "notes_link": notes_link,
        "link_to_job_req": job_url_val,
    }
    # Map: normalized header (lower) -> value. Only include columns that are in column_map.
    header_to_value: dict[str, Any] = {}
    for field, sheet_header in column_map.items():
        if not sheet_header or field not in values_by_field:
            continue
        header_to_value[sheet_header.strip().lower()] = values_by_field[field]
    # Build row in same order as header_row
    row = []
    for h in header_row:
        key = h.strip().lower() if h else ""
        row.append(header_to_value.get(key, ""))
    return row


def merge_row_with_existing(
    header_row: list[str],
    new_row: list[Any],
    existing_row: list[str],
    column_map: dict[str, str],
) -> list[Any]:
    """Overwrite only columns we map; leave other columns (e.g. Salary, Rejection Reason) as in existing_row."""
    written_headers = {v.strip().lower() for v in column_map.values() if v}
    merged = []
    for i, h in enumerate(header_row):
        key = h.strip().lower() if h else ""
        if key in written_headers:
            merged.append(new_row[i] if i < len(new_row) else "")
        else:
            merged.append(existing_row[i] if i < len(existing_row) else "")
    return merged


def sheet_row_for_job(
    job_url: str | None,
    company: str,
    role: str,
    status: str,
    resume_link: str,
    cover_letter_link: str,
    notes_link: str,
    keywords: list,
    location: str,
    source: str,
) -> list:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    return [
        now,
        company,
        role,
        job_url or "",
        status,
        resume_link,
        cover_letter_link,
        notes_link,
        ", ".join(keywords) if isinstance(keywords, list) else str(keywords),
        location,
        source,
        now,
    ]


def default_column_map() -> dict[str, str]:
    """Default mapping when env column names are not set; matches common tracker headers."""
    return {
        "company": "Company Name",
        "job_url": "Job URL",
        "status": "Application Status",
        "role": "Role",
        "date_submitted": "Date Submitted",
        "resume_link": "Resume Link",
        "cover_link": "Cover Letter Link",
        "notes_link": "Notes Link",
        "link_to_job_req": "Link to Job Req",
    }


def sync_job_to_sheet(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    url_column: str,
    job,  # Job model or object with .url, .company, .role, .status
    resume_link: str,
    cover_letter_link: str,
    notes_link: str,
    column_map: dict[str, str],
) -> None:
    """
    Find or append the row for this job and write/update it so columns match the sheet header.
    Uses column_map to place company, role, job_url, status, date_submitted, links in correct columns.
    """
    header_row = get_header_row(service, spreadsheet_id, sheet_name)
    if not header_row:
        raise ValueError("Sheet has no header row")
    row_values = build_row_by_headers(
        header_row,
        getattr(job, "url", None) or (job.get("url") if isinstance(job, dict) else None),
        (getattr(job, "company", None) or "") or (job.get("company", "") if isinstance(job, dict) else ""),
        (getattr(job, "role", None) or "") or (job.get("role", "") if isinstance(job, dict) else ""),
        (getattr(job, "status", None) or "") or (job.get("status", "") if isinstance(job, dict) else ""),
        resume_link,
        cover_letter_link,
        notes_link,
        column_map,
    )
    job_url = getattr(job, "url", None) or (job.get("url") if isinstance(job, dict) else None) or ""
    row_num = find_row_by_url(service, spreadsheet_id, sheet_name, url_column, job_url)
    if row_num is not None:
        existing = get_row(service, spreadsheet_id, sheet_name, row_num)
        # Pad existing to header length so merge doesn't truncate
        while len(existing) < len(header_row):
            existing.append("")
        row_values = merge_row_with_existing(header_row, row_values, existing, column_map)
        update_row(service, spreadsheet_id, sheet_name, row_num, row_values, 0)
    else:
        append_row(service, spreadsheet_id, sheet_name, row_values)
