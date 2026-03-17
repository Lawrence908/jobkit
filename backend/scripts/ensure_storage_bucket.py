#!/usr/bin/env python3
"""Create the jobkit-artifacts bucket in Supabase Storage if it does not exist.

The app normally creates the bucket on first upload, but if uploads never ran
(e.g. supabase package was missing or env not set), no bucket exists. Run this
once with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set.

Usage:
    cd backend && python -m scripts.ensure_storage_bucket

Requires: supabase package, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in env.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.services.storage import BUCKET, use_storage


def main() -> int:
    if not use_storage():
        print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        return 1
    try:
        from supabase import create_client
        s = get_settings()
        client = create_client(s.supabase_url, s.supabase_service_role_key)
        buckets = client.storage.list_buckets()
        names = [b.name for b in (buckets or [])]
        if BUCKET in names:
            print(f"Bucket '{BUCKET}' already exists.")
            return 0
        client.storage.create_bucket(BUCKET, options={"private": True})
        print(f"Created bucket '{BUCKET}' in Supabase Storage.")
        return 0
    except ImportError:
        print("Install the supabase package: pip install supabase")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
