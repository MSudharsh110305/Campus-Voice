"""
Cleanup script: remove all non-canonical authority accounts from the database.

All FK references use CASCADE or SET NULL, so PostgreSQL handles cleanup
automatically when we delete the authority rows.

Canonical accounts (23 total) — kept by email:
  admin@srec.ac.in, officer@srec.ac.in, dc@srec.ac.in, sdw@srec.ac.in,
  dw.mens@srec.ac.in, warden1.mens@srec.ac.in, warden2.mens@srec.ac.in,
  dw.womens@srec.ac.in, warden1.womens@srec.ac.in, warden2.womens@srec.ac.in,
  hod.cse … hod.mtechcse@srec.ac.in

Run from project root:
    python scripts/cleanup_authorities.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config.settings import settings

CANONICAL_EMAILS = {
    "admin@srec.ac.in",
    "officer@srec.ac.in",
    "dc@srec.ac.in",
    "sdw@srec.ac.in",
    "dw.mens@srec.ac.in",
    "warden1.mens@srec.ac.in",
    "warden2.mens@srec.ac.in",
    "dw.womens@srec.ac.in",
    "warden1.womens@srec.ac.in",
    "warden2.womens@srec.ac.in",
    "hod.cse@srec.ac.in",
    "hod.ece@srec.ac.in",
    "hod.mech@srec.ac.in",
    "hod.civil@srec.ac.in",
    "hod.eee@srec.ac.in",
    "hod.it@srec.ac.in",
    "hod.bio@srec.ac.in",
    "hod.aero@srec.ac.in",
    "hod.raa@srec.ac.in",
    "hod.eie@srec.ac.in",
    "hod.mba@srec.ac.in",
    "hod.aids@srec.ac.in",
    "hod.mtechcse@srec.ac.in",
}


async def cleanup():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Show all current authorities
        result = await session.execute(
            text("SELECT id, email, name, authority_type FROM authorities ORDER BY id")
        )
        all_rows = result.fetchall()

        non_canonical_ids = []
        for aid, email, name, atype in all_rows:
            if email in CANONICAL_EMAILS:
                print(f"  KEEP   [{aid:3d}] {email:<40} ({atype})")
            else:
                non_canonical_ids.append(aid)
                print(f"  DELETE [{aid:3d}] {email:<40} ({atype})")

        if not non_canonical_ids:
            print("\nNo non-canonical authorities found — nothing to delete.")
            await engine.dispose()
            return

        print(f"\n  {len(all_rows) - len(non_canonical_ids)} kept, {len(non_canonical_ids)} to delete.")
        answer = input("\nProceed? (yes/no): ").strip().lower()
        if answer != "yes":
            print("Aborted.")
            await engine.dispose()
            return

        # 2. Build the IN clause
        if len(non_canonical_ids) == 1:
            id_clause = f"({non_canonical_ids[0]})"
        else:
            id_clause = str(tuple(non_canonical_ids))

        # 3. Delete — PostgreSQL CASCADE / SET NULL handles all FK references automatically
        await session.execute(
            text(f"DELETE FROM authorities WHERE id IN {id_clause}")
        )
        await session.commit()

        # 4. Summary
        result = await session.execute(
            text("SELECT id, email, name, authority_type, authority_level FROM authorities ORDER BY authority_level DESC, id")
        )
        rows = result.fetchall()
        print(f"\n✓ Done. {len(non_canonical_ids)} account(s) removed. {len(rows)} remaining:\n")
        for row in rows:
            print(f"  [{row[0]:3d}] L{row[4]:3d}  {row[1]:<40} ({row[2]})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup())
