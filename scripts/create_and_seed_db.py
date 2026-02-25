#!/usr/bin/env python3
"""
Create database schema and seed authority accounts for CampusVoice.

Usage:
  python scripts/create_and_seed_db.py             # run with env-vars or .env configured
  python scripts/create_and_seed_db.py --drop      # drop (dev only) then recreate and seed
  python scripts/create_and_seed_db.py --show      # show seeded authority accounts after run

Notes:
- This script uses the project's existing setup utilities (`setup_database.py`).
- Configure DB connection by setting `DATABASE_URL` in a `.env` file or environment.
  See scripts/README_DB_SETUP.md for details.

"""
import asyncio
import argparse
import logging
import os
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("create_and_seed_db")


def parse_args():
    p = argparse.ArgumentParser(description="Create DB schema and seed authority accounts")
    p.add_argument("--drop", action="store_true", help="Drop existing tables first (Development only)")
    p.add_argument("--show", action="store_true", help="Show authority accounts after seeding")
    p.add_argument("--retries", type=int, default=5, help="Number of connection retries")
    p.add_argument("--retry-delay", type=int, default=3, help="Seconds between retries")
    return p.parse_args()


async def run(drop: bool = False, show: bool = False, retries: int = 5, retry_delay: int = 3) -> int:
    """Main orchestration: validate connection, create tables, seed authorities."""
    # Ensure project root is on sys.path so `setup_database` can be imported
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        # Import inside function so script can be copied/used without importing at module import time
        from setup_database import test_connection, create_tables, seed_authorities, drop_all_tables
        from src.database.connection import AsyncSessionLocal
        from sqlalchemy import text
    except Exception as e:
        logger.error("Failed to import project utilities. Are you running from project root? %s", e)
        return 2

    # Show which DATABASE_URL will be used (masked)
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if db_url:
        masked = mask_db_url(db_url)
        logger.info("Using database URL: %s", masked)
    else:
        logger.warning("No DATABASE_URL environment variable detected. Ensure `src/config/settings.py` loads from .env or env vars.")

    # Wait for DB to become available with retries
    for attempt in range(1, retries + 1):
        try:
            ok = await test_connection()
            if ok:
                logger.info("Database connection successful")
                break
        except Exception as e:
            logger.warning("Connection test failed (attempt %d/%d): %s", attempt, retries, e)

        if attempt == retries:
            logger.error("Unable to connect to database after %d attempts", retries)
            return 3

        await asyncio.sleep(retry_delay)

    # Optionally drop tables (dev only)
    if drop:
        if os.environ.get("ENVIRONMENT", "development") == "production":
            logger.error("Refusing to drop tables in production environment. Set ENVIRONMENT appropriately to proceed.")
            return 4
        logger.warning("Dropping all tables (development only)...")
        try:
            await drop_all_tables()
        except Exception as e:
            logger.error("Failed to drop tables: %s", e)
            return 5

    # Create tables
    try:
        logger.info("Creating database tables (idempotent)...")
        await create_tables()
    except Exception as e:
        logger.error("Failed to create tables: %s", e)
        return 6

    # Seed authorities
    try:
        logger.info("Seeding authority accounts (idempotent)...")
        await seed_authorities()
    except Exception as e:
        logger.error("Failed to seed authorities: %s", e)
        return 7

    # Optionally show seeded authorities
    if show:
        try:
            async with AsyncSessionLocal() as s:
                r = await s.execute(text("SELECT email, authority_type, authority_level FROM authorities ORDER BY authority_level DESC, email"))
                rows = r.fetchall()
                print("\nAuthority accounts in DB:")
                for row in rows:
                    print(f" - {row[0]} | {row[1]} | level={row[2]}")
        except Exception as e:
            logger.warning("Could not list authorities: %s", e)

    logger.info("Success: DB schema ensured and authorities seeded")
    return 0


def mask_db_url(url: Optional[str]) -> str:
    if not url:
        return "(not set)"
    try:
        # basic masking: hide password
        if "@" in url and ":" in url.split("@")[0]:
            pre, rest = url.split("@", 1)
            userpass = pre.split("//", 1)[-1]
            if ":" in userpass:
                user, _pw = userpass.split(":", 1)
                return url.replace(userpass, f"{user}:****")
        # fallback: truncate
        return url[:50] + "..."
    except Exception:
        return "(masked)"


if __name__ == "__main__":
    args = parse_args()
    try:
        rc = asyncio.run(run(drop=args.drop, show=args.show, retries=args.retries, retry_delay=args.retry_delay))
        sys.exit(rc)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(10)
