"""
migrate_v2.py — Phase 2 schema migration

Adds 7 new columns to the `complaints` table:
  - is_anonymous          BOOLEAN NOT NULL DEFAULT FALSE
  - satisfaction_rating   SMALLINT (1-5, nullable)
  - satisfaction_feedback TEXT (nullable)
  - rated_at              TIMESTAMPTZ (nullable)
  - resolution_note       TEXT (nullable)
  - duplicate_of_id       UUID FK -> complaints.id (nullable, SET NULL)

Also adds:
  - CHECK constraint: satisfaction_rating BETWEEN 1 AND 5
  - INDEX on is_anonymous (for filtering anon feed)
  - INDEX on duplicate_of_id (for FK lookups)
  - INDEX on satisfaction_rating (for admin analytics queries)

SAFE TO RUN ON EXISTING DATA — all new columns are nullable or have defaults.

Usage:
    python migrate_v2.py
    python migrate_v2.py --dry-run   (print SQL only, no execution)
    python migrate_v2.py --rollback  (remove the new columns)
"""

import asyncio
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


FORWARD_SQL = [
    # ── 1. is_anonymous ────────────────────────────────────────────────────────
    """
    ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS is_anonymous BOOLEAN NOT NULL DEFAULT FALSE;
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_complaint_anonymous
    ON complaints (is_anonymous)
    WHERE is_anonymous = TRUE;
    """,

    # ── 2. satisfaction_rating ─────────────────────────────────────────────────
    """
    ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS satisfaction_rating SMALLINT
    CONSTRAINT check_satisfaction_rating
        CHECK (satisfaction_rating IS NULL OR (satisfaction_rating >= 1 AND satisfaction_rating <= 5));
    """,

    # ── 3. satisfaction_feedback ───────────────────────────────────────────────
    """
    ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS satisfaction_feedback TEXT;
    """,

    # ── 4. rated_at ────────────────────────────────────────────────────────────
    """
    ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS rated_at TIMESTAMPTZ;
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_complaint_satisfaction
    ON complaints (satisfaction_rating)
    WHERE satisfaction_rating IS NOT NULL;
    """,

    # ── 5. resolution_note ─────────────────────────────────────────────────────
    """
    ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS resolution_note TEXT;
    """,

    # ── 6. duplicate_of_id ─────────────────────────────────────────────────────
    """
    ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS duplicate_of_id UUID
    REFERENCES complaints(id) ON DELETE SET NULL;
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_complaint_duplicate_of
    ON complaints (duplicate_of_id)
    WHERE duplicate_of_id IS NOT NULL;
    """,
]

ROLLBACK_SQL = [
    "DROP INDEX IF EXISTS idx_complaint_duplicate_of;",
    "DROP INDEX IF EXISTS idx_complaint_satisfaction;",
    "DROP INDEX IF EXISTS idx_complaint_anonymous;",
    "ALTER TABLE complaints DROP COLUMN IF EXISTS duplicate_of_id;",
    "ALTER TABLE complaints DROP COLUMN IF EXISTS resolution_note;",
    "ALTER TABLE complaints DROP COLUMN IF EXISTS rated_at;",
    "ALTER TABLE complaints DROP COLUMN IF EXISTS satisfaction_feedback;",
    "ALTER TABLE complaints DROP COLUMN IF EXISTS satisfaction_rating;",
    "ALTER TABLE complaints DROP COLUMN IF EXISTS is_anonymous;",
]

VERIFY_SQL = """
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'complaints'
  AND column_name IN (
      'is_anonymous', 'satisfaction_rating', 'satisfaction_feedback',
      'rated_at', 'resolution_note', 'duplicate_of_id'
  )
ORDER BY column_name;
"""


async def run_migration(dry_run: bool = False, rollback: bool = False):
    from src.database.connection import engine
    from sqlalchemy import text

    statements = ROLLBACK_SQL if rollback else FORWARD_SQL
    mode = "ROLLBACK" if rollback else "FORWARD"

    print(f"\n{'='*60}")
    print(f"  CampusVoice v2 Schema Migration — {mode}")
    print(f"  dry_run={dry_run}")
    print(f"{'='*60}\n")

    if dry_run:
        print("DRY RUN — SQL that would be executed:\n")
        for i, stmt in enumerate(statements, 1):
            print(f"--- Statement {i} ---")
            print(stmt.strip())
            print()
        return
    async with engine.begin() as conn:
        for i, stmt in enumerate(statements, 1):
            stmt_preview = stmt.strip().split('\n')[0][:60]
            print(f"  [{i}/{len(statements)}] {stmt_preview}...")
            try:
                await conn.execute(text(stmt))
                print(f"         OK")
            except Exception as exc:
                print(f"         ERROR: {exc}")
                raise

    print(f"\n  Migration {mode} complete.\n")

    # Verify columns exist
    print("  Verifying columns...")
    async with engine.connect() as conn:
        result = await conn.execute(text(VERIFY_SQL))
        rows = result.fetchall()
        if not rows:
            print("  WARNING: No v2 columns found — migration may not have applied.")
        else:
            for row in rows:
                print(f"    column={row[0]:<30} type={row[1]:<20} nullable={row[2]}")
    print()


def main():
    dry_run = "--dry-run" in sys.argv
    rollback = "--rollback" in sys.argv

    if rollback and dry_run:
        print("Cannot combine --dry-run and --rollback. Pick one.")
        sys.exit(1)

    asyncio.run(run_migration(dry_run=dry_run, rollback=rollback))


if __name__ == "__main__":
    main()
