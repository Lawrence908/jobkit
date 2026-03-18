#!/usr/bin/env python3
"""Create the demo user in Supabase and ingest Ada Lovelace data.

Usage:
    cd backend && python -m scripts.setup_demo_user

Reads DEMO_USER_EMAIL and DEMO_USER_PASSWORD from env/.env.
Creates the Supabase user (skips if already exists), then ingests
data/demo/ into that user. Prints the user UUID to set as DEMO_USER_ID.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.services.avatar_store import save_avatar_from_upload
from scripts.ingest_data_to_user import run as ingest_run


def main() -> None:
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_service_role_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
        sys.exit(1)

    email = settings.demo_user_email
    password = settings.demo_user_password
    if not email or not password:
        print("Error: DEMO_USER_EMAIL and DEMO_USER_PASSWORD must be set in .env")
        sys.exit(1)

    print(f"Setting up demo user: {email}")

    # Create user via Supabase Admin API
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
    }

    user_id: str | None = None

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, json=payload, headers=headers)

        if resp.status_code == 422 and "already been registered" in resp.text.lower():
            print("  User already exists, fetching ID...")
            # List users and find by email
            list_resp = client.get(url, headers=headers)
            list_resp.raise_for_status()
            for u in list_resp.json().get("users", []):
                if u.get("email", "").lower() == email.lower():
                    user_id = u["id"]
                    break
            if not user_id:
                print("Error: User exists but could not find ID")
                sys.exit(1)
        elif resp.is_success:
            user_id = resp.json()["id"]
            print(f"  Created user: {user_id}")
        else:
            print(f"Error: Supabase returned {resp.status_code}: {resp.text}")
            sys.exit(1)

    print(f"  Demo user ID: {user_id}")

    # Ingest demo data
    demo_dir = Path(__file__).resolve().parent.parent.parent / "data" / "demo"
    if not demo_dir.exists():
        print(f"Error: Demo data directory not found: {demo_dir}")
        sys.exit(1)

    print(f"  Ingesting data from {demo_dir}...")
    ingest_run(user_id, demo_dir)

    # Avatar
    avatar_candidates = list(demo_dir.glob("avatar.*"))
    if avatar_candidates:
        avatar_file = avatar_candidates[0]
        try:
            save_avatar_from_upload(user_id, avatar_file.read_bytes())
            print(f"  avatar: saved from {avatar_file.name}")
        except Exception as e:
            print(f"  avatar: failed ({e})")
    else:
        print("  avatar: skipped (no avatar.* in demo dir)")

    print()
    print("=" * 60)
    print(f"  DEMO_USER_ID={user_id}")
    print("=" * 60)
    print()
    print("Add the line above to your .env file, then restart the backend.")


if __name__ == "__main__":
    main()
