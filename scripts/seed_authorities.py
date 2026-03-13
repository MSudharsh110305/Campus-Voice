"""
Seed script: create all canonical authority accounts for SREC CampusVoice.

23 canonical accounts only — any extra accounts should be removed first with
    python scripts/cleanup_authorities.py

Run from project root:
    python scripts/seed_authorities.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config.settings import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Canonical authority definitions ───────────────────────────────────────────

AUTHORITIES = [
    # ── Admin ─────────────────────────────────────────────────────────────────
    {
        "name": "Super Admin",
        "email": "admin@srec.ac.in",
        "password": "Admin@123456",
        "authority_type": "Admin",
        "authority_level": 100,
        "designation": "System Administrator",
        "department_code": None,
    },
    # ── Admin Officer ─────────────────────────────────────────────────────────
    {
        "name": "Dr. R. Krishnamurthy",
        "email": "officer@srec.ac.in",
        "password": "Officer@1234",
        "authority_type": "Admin Officer",
        "authority_level": 50,
        "designation": "Administrative Officer",
        "department_code": None,
    },
    # ── Disciplinary Committee ────────────────────────────────────────────────
    {
        "name": "Prof. S. Rajagopal",
        "email": "dc@srec.ac.in",
        "password": "Discip@12345",
        "authority_type": "Disciplinary Committee",
        "authority_level": 20,
        "designation": "Disciplinary Committee Head",
        "department_code": None,
    },
    # ── Senior Deputy Warden ──────────────────────────────────────────────────
    {
        "name": "Dr. M. Subramanian",
        "email": "sdw@srec.ac.in",
        "password": "SeniorDW@123",
        "authority_type": "Senior Deputy Warden",
        "authority_level": 15,
        "designation": "Senior Deputy Warden",
        "department_code": None,
    },
    # ── Men's Hostel Deputy Warden ────────────────────────────────────────────
    {
        "name": "Mr. K. Venkatesh",
        "email": "dw.mens@srec.ac.in",
        "password": "MensDW@1234",
        "authority_type": "Men's Hostel Deputy Warden",
        "authority_level": 10,
        "designation": "Men's Hostel Deputy Warden",
        "department_code": None,
    },
    # ── Men's Hostel Wardens ──────────────────────────────────────────────────
    {
        "name": "Mr. N. Selvakumar",
        "email": "warden1.mens@srec.ac.in",
        "password": "MensW1@1234",
        "authority_type": "Men's Hostel Warden",
        "authority_level": 5,
        "designation": "Men's Hostel Warden – Block A",
        "department_code": None,
    },
    {
        "name": "Mr. D. Murugesan",
        "email": "warden2.mens@srec.ac.in",
        "password": "MensW2@1234",
        "authority_type": "Men's Hostel Warden",
        "authority_level": 5,
        "designation": "Men's Hostel Warden – Block B",
        "department_code": None,
    },
    # ── Women's Hostel Deputy Warden ──────────────────────────────────────────
    {
        "name": "Mrs. P. Saraswathi",
        "email": "dw.womens@srec.ac.in",
        "password": "WomensDW@123",
        "authority_type": "Women's Hostel Deputy Warden",
        "authority_level": 10,
        "designation": "Women's Hostel Deputy Warden",
        "department_code": None,
    },
    # ── Women's Hostel Wardens ────────────────────────────────────────────────
    {
        "name": "Mrs. L. Divya",
        "email": "warden1.womens@srec.ac.in",
        "password": "WomensW1@123",
        "authority_type": "Women's Hostel Warden",
        "authority_level": 5,
        "designation": "Women's Hostel Warden – Block E",
        "department_code": None,
    },
    {
        "name": "Mrs. B. Kavitha",
        "email": "warden2.womens@srec.ac.in",
        "password": "WomensW2@123",
        "authority_type": "Women's Hostel Warden",
        "authority_level": 5,
        "designation": "Women's Hostel Warden – Block F",
        "department_code": None,
    },
    # ── HODs (13 canonical departments) ──────────────────────────────────────
    {"name": "Dr. A. Balasubramanian", "email": "hod.cse@srec.ac.in",      "password": "HodCSE@123",      "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – CSE",      "department_code": "CSE"},
    {"name": "Dr. V. Sundaram",        "email": "hod.ece@srec.ac.in",      "password": "HodECE@123",      "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – ECE",      "department_code": "ECE"},
    {"name": "Dr. P. Ganesan",         "email": "hod.mech@srec.ac.in",     "password": "HodMECH@123",     "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – MECH",     "department_code": "MECH"},
    {"name": "Dr. S. Murugan",         "email": "hod.civil@srec.ac.in",    "password": "HodCIVIL@123",    "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – CIVIL",    "department_code": "CIVIL"},
    {"name": "Dr. R. Jayakumar",       "email": "hod.eee@srec.ac.in",      "password": "HodEEE@123",      "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – EEE",      "department_code": "EEE"},
    {"name": "Dr. K. Muthukumar",      "email": "hod.it@srec.ac.in",       "password": "HodIT@123",       "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – IT",       "department_code": "IT"},
    {"name": "Dr. N. Anbazhagan",      "email": "hod.bio@srec.ac.in",      "password": "HodBIO@123",      "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – BIO",      "department_code": "BIO"},
    {"name": "Dr. C. Senthilkumar",    "email": "hod.aero@srec.ac.in",     "password": "HodAERO@123",     "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – AERO",     "department_code": "AERO"},
    {"name": "Dr. M. Rajendran",       "email": "hod.raa@srec.ac.in",      "password": "HodRAA@123",      "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – RAA",      "department_code": "RAA"},
    {"name": "Dr. T. Sivasubramanian", "email": "hod.eie@srec.ac.in",      "password": "HodEIE@123",      "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – EIE",      "department_code": "EIE"},
    {"name": "Dr. R. Arumugam",        "email": "hod.mba@srec.ac.in",      "password": "HodMBA@123",      "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – MBA",      "department_code": "MBA"},
    {"name": "Dr. S. Karthikeyan",     "email": "hod.aids@srec.ac.in",     "password": "HodAIDS@123",     "authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – AIDS",     "department_code": "AIDS"},
    {"name": "Dr. V. Ramasamy",        "email": "hod.mtechcse@srec.ac.in", "password": "HodMTECH_CSE@123","authority_type": "HOD", "authority_level": 8, "designation": "Head of Department – MTECH CSE", "department_code": "MTECH_CSE"},
]


# ── Seed function ──────────────────────────────────────────────────────────────

async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Build dept_code → dept_id lookup
        result = await session.execute(text("SELECT id, code FROM departments"))
        dept_map = {row.code: row.id for row in result}

        created = 0
        skipped = 0

        for auth in AUTHORITIES:
            exists = await session.execute(
                text("SELECT id FROM authorities WHERE email = :email"),
                {"email": auth["email"]}
            )
            if exists.scalar_one_or_none():
                print(f"  SKIP   {auth['email']} (already exists)")
                skipped += 1
                continue

            dept_id = dept_map.get(auth["department_code"]) if auth["department_code"] else None
            hashed = pwd_ctx.hash(auth["password"])

            await session.execute(
                text("""
                    INSERT INTO authorities
                        (name, email, password_hash, authority_type, department_id,
                         designation, authority_level, is_active)
                    VALUES
                        (:name, :email, :password_hash, :authority_type, :department_id,
                         :designation, :authority_level, true)
                """),
                {
                    "name": auth["name"],
                    "email": auth["email"],
                    "password_hash": hashed,
                    "authority_type": auth["authority_type"],
                    "department_id": dept_id,
                    "designation": auth["designation"],
                    "authority_level": auth["authority_level"],
                }
            )
            print(f"  CREATE {auth['email']}  [{auth['authority_type']}]")
            created += 1

        await session.commit()
        print(f"\n✓ Done — {created} created, {skipped} skipped.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
