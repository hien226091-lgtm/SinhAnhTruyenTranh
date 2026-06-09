#!/usr/bin/env python3
"""Create database tables for the project.

Usage:
  python api_base/scripts/create_tables.py --database-url "mysql+pymysql://user:pass@host:3306/truyentranh_ai?charset=utf8mb4"

If `DATABASE_URL` is set in the environment (or `.env` loaded externally) the
script will use that by default.
"""
import argparse
import os
import sys

# Ensure the repository root (one level above `api_base`) is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def main() -> None:
    p = argparse.ArgumentParser(description="Create DB tables for the Comic AI project.")
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="SQLAlchemy database URL")
    args = p.parse_args()

    if not args.database_url:
        print("Error: no database URL provided. Set DATABASE_URL env var or pass --database-url", file=sys.stderr)
        sys.exit(2)

    # Lazy import the DB helpers and ORM so package imports work when run from project root
    from api_base.app.models.base_db import init_db, create_tables

    init_db(args.database_url)
    create_tables()
    print("Tables created (or already exist) on:", args.database_url)


if __name__ == "__main__":
    main()
