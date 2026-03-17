#!/usr/bin/env python3
"""Backfill user_id on existing rows that were created before multi-user auth.

Usage:
    python -m scripts.backfill_user_id <user_id_uuid>

Run from backend/ directory after the user has signed up via Supabase Auth.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import get_engine


def backfill(user_id: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        for table in ("jobs", "artifacts", "google_tokens"):
            result = conn.execute(
                text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
                {"uid": user_id},
            )
            print(f"  {table}: {result.rowcount} rows updated")
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python -m scripts.backfill_user_id <user_id_uuid>")
        sys.exit(1)
    uid = sys.argv[1].strip()
    if len(uid) < 32:
        print(f"Error: '{uid}' doesn't look like a UUID")
        sys.exit(1)
    print(f"Backfilling user_id = {uid} on all rows with NULL user_id...")
    backfill(uid)
