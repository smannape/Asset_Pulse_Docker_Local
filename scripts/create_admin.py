#!/usr/bin/env python3
"""
CLI script to bootstrap the first admin user.

Usage (from repo root inside the running backend container or with venv active):
    python scripts/create_admin.py --email admin@company.com --password SecurePass1!

Or via docker exec:
    docker exec -it assetpulse_backend python -m scripts.create_admin \\
        --email admin@company.com --password SecurePass1!
"""

from __future__ import annotations

import argparse
import sys
import os

# Ensure the backend/app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an Asset Pulse admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 8 chars)")
    parser.add_argument("--name", default="System Admin", help="Display name")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("ERROR: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    from app.database import User, init_db, get_session
    from app.modules.auth import hash_password
    from sqlalchemy import select

    init_db()

    with get_session() as s:
        existing = s.execute(
            select(User).where(User.email == args.email.lower())
        ).scalar_one_or_none()
        if existing:
            print(f"User '{args.email}' already exists (role={existing.role}).")
            sys.exit(0)

        admin = User(
            email=args.email.lower().strip(),
            full_name=args.name,
            password_hash=hash_password(args.password),
            role="admin",
            is_active=True,
        )
        s.add(admin)
        s.flush()
        uid = admin.id

    print(f"Admin user created: id={uid}  email={args.email}  role=admin")


if __name__ == "__main__":
    main()
