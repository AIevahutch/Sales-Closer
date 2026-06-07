"""SQLite persistence and CSV import/export."""

from __future__ import annotations

import csv
import io
import os
import sqlite3
import tempfile
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .constants import PROSPECT_COLUMNS, TEXT_COLUMNS
from .utils import (
    clean_text,
    compact_join,
    extract_domain,
    is_placeholder_url,
    normalize_instagram_handle,
    now_iso,
    today_iso,
)

DEFAULT_DB_PATH = "data/closer_acquisition.sqlite3"
FALLBACK_DB_FILENAME = "closer_acquisition.sqlite3"
SAMPLE_PROSPECT_BRANDS = {
    "rn business coach - book a strategy call",
    "bcba practice growth consultant",
    "remote nurse career coach",
    "autism provider business mastermind",
}
URL_COLUMNS = (
    "instagram_url",
    "website",
    "book_call_link",
    "application_link",
    "contact_form_url",
    "link_in_bio_url",
)


def default_db_path() -> str:
    return os.environ.get("CLOSER_DB_PATH", DEFAULT_DB_PATH)


def fallback_db_path() -> str:
    return str(Path(tempfile.gettempdir()) / FALLBACK_DB_FILENAME)


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def get_connection(path: Optional[str] = None) -> sqlite3.Connection:
    db_path = Path(path or default_db_path())
    try:
        return _connect(db_path)
    except sqlite3.OperationalError as exc:
        message = str(exc).lower()
        explicit_path = bool(path or os.environ.get("CLOSER_DB_PATH"))
        if explicit_path or ("disk i/o" not in message and "unable to open" not in message):
            raise
        return _connect(Path(fallback_db_path()))


def connection_db_path(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    return row["file"] if row and row["file"] else ":memory:"


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prospects (
            prospect_id INTEGER PRIMARY KEY AUTOINCREMENT
        )
        """
    )
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(prospects)").fetchall()}
    for column in TEXT_COLUMNS:
        if column not in existing:
            conn.execute(f"ALTER TABLE prospects ADD COLUMN {column} TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, object]:
    return {key: row[key] for key in row.keys()}


def is_sample_prospect(row: Dict[str, object]) -> bool:
    brand = clean_text(row.get("brand") or row.get("name")).lower()
    if brand in SAMPLE_PROSPECT_BRANDS:
        return True
    return any(is_placeholder_url(row.get(column)) for column in URL_COLUMNS)


def get_settings(conn: sqlite3.Connection) -> Dict[str, str]:
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] or "" for row in rows}


def save_settings(conn: sqlite3.Connection, settings: Dict[str, str]) -> None:
    now = now_iso()
    for key, value in settings.items():
        conn.execute(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, clean_text(value), now),
        )
    conn.commit()


def normalize_prospect(raw: Dict[str, object]) -> Dict[str, str]:
    now = now_iso()
    normalized = {column: clean_text(raw.get(column)) for column in TEXT_COLUMNS}
    normalized["instagram_handle"] = normalize_instagram_handle(
        normalized.get("instagram_handle") or normalized.get("instagram_url")
    )
    if normalized["instagram_handle"]:
        normalized["instagram_url"] = f"https://www.instagram.com/{normalized['instagram_handle']}/"
    normalized.setdefault("status", "New")
    if not normalized["status"]:
        normalized["status"] = "New"
    normalized.setdefault("dm_status", "Not Started")
    if not normalized["dm_status"]:
        normalized["dm_status"] = "Not Started"
    normalized.setdefault("email_status", "Not Started")
    if not normalized["email_status"]:
        normalized["email_status"] = "Not Started"
    if not normalized["date_added"]:
        normalized["date_added"] = today_iso()
    if not normalized["created_at"]:
        normalized["created_at"] = now
    normalized["updated_at"] = now
    return normalized


def _similar(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_duplicate(conn: sqlite3.Connection, prospect: Dict[str, object]) -> Optional[int]:
    handle = normalize_instagram_handle(prospect.get("instagram_handle") or prospect.get("instagram_url"))
    email = clean_text(prospect.get("email")).lower()
    domain = extract_domain(prospect.get("website"))
    brand = clean_text(prospect.get("brand") or prospect.get("name")).lower()

    if handle:
        row = conn.execute(
            "SELECT prospect_id FROM prospects WHERE lower(instagram_handle) = ? LIMIT 1",
            (handle,),
        ).fetchone()
        if row:
            return int(row["prospect_id"])
    if email:
        row = conn.execute(
            "SELECT prospect_id FROM prospects WHERE lower(email) = ? LIMIT 1",
            (email,),
        ).fetchone()
        if row:
            return int(row["prospect_id"])
    if domain:
        rows = conn.execute("SELECT prospect_id, website FROM prospects WHERE website IS NOT NULL").fetchall()
        for row in rows:
            if extract_domain(row["website"]) == domain:
                return int(row["prospect_id"])
    if brand:
        rows = conn.execute("SELECT prospect_id, brand, name FROM prospects").fetchall()
        for row in rows:
            existing = clean_text(row["brand"] or row["name"]).lower()
            if _similar(existing, brand) >= 0.9:
                return int(row["prospect_id"])
    return None


def upsert_prospect(conn: sqlite3.Connection, raw: Dict[str, object]) -> Tuple[int, bool]:
    prospect = normalize_prospect(raw)
    duplicate_id = find_duplicate(conn, prospect)
    if duplicate_id:
        existing = get_prospect(conn, duplicate_id) or {}
        merged = {}
        for column in TEXT_COLUMNS:
            new_value = prospect.get(column, "")
            existing_value = clean_text(existing.get(column))
            if column in {"scoring_notes", "source_urls", "bio_notes"}:
                merged[column] = compact_join([existing_value, new_value])
            else:
                merged[column] = new_value or existing_value
        merged["created_at"] = clean_text(existing.get("created_at")) or prospect["created_at"]
        merged["updated_at"] = now_iso()
        assignments = ", ".join(f"{column} = ?" for column in TEXT_COLUMNS)
        conn.execute(
            f"UPDATE prospects SET {assignments} WHERE prospect_id = ?",
            [merged[column] for column in TEXT_COLUMNS] + [duplicate_id],
        )
        conn.commit()
        return duplicate_id, False

    columns = TEXT_COLUMNS
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO prospects ({', '.join(columns)}) VALUES ({placeholders})",
        [prospect[column] for column in columns],
    )
    conn.commit()
    new_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    return new_id, True


def get_prospect(conn: sqlite3.Connection, prospect_id: int) -> Optional[Dict[str, object]]:
    row = conn.execute("SELECT * FROM prospects WHERE prospect_id = ?", (prospect_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_prospects(
    conn: sqlite3.Connection,
    status: str = "",
    priority: str = "",
    category: str = "",
    limit: int = 500,
) -> List[Dict[str, object]]:
    clauses = []
    params: List[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if category:
        clauses.append("category = ?")
        params.append(category)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = conn.execute(
        f"""
        SELECT * FROM prospects
        {where}
        ORDER BY
            CASE priority
                WHEN 'Very High' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                ELSE 4
            END,
            CAST(NULLIF(fit_score, '') AS INTEGER) DESC,
            updated_at DESC
        LIMIT ?
        """,
        params + [limit],
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def update_prospect(conn: sqlite3.Connection, prospect_id: int, updates: Dict[str, object]) -> None:
    allowed = [column for column in TEXT_COLUMNS if column in updates]
    if not allowed:
        return
    normalized = {column: clean_text(updates[column]) for column in allowed}
    if "updated_at" not in normalized:
        normalized["updated_at"] = now_iso()
        allowed.append("updated_at")
    assignments = ", ".join(f"{column} = ?" for column in allowed)
    conn.execute(
        f"UPDATE prospects SET {assignments} WHERE prospect_id = ?",
        [normalized[column] for column in allowed] + [prospect_id],
    )
    conn.commit()


def delete_prospect(conn: sqlite3.Connection, prospect_id: int) -> None:
    conn.execute("DELETE FROM prospects WHERE prospect_id = ?", (prospect_id,))
    conn.commit()


def daily_instagram_queue(conn: sqlite3.Connection, cap: int = 12) -> List[Dict[str, object]]:
    base_where = """
        COALESCE(instagram_url, '') != ''
        AND COALESCE(status, 'New') NOT IN ('Sent', 'Replied', 'Call Booked', 'Trial Offered', 'Closed Client', 'Not a Fit')
    """
    high_rows = conn.execute(
        """
        SELECT * FROM prospects
        WHERE
          COALESCE(priority, '') IN ('Very High', 'High')
          AND
        """
        + base_where
        + """
        ORDER BY
            CASE priority
                WHEN 'Very High' THEN 1
                WHEN 'High' THEN 2
                ELSE 4
            END,
            CAST(NULLIF(fit_score, '') AS INTEGER) DESC,
            date_added ASC
        """,
        (),
    ).fetchall()
    high_rows = [row for row in high_rows if not is_sample_prospect(_row_to_dict(row))][:cap]
    if len(high_rows) >= cap:
        return [_row_to_dict(row) for row in high_rows]

    medium_rows = conn.execute(
        """
        SELECT * FROM prospects
        WHERE
          COALESCE(priority, '') = 'Medium'
          AND
        """
        + base_where
        + """
        ORDER BY CAST(NULLIF(fit_score, '') AS INTEGER) DESC, date_added ASC
        """,
        (),
    ).fetchall()
    medium_rows = [row for row in medium_rows if not is_sample_prospect(_row_to_dict(row))][: cap - len(high_rows)]
    return [_row_to_dict(row) for row in [*high_rows, *medium_rows]]


def followups_due(conn: sqlite3.Connection, on_or_before: str) -> List[Dict[str, object]]:
    rows = conn.execute(
        """
        SELECT * FROM prospects
        WHERE COALESCE(status, '') NOT IN ('Replied', 'Call Booked', 'Trial Offered', 'Closed Client', 'Not a Fit')
          AND (
            (COALESCE(follow_up_1_date, '') != '' AND follow_up_1_date <= ? AND COALESCE(follow_up_1_sent_date, '') = '')
            OR
            (COALESCE(follow_up_2_date, '') != '' AND follow_up_2_date <= ? AND COALESCE(follow_up_2_sent_date, '') = '')
          )
        ORDER BY follow_up_1_date ASC, follow_up_2_date ASC
        """,
        (on_or_before, on_or_before),
    ).fetchall()
    return [row for row in (_row_to_dict(row) for row in rows) if not is_sample_prospect(row)]


def export_csv(conn: sqlite3.Connection) -> str:
    rows = list_prospects(conn, limit=10000)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=PROSPECT_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in PROSPECT_COLUMNS})
    return output.getvalue()


def import_csv(conn: sqlite3.Connection, csv_text: str) -> Dict[str, int]:
    reader = csv.DictReader(io.StringIO(csv_text))
    created = 0
    updated = 0
    for row in reader:
        prospect_id, is_new = upsert_prospect(conn, row)
        if prospect_id:
            created += int(is_new)
            updated += int(not is_new)
    return {"created": created, "updated": updated}


def metrics(conn: sqlite3.Connection) -> Dict[str, object]:
    rows = [row for row in list_prospects(conn, limit=10000) if not is_sample_prospect(row)]

    def count_where(predicate):
        return sum(1 for row in rows if predicate(row))

    replies = count_where(lambda row: row.get("status") in {"Replied", "Call Booked", "Trial Offered", "Closed Client"})
    dms_sent = count_where(lambda row: row.get("date_dm_sent"))
    calls = count_where(lambda row: row.get("status") in {"Call Booked", "Trial Offered", "Closed Client"})
    trials = count_where(lambda row: row.get("status") in {"Trial Offered", "Closed Client"})
    closed = count_where(lambda row: row.get("status") == "Closed Client")
    priority_prospects = count_where(lambda row: row.get("priority") in {"Very High", "High"})
    instagram_ready = count_where(
        lambda row: clean_text(row.get("instagram_url"))
        and row.get("status") not in {"Sent", "Replied", "Call Booked", "Trial Offered", "Closed Client", "Not a Fit"}
    )

    return {
        "Total prospects discovered": len(rows),
        "Total prospects saved": len(rows),
        "Total prospects scored": count_where(lambda row: clean_text(row.get("fit_score"))),
        "Priority prospects": priority_prospects,
        "Instagram-ready active": instagram_ready,
        "Very High prospects": count_where(lambda row: row.get("priority") == "Very High"),
        "High prospects": count_where(lambda row: row.get("priority") == "High"),
        "DMs generated": count_where(lambda row: row.get("date_dm_generated")),
        "DMs approved": count_where(lambda row: row.get("date_dm_approved")),
        "DMs sent": dms_sent,
        "Emails generated": count_where(lambda row: row.get("date_email_generated")),
        "Emails approved": count_where(lambda row: row.get("date_email_approved")),
        "Emails sent": count_where(lambda row: row.get("date_email_sent")),
        "Follow-ups due": len(followups_due(conn, today_iso())),
        "Follow-ups sent": count_where(lambda row: row.get("follow_up_1_sent_date") or row.get("follow_up_2_sent_date")),
        "Replies received": replies,
        "Calls booked": calls,
        "Trial opportunities opened": trials,
        "Commission-only opportunities opened": trials,
        "Closed clients": closed,
        "Rejections": count_where(lambda row: row.get("outcome") == "Rejected" or row.get("status") == "Not a Fit"),
        "Response rate": round((replies / dms_sent) * 100, 1) if dms_sent else 0,
        "Call booked rate": round((calls / dms_sent) * 100, 1) if dms_sent else 0,
        "Trial opportunity rate": round((trials / dms_sent) * 100, 1) if dms_sent else 0,
        "Client close rate": round((closed / dms_sent) * 100, 1) if dms_sent else 0,
    }
