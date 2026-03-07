"""
Database connection management with async support.
Handles engine creation, session management, and database initialization.
"""

import logging
import asyncio
from typing import AsyncGenerator, Optional, Callable, Any
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)
from sqlalchemy import text, event
from sqlalchemy.exc import OperationalError, DatabaseError
from src.config.settings import settings

logger = logging.getLogger(__name__)


# ==================== ENGINE CREATION ====================

def create_engine() -> AsyncEngine:
    """
    Create async database engine with connection pooling.
    
    Returns:
        AsyncEngine: Configured async database engine
    
    Raises:
        ValueError: If DATABASE_URL is invalid
    
    Note:
        For async engines, SQLAlchemy automatically uses async-compatible pooling.
    """
    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            connect_args={
                "server_settings": {
                    "application_name": settings.APP_NAME,
                    "jit": "off",
                },
                "command_timeout": 60,
                "timeout": 30,
            },
        )
        
        logger.info(
            f"✅ Database engine created: "
            f"pool_size={settings.DB_POOL_SIZE}, "
            f"max_overflow={settings.DB_MAX_OVERFLOW}, "
            f"pool_recycle={settings.DB_POOL_RECYCLE}s, "
            f"environment={settings.ENVIRONMENT}"
        )
        
        return engine
    
    except Exception as e:
        logger.error(f"❌ Failed to create database engine: {e}")
        raise


engine: AsyncEngine = create_engine()


# ==================== CONNECTION EVENT LISTENERS ====================

@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log new database connections"""
    if settings.DB_ECHO:
        logger.debug(f"🔌 New database connection established: {id(dbapi_conn)}")


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout from pool"""
    if settings.DB_ECHO:
        logger.debug(f"📤 Connection checked out from pool: {id(dbapi_conn)}")


@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log connection return to pool"""
    if settings.DB_ECHO:
        logger.debug(f"📥 Connection returned to pool: {id(dbapi_conn)}")


# ==================== SESSION FACTORY ====================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Usage:
        ```python
        from fastapi import Depends
        from src.database.connection import get_db
        
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
        ```
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database session error: {e}", exc_info=True)
            raise


# ==================== DATABASE INITIALIZATION ====================

async def create_all_tables():
    """
    Create all database tables from SQLAlchemy models.
    Called during application startup.
    """
    from src.database.models import Base
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
    
    except Exception as e:
        # Ignore IntegrityError from race condition when multiple workers
        # try to create tables simultaneously (e.g. gunicorn with 2+ workers)
        if "already exists" in str(e):
            logger.warning("⚠️ Tables already exist (likely created by another worker), skipping")
        else:
            logger.error(f"❌ Failed to create database tables: {e}", exc_info=True)
            raise


async def drop_all_tables():
    """
    Drop all database tables.
    
    ⚠️ WARNING: Use only in development/testing!
    """
    if settings.is_production:
        raise RuntimeError("❌ Cannot drop tables in production environment!")
    
    from src.database.models import Base
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("⚠️ All database tables dropped")
    
    except Exception as e:
        logger.error(f"❌ Failed to drop database tables: {e}", exc_info=True)
        raise


async def init_db(retry_attempts: int = 3, retry_delay: int = 5):
    """
    Initialize database with tables and seed data.
    Called during application startup.
    
    Args:
        retry_attempts: Number of retry attempts on failure
        retry_delay: Delay between retries in seconds
    """
    logger.info("🔄 Initializing database...")
    
    for attempt in range(1, retry_attempts + 1):
        try:
            await create_all_tables()

            # Schema migrations for new columns (idempotent)
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE authority_updates "
                        "ADD COLUMN IF NOT EXISTS target_gender VARCHAR[] NULL"
                    ))
                    logger.info("✅ Migration: authority_updates.target_gender ensured")
                except Exception as me:
                    logger.debug(f"Migration note (target_gender): {me}")

            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE complaints "
                        "ADD COLUMN IF NOT EXISTS reach INTEGER NOT NULL DEFAULT 0"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints "
                        "ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0"
                    ))
                    logger.info("✅ Migration: complaints.reach + complaints.view_count ensured")
                except Exception as me:
                    logger.debug(f"Migration note (reach/view_count): {me}")

            # New columns for disputes + authority attachments
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS has_disputed BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS appeal_reason TEXT"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS authority_attachment_data BYTEA"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS authority_attachment_filename VARCHAR(255)"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS authority_attachment_mimetype VARCHAR(100)"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS authority_attachment_size INTEGER"
                    ))
                    logger.info("✅ Migration: complaint dispute + authority attachment columns ensured")
                except Exception as me:
                    logger.debug(f"Migration note (dispute/attachment cols): {me}")

            # Campus reputation for students
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE students ADD COLUMN IF NOT EXISTS campus_reputation INTEGER NOT NULL DEFAULT 0"
                    ))
                    logger.info("✅ Migration: students.campus_reputation ensured")
                except Exception as me:
                    logger.debug(f"Migration note (campus_reputation): {me}")

            # Petition scope + publish flag
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE petitions ADD COLUMN IF NOT EXISTS petition_scope VARCHAR(20) NOT NULL DEFAULT 'General'"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE petitions ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
                    logger.info("✅ Migration: petition petition_scope + is_published ensured")
                except Exception as me:
                    logger.debug(f"Migration note (petition scope/publish): {me}")

            # Petition goal + deadline columns
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE petitions ADD COLUMN IF NOT EXISTS custom_goal INTEGER"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE petitions ADD COLUMN IF NOT EXISTS deadline TIMESTAMPTZ"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE petitions ADD COLUMN IF NOT EXISTS goal_reached_notified BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
                    logger.info("✅ Migration: petition custom_goal + deadline + goal_reached_notified ensured")
                except Exception as me:
                    logger.debug(f"Migration note (petition goal/deadline): {me}")

            # Petition tables — created by create_all if they don't exist, but
            # explicitly ensured here so existing DBs pick them up on restart.
            async with engine.begin() as conn:
                try:
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS petitions (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            title VARCHAR(255) NOT NULL,
                            description TEXT NOT NULL,
                            created_by_roll_no VARCHAR(20) NOT NULL
                                REFERENCES students(roll_no) ON DELETE CASCADE,
                            category_id INTEGER REFERENCES complaint_categories(id) ON DELETE SET NULL,
                            department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
                            signature_count INTEGER NOT NULL DEFAULT 0,
                            milestone_goal INTEGER NOT NULL DEFAULT 50,
                            milestones_reached INTEGER[] NOT NULL DEFAULT '{}',
                            status VARCHAR(50) NOT NULL DEFAULT 'Open',
                            authority_response TEXT,
                            responded_by_id BIGINT REFERENCES authorities(id) ON DELETE SET NULL,
                            responded_at TIMESTAMPTZ,
                            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                    """))
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS petition_signatures (
                            id BIGSERIAL PRIMARY KEY,
                            petition_id UUID NOT NULL
                                REFERENCES petitions(id) ON DELETE CASCADE,
                            student_roll_no VARCHAR(20) NOT NULL
                                REFERENCES students(roll_no) ON DELETE CASCADE,
                            signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            CONSTRAINT uq_petition_signature UNIQUE (petition_id, student_roll_no)
                        )
                    """))
                    # Indexes
                    await conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_petition_status_created "
                        "ON petitions(status, submitted_at)"
                    ))
                    await conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_petition_sig_petition "
                        "ON petition_signatures(petition_id)"
                    ))
                    logger.info("✅ Migration: petitions + petition_signatures tables ensured")
                except Exception as me:
                    logger.debug(f"Migration note (petitions): {me}")

            # Student representatives table
            async with engine.begin() as conn:
                try:
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS student_representatives (
                            id BIGSERIAL PRIMARY KEY,
                            student_roll_no VARCHAR(20) NOT NULL
                                REFERENCES students(roll_no) ON DELETE CASCADE,
                            department_id INTEGER NOT NULL
                                REFERENCES departments(id) ON DELETE CASCADE,
                            year INTEGER NOT NULL,
                            scope VARCHAR(20) NOT NULL,
                            appointed_by_id BIGINT
                                REFERENCES authorities(id) ON DELETE SET NULL,
                            is_active BOOLEAN NOT NULL DEFAULT TRUE,
                            appointed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            removed_at TIMESTAMPTZ,
                            CONSTRAINT uq_rep_student_scope UNIQUE (student_roll_no, scope)
                        )
                    """))
                    await conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_rep_dept_year_scope "
                        "ON student_representatives(department_id, year, scope, is_active)"
                    ))
                    logger.info("✅ Migration: student_representatives table ensured")
                except Exception as me:
                    logger.debug(f"Migration note (student_representatives): {me}")

            # Notice file attachments
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE authority_updates ADD COLUMN IF NOT EXISTS attachment_data BYTEA"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE authority_updates ADD COLUMN IF NOT EXISTS attachment_filename VARCHAR(255)"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE authority_updates ADD COLUMN IF NOT EXISTS attachment_mimetype VARCHAR(100)"
                    ))
                    logger.info("✅ Migration: authority_updates attachment columns ensured")
                except Exception as me:
                    logger.debug(f"Migration note (notice attachments): {me}")

            # complainant_department_id: track submitter's department for cross-dept visibility (Rule D2)
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "complainant_department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL"
                    ))
                    await conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_complaint_complainant_dept "
                        "ON complaints(complainant_department_id) WHERE complainant_department_id IS NOT NULL"
                    ))
                    logger.info("✅ Migration: complaints.complainant_department_id ensured")
                except Exception as me:
                    logger.debug(f"Migration note (complainant_department_id): {me}")

            # Complaint merge columns (LLM auto-merge for duplicate clustering)
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "merged_into_id UUID REFERENCES complaints(id) ON DELETE SET NULL"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "is_merged_canonical BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
                    await conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_complaint_merged_into "
                        "ON complaints(merged_into_id) WHERE merged_into_id IS NOT NULL"
                    ))
                    logger.info("✅ Migration: complaint merge columns ensured")
                except Exception as me:
                    logger.debug(f"Migration note (complaint merge): {me}")

            # Ensure critical authorities exist (DC + SDW) using raw SQL + ON CONFLICT
            # This runs every startup and is idempotent — safe to call repeatedly.
            async with engine.begin() as conn:
                try:
                    from src.services.auth_service import auth_service as _as
                    _dc_hash  = _as.hash_password("Discip@12345")
                    _sdw_hash = _as.hash_password("SeniorDW@123")
                    await conn.execute(text("""
                        INSERT INTO authorities
                            (name, email, password_hash, authority_type, authority_level,
                             designation, is_active, created_at, updated_at)
                        VALUES
                            ('Dr. Anand Verma',  'dc@srec.ac.in',  :dc_hash,
                             'Disciplinary Committee', 20, 'Disciplinary Committee Head',
                             TRUE, NOW(), NOW()),
                            ('Mr. Venkat Rao',   'sdw@srec.ac.in', :sdw_hash,
                             'Senior Deputy Warden',  15, 'Senior Deputy Warden',
                             TRUE, NOW(), NOW())
                        ON CONFLICT (email) DO NOTHING
                    """), {"dc_hash": _dc_hash, "sdw_hash": _sdw_hash})
                    logger.info("✅ Migration: DC and SDW authorities ensured")
                except Exception as me:
                    logger.warning(f"Migration note (DC/SDW authority): {me}")

            # System settings table (configurable key-value store for admin)
            async with engine.begin() as conn:
                try:
                    await conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS system_settings (
                            key VARCHAR(100) PRIMARY KEY,
                            value VARCHAR(500) NOT NULL,
                            description TEXT,
                            updated_by_id BIGINT REFERENCES authorities(id) ON DELETE SET NULL,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                    """))
                    # Seed default settings if not present
                    await conn.execute(text("""
                        INSERT INTO system_settings (key, value, description)
                        VALUES ('petition_cooldown_days', '7', 'Legacy: Minimum days between petition creations per representative')
                        ON CONFLICT (key) DO NOTHING
                    """))
                    await conn.execute(text("""
                        INSERT INTO system_settings (key, value, description)
                        VALUES ('petition_weekly_limit', '1', 'Number of petitions a representative can create per week (0 = unlimited)')
                        ON CONFLICT (key) DO NOTHING
                    """))
                    logger.info("✅ Migration: system_settings table ensured")
                except Exception as me:
                    logger.debug(f"Migration note (system_settings): {me}")

            # Dispute window + soft-delete columns (data lifecycle system)
            async with engine.begin() as conn:
                try:
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "dispute_deadline TIMESTAMPTZ"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "dispute_status VARCHAR(20)"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "appeal_deadline TIMESTAMPTZ"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
                    await conn.execute(text(
                        "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                        "deleted_at TIMESTAMPTZ"
                    ))
                    # Backfill dispute_deadline for existing spam complaints that are missing it
                    await conn.execute(text(
                        "UPDATE complaints "
                        "SET dispute_deadline = spam_flagged_at + INTERVAL '7 days' "
                        "WHERE is_marked_as_spam = TRUE "
                        "  AND spam_flagged_at IS NOT NULL "
                        "  AND dispute_deadline IS NULL"
                    ))
                    logger.info("✅ Migration: complaint dispute_deadline + soft-delete columns ensured")
                except Exception as me:
                    logger.debug(f"Migration note (dispute/soft-delete cols): {me}")

            async with AsyncSessionLocal() as session:
                from src.database.models import Department

                result = await session.execute(text("SELECT COUNT(*) FROM departments"))
                count = result.scalar()

                if count == 0:
                    logger.info("📦 Database is empty, seeding initial data...")
                    await seed_initial_data(session)
                else:
                    logger.info(f"✅ Database already contains {count} departments")
                    # Still seed authorities if missing
                    await seed_authorities(session)
                    # Ensure any newly-added authorities (e.g. SDW) are inserted
                    await seed_missing_authorities(session)

            logger.info("✅ Database initialization complete")

            # Start retention sweep on startup and schedule daily loop
            try:
                from src.services.retention_service import run_retention_sweep, schedule_daily_sweep
                async with AsyncSessionLocal() as sweep_session:
                    await run_retention_sweep(sweep_session)
                asyncio.create_task(schedule_daily_sweep())
                logger.info("✅ Retention service started")
            except Exception as re:
                logger.warning(f"Retention service startup warning: {re}")

            return

        except OperationalError as e:
            if attempt < retry_attempts:
                logger.warning(
                    f"⚠️ Database initialization attempt {attempt}/{retry_attempts} failed. "
                    f"Retrying in {retry_delay}s... Error: {e}"
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"❌ Database initialization failed after {retry_attempts} attempts: {e}")
                raise
        
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
            raise


async def seed_initial_data(session: AsyncSession):
    """
    Seed initial data (departments and categories).
    
    Args:
        session: Database session
    """
    from src.database.models import Department, ComplaintCategory
    from src.config.constants import DEPARTMENTS, CATEGORIES
    
    try:
        for dept_data in DEPARTMENTS:
            dept = Department(
                code=dept_data["code"],
                name=dept_data["name"],
                hod_name=dept_data.get("hod_name"),
                hod_email=dept_data.get("hod_email"),
            )
            session.add(dept)
        
        logger.info(f"✅ Added {len(DEPARTMENTS)} departments")
        
        for cat_data in CATEGORIES:
            category = ComplaintCategory(
                name=cat_data["name"],
                description=cat_data["description"],
                keywords=cat_data.get("keywords", []),
            )
            session.add(category)
        
        logger.info(f"✅ Added {len(CATEGORIES)} complaint categories")
        
        await session.commit()
        logger.info("✅ Initial data seeded successfully")

        # Seed default authorities
        await seed_authorities(session)

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Failed to seed initial data: {e}", exc_info=True)
        raise


async def seed_authorities(session: AsyncSession):
    """Seed default authority accounts for SREC college."""
    from src.database.models import Authority
    from src.services.auth_service import auth_service

    try:
        result = await session.execute(text("SELECT COUNT(*) FROM authorities"))
        count = result.scalar()
        if count and count > 0:
            logger.info(f"✅ Authorities already seeded ({count} found)")
            return

        # Get department IDs for HOD assignments
        dept_result = await session.execute(text("SELECT id, code FROM departments"))
        dept_map = {row[1]: row[0] for row in dept_result.fetchall()}

        # Canonical 23 authority accounts
        authorities = [
            # Admin
            {
                "name": "Super Admin",
                "email": "admin@srec.ac.in",
                "password": "Admin@123456",
                "authority_type": "Admin",
                "authority_level": 100,
                "designation": "System Administrator",
                "department_id": None,
            },
            # Admin Officer
            {
                "name": "Dr. R. Krishnamurthy",
                "email": "officer@srec.ac.in",
                "password": "Officer@1234",
                "authority_type": "Admin Officer",
                "authority_level": 50,
                "designation": "Administrative Officer",
                "department_id": None,
            },
            # Disciplinary Committee
            {
                "name": "Dr. Anand Verma",
                "email": "dc@srec.ac.in",
                "password": "Discip@12345",
                "authority_type": "Disciplinary Committee",
                "authority_level": 20,
                "designation": "Disciplinary Committee Head",
                "department_id": None,
            },
            # Senior Deputy Warden
            {
                "name": "Mr. Venkat Rao",
                "email": "sdw@srec.ac.in",
                "password": "SeniorDW@123",
                "authority_type": "Senior Deputy Warden",
                "authority_level": 15,
                "designation": "Senior Deputy Warden",
                "department_id": None,
            },
            # Men's Hostel Deputy Warden
            {
                "name": "Mr. K. Venkatesh",
                "email": "dw.mens@srec.ac.in",
                "password": "MensDW@1234",
                "authority_type": "Men's Hostel Deputy Warden",
                "authority_level": 10,
                "designation": "Men's Hostel Deputy Warden",
                "department_id": None,
            },
            # Men's Hostel Wardens
            {
                "name": "Mr. N. Selvakumar",
                "email": "warden1.mens@srec.ac.in",
                "password": "MensW1@1234",
                "authority_type": "Men's Hostel Warden",
                "authority_level": 5,
                "designation": "Men's Hostel Warden – Block A",
                "department_id": None,
            },
            {
                "name": "Mr. D. Murugesan",
                "email": "warden2.mens@srec.ac.in",
                "password": "MensW2@1234",
                "authority_type": "Men's Hostel Warden",
                "authority_level": 5,
                "designation": "Men's Hostel Warden – Block B",
                "department_id": None,
            },
            # Women's Hostel Deputy Warden
            {
                "name": "Mrs. P. Saraswathi",
                "email": "dw.womens@srec.ac.in",
                "password": "WomensDW@123",
                "authority_type": "Women's Hostel Deputy Warden",
                "authority_level": 10,
                "designation": "Women's Hostel Deputy Warden",
                "department_id": None,
            },
            # Women's Hostel Wardens
            {
                "name": "Mrs. L. Divya",
                "email": "warden1.womens@srec.ac.in",
                "password": "WomensW1@123",
                "authority_type": "Women's Hostel Warden",
                "authority_level": 5,
                "designation": "Women's Hostel Warden – Block E",
                "department_id": None,
            },
            {
                "name": "Mrs. B. Kavitha",
                "email": "warden2.womens@srec.ac.in",
                "password": "WomensW2@123",
                "authority_type": "Women's Hostel Warden",
                "authority_level": 5,
                "designation": "Women's Hostel Warden – Block F",
                "department_id": None,
            },
        ]

        # HODs for the 13 canonical departments
        hod_data = [
            ("CSE",       "Dr. A. Balasubramanian", "hod.cse@srec.ac.in",      "HodCSE@123"),
            ("ECE",       "Dr. V. Sundaram",        "hod.ece@srec.ac.in",      "HodECE@123"),
            ("MECH",      "Dr. P. Ganesan",         "hod.mech@srec.ac.in",     "HodMECH@123"),
            ("CIVIL",     "Dr. S. Murugan",         "hod.civil@srec.ac.in",    "HodCIVIL@123"),
            ("EEE",       "Dr. R. Jayakumar",       "hod.eee@srec.ac.in",      "HodEEE@123"),
            ("IT",        "Dr. K. Muthukumar",      "hod.it@srec.ac.in",       "HodIT@123"),
            ("BIO",       "Dr. N. Anbazhagan",      "hod.bio@srec.ac.in",      "HodBIO@123"),
            ("AERO",      "Dr. C. Senthilkumar",    "hod.aero@srec.ac.in",     "HodAERO@123"),
            ("RAA",       "Dr. M. Rajendran",       "hod.raa@srec.ac.in",      "HodRAA@123"),
            ("EIE",       "Dr. T. Sivasubramanian", "hod.eie@srec.ac.in",      "HodEIE@123"),
            ("MBA",       "Dr. R. Arumugam",        "hod.mba@srec.ac.in",      "HodMBA@123"),
            ("AIDS",      "Dr. S. Karthikeyan",     "hod.aids@srec.ac.in",     "HodAIDS@123"),
            ("MTECH_CSE", "Dr. V. Ramasamy",        "hod.mtechcse@srec.ac.in", "HodMTECH_CSE@123"),
        ]

        for dept_code, name, email, password in hod_data:
            dept_id = dept_map.get(dept_code)
            if dept_id:
                authorities.append({
                    "name": name,
                    "email": email,
                    "password": password,
                    "authority_type": "HOD",
                    "authority_level": 8,
                    "designation": f"Head of Department – {dept_code}",
                    "department_id": dept_id,
                })

        for auth_data in authorities:
            password = auth_data.pop("password")
            auth_data["password_hash"] = auth_service.hash_password(password)
            authority = Authority(**auth_data)
            session.add(authority)

        await session.commit()
        logger.info(f"✅ Seeded {len(authorities)} default authorities")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Failed to seed authorities: {e}", exc_info=True)


async def seed_missing_authorities(session: AsyncSession):
    """Insert any authority accounts that are in the canonical list but missing from the DB.

    This is safe to call every startup — it only inserts rows whose email
    doesn't already exist (INSERT ... ON CONFLICT DO NOTHING equivalent via
    checking before insert).
    """
    from src.database.models import Authority
    from src.services.auth_service import auth_service
    from sqlalchemy import select as sa_select

    # Minimal list of authorities that must always exist.
    # Add new authorities here when the org chart changes.
    required = [
        {
            "name": "Dr. Anand Verma",
            "email": "dc@srec.ac.in",
            "password": "Discip@12345",
            "authority_type": "Disciplinary Committee",
            "authority_level": 20,
            "designation": "Disciplinary Committee Head",
            "department_id": None,
        },
        {
            "name": "Mr. Venkat Rao",
            "email": "sdw@srec.ac.in",
            "password": "SeniorDW@123",
            "authority_type": "Senior Deputy Warden",
            "authority_level": 15,
            "designation": "Senior Deputy Warden",
            "department_id": None,
        },
    ]

    try:
        inserted = 0
        for auth_data in required:
            existing = await session.execute(
                sa_select(Authority).where(Authority.email == auth_data["email"])
            )
            if existing.scalar_one_or_none() is not None:
                continue
            hashed = auth_service.hash_password(auth_data["password"])
            authority = Authority(
                name=auth_data["name"],
                email=auth_data["email"],
                password_hash=hashed,
                authority_type=auth_data["authority_type"],
                authority_level=auth_data["authority_level"],
                designation=auth_data.get("designation"),
                department_id=auth_data.get("department_id"),
                is_active=True,
            )
            session.add(authority)
            inserted += 1

        if inserted:
            await session.commit()
            logger.info(f"✅ seed_missing_authorities: inserted {inserted} missing authority/ies")
        else:
            logger.debug("✅ seed_missing_authorities: all required authorities present")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ seed_missing_authorities failed: {e}", exc_info=True)


# ==================== SREC MIGRATION ====================

async def migrate_to_srec():
    """
    Migrate existing database to SREC college format.
    - Updates email domains from @college.edu or @campusvoice.edu to @srec.ac.in
    - Updates Hostel category to Men's Hostel and adds Women's Hostel

    Call this once to migrate an existing database.
    """
    logger.info("🔄 Starting SREC migration...")

    async with AsyncSessionLocal() as session:
        try:
            # Update student emails from @college.edu to @srec.ac.in
            await session.execute(
                text("""
                    UPDATE students
                    SET email = REPLACE(email, '@college.edu', '@srec.ac.in')
                    WHERE email LIKE '%@college.edu'
                """)
            )
            logger.info("✅ Updated student emails")

            # Update authority emails from @campusvoice.edu to @srec.ac.in
            await session.execute(
                text("""
                    UPDATE authorities
                    SET email = REPLACE(email, '@campusvoice.edu', '@srec.ac.in')
                    WHERE email LIKE '%@campusvoice.edu'
                """)
            )
            logger.info("✅ Updated authority emails")

            # Check if old "Hostel" category exists
            result = await session.execute(
                text("SELECT id FROM complaint_categories WHERE name = 'Hostel'")
            )
            old_hostel_id = result.scalar()

            if old_hostel_id:
                # Rename old Hostel to Men's Hostel
                await session.execute(
                    text("""
                        UPDATE complaint_categories
                        SET name = 'Men''s Hostel',
                            description = 'Men''s hostel facilities, cleanliness, room issues, mess complaints, amenities'
                        WHERE name = 'Hostel'
                    """)
                )
                logger.info("✅ Renamed Hostel category to Men's Hostel")

                # Check if Women's Hostel already exists
                result = await session.execute(
                    text("SELECT id FROM complaint_categories WHERE name = 'Women''s Hostel'")
                )
                womens_hostel_exists = result.scalar()

                if not womens_hostel_exists:
                    # Add Women's Hostel category (using PostgreSQL ARRAY syntax)
                    await session.execute(
                        text("""
                            INSERT INTO complaint_categories (name, description, keywords, is_active, created_at)
                            VALUES (
                                'Women''s Hostel',
                                'Women''s hostel facilities, cleanliness, room issues, mess complaints, amenities',
                                ARRAY['room', 'hostel', 'warden', 'bed', 'hall', 'mess', 'food', 'water', 'bathroom', 'toilet', 'shower', 'ac', 'fan', 'electricity', 'women', 'girls', 'ladies'],
                                true,
                                NOW()
                            )
                        """)
                    )
                    logger.info("✅ Added Women's Hostel category")

            # Update old authority types to new hostel-specific types
            await session.execute(
                text("""
                    UPDATE authorities
                    SET authority_type = 'Men''s Hostel Warden'
                    WHERE authority_type = 'Warden'
                    AND (designation LIKE '%Men%' OR designation LIKE '%Block A%' OR designation LIKE '%Block B%')
                """)
            )

            await session.execute(
                text("""
                    UPDATE authorities
                    SET authority_type = 'Men''s Hostel Deputy Warden'
                    WHERE authority_type = 'Deputy Warden'
                    AND (designation LIKE '%Men%' OR department_id IS NULL)
                """)
            )

            await session.commit()
            logger.info("✅ SREC migration completed successfully")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ SREC migration failed: {e}", exc_info=True)
            raise


async def update_categories_for_srec():
    """
    Update complaint categories for SREC.
    Adds Men's Hostel and Women's Hostel if not present.
    """
    async with AsyncSessionLocal() as session:
        try:
            from src.config.constants import CATEGORIES

            for cat_data in CATEGORIES:
                # Check if category exists
                result = await session.execute(
                    text("SELECT id FROM complaint_categories WHERE name = :name"),
                    {"name": cat_data["name"]}
                )
                existing = result.scalar()

                if not existing:
                    await session.execute(
                        text("""
                            INSERT INTO complaint_categories (name, description, keywords)
                            VALUES (:name, :description, :keywords)
                        """),
                        {
                            "name": cat_data["name"],
                            "description": cat_data["description"],
                            "keywords": str(cat_data.get("keywords", []))
                        }
                    )
                    logger.info(f"✅ Added category: {cat_data['name']}")

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Failed to update categories: {e}", exc_info=True)


# ==================== DATABASE HEALTH CHECK ====================

async def health_check() -> bool:
    """
    Check database connectivity.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


async def get_db_info() -> dict:
    """
    Get database connection information.
    
    Returns:
        dict: Database info including version, pool status, etc.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            
            result = await session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            )
            connections = result.scalar()
            
            result = await session.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            )
            db_size = result.scalar()
            
            result = await session.execute(
                text("""
                    SELECT count(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
            )
            table_count = result.scalar()
            
            return {
                "healthy": True,
                "version": version.split(",")[0] if version else "Unknown",
                "connections": connections,
                "database_size": db_size,
                "table_count": table_count,
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_recycle": settings.DB_POOL_RECYCLE,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "environment": settings.ENVIRONMENT,
            }
    
    except Exception as e:
        logger.error(f"❌ Failed to get database info: {e}", exc_info=True)
        return {"healthy": False, "error": str(e)}


async def get_pool_status() -> dict:
    """
    Get connection pool status.
    
    Returns:
        dict: Pool statistics
    """
    try:
        pool = engine.pool
        
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get pool status: {e}")
        return {"error": str(e)}


# ==================== CLEANUP ====================

async def close_db():
    """
    Close database connections.
    Called during application shutdown.
    """
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    
    except Exception as e:
        logger.error(f"❌ Failed to close database connections: {e}", exc_info=True)


# ==================== TRANSACTION HELPERS ====================

async def execute_in_transaction(
    session: AsyncSession, 
    func: Callable, 
    *args, 
    **kwargs
) -> Any:
    """
    Execute a function within a database transaction.
    
    Args:
        session: Database session
        func: Async function to execute
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        Result of the function
    """
    try:
        result = await func(session, *args, **kwargs)
        await session.commit()
        return result
    
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Transaction failed: {e}", exc_info=True)
        raise


async def execute_with_retry(
    func: Callable,
    *args,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs
) -> Any:
    """
    Execute a database operation with retry logic.
    
    Args:
        func: Async function to execute
        *args: Function arguments
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        **kwargs: Function keyword arguments
    
    Returns:
        Result of the function
    """
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        
        except (OperationalError, DatabaseError) as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"⚠️ Database operation failed (attempt {attempt}/{max_retries}). "
                    f"Retrying in {retry_delay}s... Error: {e}"
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    f"❌ Database operation failed after {max_retries} attempts: {e}",
                    exc_info=True
                )
    
    raise last_exception


# ==================== TESTING HELPERS ====================

async def test_connection():
    """
    Test database connection.
    
    Returns:
        bool: True if connection successful
    """
    try:
        logger.info("🔍 Testing database connection...")
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT current_database(), current_user"))
            db_name, db_user = result.fetchone()
            
            logger.info(f"✅ Connected to database '{db_name}' as user '{db_user}'")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}", exc_info=True)
        return False


async def reset_database():
    """
    Reset database (drop and recreate tables with seed data).
    
    ⚠️ WARNING: Use only in development/testing!
    """
    if settings.is_production:
        raise RuntimeError("❌ Cannot reset database in production!")
    
    logger.warning("⚠️ Resetting database...")
    
    await drop_all_tables()
    await create_all_tables()
    
    async with AsyncSessionLocal() as session:
        await seed_initial_data(session)
    
    logger.info("✅ Database reset complete")


# ==================== EXPORT ====================

__all__ = [
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "create_all_tables",
    "drop_all_tables",
    "init_db",
    "seed_initial_data",
    "seed_authorities",
    "seed_missing_authorities",
    "health_check",
    "get_db_info",
    "get_pool_status",
    "test_connection",
    "close_db",
    "execute_in_transaction",
    "execute_with_retry",
    "reset_database",
    "migrate_to_srec",
    "update_categories_for_srec",
]
