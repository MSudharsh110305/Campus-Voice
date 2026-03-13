"""
Data lifecycle / retention service for CampusVoice.

Implements:
  - Spam hard-delete  : 30 days after spam_flagged_at (no active dispute)
  - Resolved soft-delete: 10 months after resolved_at
  - Resolved hard-delete: 6 months after deleted_at
  - Closed soft-delete  : 2 years after updated_at
  - Closed hard-delete  : 6 months after deleted_at

Scheduling:
  - run_retention_sweep() is called once at startup (in connection.py init_db)
  - schedule_daily_sweep() loops every 24 hours via asyncio.create_task()

All operations are idempotent — safe to run multiple times.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Complaint, AuthorityUpdate

logger = logging.getLogger(__name__)


async def run_retention_sweep(db: AsyncSession) -> None:
    """
    Execute one full retention sweep.

    Steps (each idempotent):
      1. Hard-delete spam complaints whose 30-day window has expired and are
         not in an active dispute / active appeal.
      2. Soft-delete Resolved complaints older than 10 months.
      3. Hard-delete soft-deleted Resolved complaints older than 6 months.
      4. Soft-delete Closed complaints older than 2 years.
      5. Hard-delete soft-deleted Closed complaints older than 6 months.
    """
    now = datetime.now(timezone.utc)

    # ── 1. SPAM hard-delete ──────────────────────────────────────────────────
    # Eligibility:
    #   - status == "Spam" (or is_marked_as_spam == True)
    #   - spam_flagged_at <= now - 30 days
    #   - NOT currently under active dispute:
    #       has_disputed == False   (never disputed), OR
    #       dispute_status == "Admin_Rejected" AND appeal_deadline < now
    spam_cutoff = now - timedelta(days=30)

    spam_query = select(Complaint).where(
        and_(
            Complaint.is_marked_as_spam == True,
            Complaint.spam_flagged_at <= spam_cutoff,
            Complaint.is_deleted == False,
            or_(
                # Case A: never disputed at all
                Complaint.has_disputed == False,
                # Case B: disputed but admin rejected AND appeal period also over
                and_(
                    Complaint.dispute_status == "Admin_Rejected",
                    or_(
                        Complaint.appeal_deadline == None,
                        Complaint.appeal_deadline < now,
                    ),
                ),
            ),
        )
    )
    result = await db.execute(spam_query)
    spam_complaints = result.scalars().all()

    spam_deleted = 0
    for complaint in spam_complaints:
        await db.delete(complaint)
        spam_deleted += 1

    if spam_deleted:
        await db.commit()
        logger.info(f"Retention sweep: hard-deleted {spam_deleted} expired spam complaint(s)")

    # ── 2. RESOLVED soft-delete (10 months) ─────────────────────────────────
    resolved_soft_cutoff = now - timedelta(days=304)  # ~10 months (30.4 days * 10)

    resolved_soft_query = select(Complaint).where(
        and_(
            Complaint.status == "Resolved",
            Complaint.resolved_at != None,
            Complaint.resolved_at <= resolved_soft_cutoff,
            Complaint.is_deleted == False,
        )
    )
    result = await db.execute(resolved_soft_query)
    to_soft_delete_resolved = result.scalars().all()

    soft_resolved = 0
    for complaint in to_soft_delete_resolved:
        complaint.is_deleted = True
        complaint.deleted_at = now
        soft_resolved += 1

    if soft_resolved:
        await db.commit()
        logger.info(f"Retention sweep: soft-deleted {soft_resolved} aged Resolved complaint(s)")

    # ── 3. RESOLVED hard-delete (6 months after soft-delete) ─────────────────
    resolved_hard_cutoff = now - timedelta(days=183)  # ~6 months

    resolved_hard_query = select(Complaint).where(
        and_(
            Complaint.status == "Resolved",
            Complaint.is_deleted == True,
            Complaint.deleted_at != None,
            Complaint.deleted_at <= resolved_hard_cutoff,
        )
    )
    result = await db.execute(resolved_hard_query)
    to_hard_delete_resolved = result.scalars().all()

    hard_resolved = 0
    for complaint in to_hard_delete_resolved:
        await db.delete(complaint)
        hard_resolved += 1

    if hard_resolved:
        await db.commit()
        logger.info(f"Retention sweep: hard-deleted {hard_resolved} long-soft-deleted Resolved complaint(s)")

    # ── 4. CLOSED soft-delete (2 years) ──────────────────────────────────────
    closed_soft_cutoff = now - timedelta(days=730)  # 2 years

    closed_soft_query = select(Complaint).where(
        and_(
            Complaint.status == "Closed",
            Complaint.updated_at <= closed_soft_cutoff,
            Complaint.is_deleted == False,
        )
    )
    result = await db.execute(closed_soft_query)
    to_soft_delete_closed = result.scalars().all()

    soft_closed = 0
    for complaint in to_soft_delete_closed:
        complaint.is_deleted = True
        complaint.deleted_at = now
        soft_closed += 1

    if soft_closed:
        await db.commit()
        logger.info(f"Retention sweep: soft-deleted {soft_closed} aged Closed complaint(s)")

    # ── 5. CLOSED hard-delete (6 months after soft-delete) ───────────────────
    closed_hard_cutoff = now - timedelta(days=183)

    closed_hard_query = select(Complaint).where(
        and_(
            Complaint.status == "Closed",
            Complaint.is_deleted == True,
            Complaint.deleted_at != None,
            Complaint.deleted_at <= closed_hard_cutoff,
        )
    )
    result = await db.execute(closed_hard_query)
    to_hard_delete_closed = result.scalars().all()

    hard_closed = 0
    for complaint in to_hard_delete_closed:
        await db.delete(complaint)
        hard_closed += 1

    if hard_closed:
        await db.commit()
        logger.info(f"Retention sweep: hard-deleted {hard_closed} long-soft-deleted Closed complaint(s)")

    # ── 6. ANNOUNCEMENT expiry ────────────────────────────────────────────────
    # Deactivate AuthorityUpdate rows whose expires_at has passed but is_active is still True.
    # This complements the query-time filter (expires_at > NOW()) already applied in the
    # student notices feed and authority my-notices endpoints.
    expire_result = await db.execute(
        update(AuthorityUpdate)
        .where(
            and_(
                AuthorityUpdate.expires_at < now,
                AuthorityUpdate.expires_at != None,
                AuthorityUpdate.is_active == True,
            )
        )
        .values(is_active=False)
        .execution_options(synchronize_session=False)
    )
    announcements_expired = expire_result.rowcount or 0
    if announcements_expired:
        await db.commit()
        logger.info(f"Retention sweep: deactivated {announcements_expired} expired announcement(s)")

    logger.info(
        f"Retention sweep complete — "
        f"spam_hd={spam_deleted}, "
        f"resolved_sd={soft_resolved}, resolved_hd={hard_resolved}, "
        f"closed_sd={soft_closed}, closed_hd={hard_closed}, "
        f"announcements_expired={announcements_expired}"
    )


async def schedule_daily_sweep() -> None:
    """
    Background loop: run a retention sweep once per day indefinitely.

    Started via asyncio.create_task() in connection.py init_db().
    Uses its own DB session per sweep so it never blocks request handling.
    """
    # Import here to avoid circular imports at module load time
    from src.database.connection import AsyncSessionLocal

    while True:
        await asyncio.sleep(86400)  # wait 24 hours before the next sweep
        try:
            async with AsyncSessionLocal() as session:
                await run_retention_sweep(session)
        except Exception as e:
            logger.error(f"Daily retention sweep failed: {e}", exc_info=True)
