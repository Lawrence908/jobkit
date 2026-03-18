"""Google Sheets append/update row."""
import logging
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def _column_letter(col_index: int) -> str:
    """0-based column index to A1 notation letter(s). 0 -> A, 26 -> AA."""
    result = ""
    while col_index >= 0:
        result = chr(65 + (col_index % 26)) + result
        col_index = col_index // 26 - 1
    return result or "A"


def _contiguous_segments(indices: list[int]) -> list[tuple[int, int]]:
    """Turn sorted column indices into (start, end) segments, end exclusive. E.g. [0,2,3,4] -> [(0,1),(2,5)]."""
    if not indices:
        return []
    segments: list[tuple[int, int]] = []
    start = indices[0]
    prev = indices[0]
    for i in indices[1:]:
        if i == prev + 1:
            prev = i
        else:
            segments.append((start, prev + 1))
            start = i
            prev = i
    segments.append((start, prev + 1))
    return segments


def get_header_row(service, spreadsheet_id: str, sheet_name: str) -> list[str]:
    """Return the first row of the sheet as column headers (strings)."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:ZZ1",
    ).execute()
    row = result.get("values", [[]])[0]
    return [str(c).strip() for c in row] if row else []


def get_all_sheet_data(
    service, spreadsheet_id: str, sheet_name: str, max_rows: int = 500
) -> tuple[list[str], list[list[str]]]:
    """
    Return (headers, data_rows) for the configured sheet.
    First row is headers; data_rows are the rest, padded to header length.
    """
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:ZZ{max_rows + 1}",
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return [], []
    headers = [str(c).strip() if c else "" for c in rows[0]]
    data_rows = []
    for row in rows[1:]:
        padded = [str(c).strip() if c else "" for c in row]
        while len(padded) < len(headers):
            padded.append("")
        data_rows.append(padded[: len(headers)])
    return headers, data_rows


def get_row(service, spreadsheet_id: str, sheet_name: str, row_index: int) -> list[str]:
    """Return one row (1-based row_index) as a list of strings; length matches header."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A{row_index}:ZZ{row_index}",
    ).execute()
    row = result.get("values", [[]])[0]
    return [str(c).strip() if c else "" for c in row] if row else []


def find_row_by_url(service, spreadsheet_id: str, sheet_name: str, url_column: str, job_url: str) -> int | None:
    """Return 1-based row index if job_url found in url_column, else None. Uses first row as header."""
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
    want = job_url.strip()
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > col_idx and (row[col_idx] or "").strip() == want:
            return i
    return None


def get_next_data_row(service, spreadsheet_id: str, sheet_name: str, max_rows: int = 1000) -> int:
    """Return 1-based row number for the next empty row (after header + data). Extends table if needed."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:ZZ{max_rows}",
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return 1
    return len(rows) + 1


def _write_row_by_segments(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    row_num: int,
    header_row: list[str],
    row_values: list[Any],
) -> None:
    """Write row_values to the given row, only in columns where header is non-empty (avoids offset from blank columns)."""
    non_empty = [i for i, h in enumerate(header_row) if (h or "").strip()]
    if not non_empty:
        return
    segments = _contiguous_segments(non_empty)
    data = []
    for start, end in segments:
        col_a = _column_letter(start)
        col_b = _column_letter(end - 1)
        range_name = f"'{sheet_name}'!{col_a}{row_num}:{col_b}{row_num}"
        vals = [row_values[i] for i in range(start, end)]
        data.append({"range": range_name, "values": [vals]})
    body = {"valueInputOption": "USER_ENTERED", "data": data}
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body,
    ).execute()


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
    Checks URL first: if job URL already exists, updates that row; otherwise appends to the next empty row.
    Writes only to columns that have a non-empty header to avoid offset from blank columns.
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
        while len(existing) < len(header_row):
            existing.append("")
        row_values = merge_row_with_existing(header_row, row_values, existing, column_map)
        _write_row_by_segments(service, spreadsheet_id, sheet_name, row_num, header_row, row_values)
    else:
        next_row = get_next_data_row(service, spreadsheet_id, sheet_name)
        _write_row_by_segments(service, spreadsheet_id, sheet_name, next_row, header_row, row_values)


def _sheet_id_for_tab(service, spreadsheet_id: str, sheet_name: str) -> int | None:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for s in meta.get("sheets", []):
        props = s.get("properties") or {}
        if (props.get("title") or "") == sheet_name:
            sid = props.get("sheetId")
            return int(sid) if sid is not None else None
    return None


def delete_job_row_from_sheet(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    url_column: str,
    job_url: str,
) -> bool:
    """
    Remove the data row whose url_column matches job_url (same matching as sync).
    Returns True if a row was deleted. No-op if URL empty or no matching row.
    """
    if not (job_url or "").strip():
        return False
    row_num = find_row_by_url(service, spreadsheet_id, sheet_name, url_column, job_url)
    if row_num is None:
        return False
    sheet_id = _sheet_id_for_tab(service, spreadsheet_id, sheet_name)
    if sheet_id is None:
        raise ValueError(f"Sheet tab not found: {sheet_name!r}")
    # row_num is 1-based (header = 1); deleteDimension startIndex is 0-based
    start = row_num - 1
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start,
                            "endIndex": start + 1,
                        }
                    }
                }
            ]
        },
    ).execute()
    return True
