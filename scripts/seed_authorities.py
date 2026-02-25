"""
Seed script: create all authority accounts for SREC CampusVoice.

Run from project root:
    python scripts/seed_authorities.py

Requires a running PostgreSQL database (DATABASE_URL in .env).
"""

import asyncio
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config.settings import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────
# Authority definitions
# ─────────────────────────────────────────────

AUTHORITIES = [
    # ── Admin ────────────────────────────────
    {
        "name": "Super Admin",
        "email": "admin@srec.ac.in",
        "password": "Admin@SREC2024",
        "authority_type": "Admin",
        "authority_level": 100,
        "designation": "System Administrator",
        "department_code": None,
        "phone": "9000000001",
    },

    # ── Admin Officer ─────────────────────────
    {
        "name": "Dr. R. Krishnamurthy",
        "email": "adminofficer@srec.ac.in",
        "password": "AdminOfficer@2024",
        "authority_type": "Admin Officer",
        "authority_level": 50,
        "designation": "Administrative Officer",
        "department_code": None,
        "phone": "9000000002",
    },

    # ── Disciplinary Committee ────────────────
    {
        "name": "Prof. S. Rajagopal",
        "email": "discipline@srec.ac.in",
        "password": "Discipline@2024",
        "authority_type": "Disciplinary Committee",
        "authority_level": 20,
        "designation": "Disciplinary Committee Head",
        "department_code": None,
        "phone": "9000000003",
    },

    # ── Senior Deputy Warden ──────────────────
    {
        "name": "Dr. M. Subramanian",
        "email": "srdepwarden@srec.ac.in",
        "password": "SrDepWarden@2024",
        "authority_type": "Senior Deputy Warden",
        "authority_level": 15,
        "designation": "Senior Deputy Warden",
        "department_code": None,
        "phone": "9000000004",
    },

    # ── Men's Hostel Deputy Wardens ───────────
    {
        "name": "Mr. K. Venkatesh",
        "email": "mdeputywarden1@srec.ac.in",
        "password": "MDepWarden1@2024",
        "authority_type": "Men's Hostel Deputy Warden",
        "authority_level": 10,
        "designation": "Men's Hostel Deputy Warden – Block A & B",
        "department_code": None,
        "phone": "9000000005",
    },
    {
        "name": "Mr. T. Arunkumar",
        "email": "mdeputywarden2@srec.ac.in",
        "password": "MDepWarden2@2024",
        "authority_type": "Men's Hostel Deputy Warden",
        "authority_level": 10,
        "designation": "Men's Hostel Deputy Warden – Block C & D",
        "department_code": None,
        "phone": "9000000006",
    },

    # ── Women's Hostel Deputy Wardens ─────────
    {
        "name": "Mrs. P. Saraswathi",
        "email": "fdeputywarden1@srec.ac.in",
        "password": "FDepWarden1@2024",
        "authority_type": "Women's Hostel Deputy Warden",
        "authority_level": 10,
        "designation": "Women's Hostel Deputy Warden – Block E & F",
        "department_code": None,
        "phone": "9000000007",
    },

    # ── Men's Hostel Wardens ──────────────────
    {
        "name": "Mr. N. Selvakumar",
        "email": "mwarden1@srec.ac.in",
        "password": "MWarden1@2024",
        "authority_type": "Men's Hostel Warden",
        "authority_level": 5,
        "designation": "Men's Hostel Warden – Block A",
        "department_code": None,
        "phone": "9000000008",
    },
    {
        "name": "Mr. D. Murugesan",
        "email": "mwarden2@srec.ac.in",
        "password": "MWarden2@2024",
        "authority_type": "Men's Hostel Warden",
        "authority_level": 5,
        "designation": "Men's Hostel Warden – Block B",
        "department_code": None,
        "phone": "9000000009",
    },
    {
        "name": "Mr. G. Ramesh",
        "email": "mwarden3@srec.ac.in",
        "password": "MWarden3@2024",
        "authority_type": "Men's Hostel Warden",
        "authority_level": 5,
        "designation": "Men's Hostel Warden – Block C",
        "department_code": None,
        "phone": "9000000010",
    },

    # ── Women's Hostel Wardens ────────────────
    {
        "name": "Mrs. L. Divya",
        "email": "fwarden1@srec.ac.in",
        "password": "FWarden1@2024",
        "authority_type": "Women's Hostel Warden",
        "authority_level": 5,
        "designation": "Women's Hostel Warden – Block E",
        "department_code": None,
        "phone": "9000000011",
    },
    {
        "name": "Mrs. B. Kavitha",
        "email": "fwarden2@srec.ac.in",
        "password": "FWarden2@2024",
        "authority_type": "Women's Hostel Warden",
        "authority_level": 5,
        "designation": "Women's Hostel Warden – Block F",
        "department_code": None,
        "phone": "9000000012",
    },

    # ── HODs (one per department, 13 total) ───
    {
        "name": "Dr. A. Balasubramanian",
        "email": "hod.cse@srec.ac.in",
        "password": "HodCSE@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – CSE",
        "department_code": "CSE",
        "phone": "9000000013",
    },
    {
        "name": "Dr. V. Sundaram",
        "email": "hod.ece@srec.ac.in",
        "password": "HodECE@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – ECE",
        "department_code": "ECE",
        "phone": "9000000014",
    },
    {
        "name": "Dr. P. Ganesan",
        "email": "hod.mech@srec.ac.in",
        "password": "HodMECH@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – MECH",
        "department_code": "MECH",
        "phone": "9000000015",
    },
    {
        "name": "Dr. S. Murugan",
        "email": "hod.civil@srec.ac.in",
        "password": "HodCIVIL@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – CIVIL",
        "department_code": "CIVIL",
        "phone": "9000000016",
    },
    {
        "name": "Dr. R. Jayakumar",
        "email": "hod.eee@srec.ac.in",
        "password": "HodEEE@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – EEE",
        "department_code": "EEE",
        "phone": "9000000017",
    },
    {
        "name": "Dr. K. Muthukumar",
        "email": "hod.it@srec.ac.in",
        "password": "HodIT@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – IT",
        "department_code": "IT",
        "phone": "9000000018",
    },
    {
        "name": "Dr. N. Anbazhagan",
        "email": "hod.bio@srec.ac.in",
        "password": "HodBIO@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – BIO",
        "department_code": "BIO",
        "phone": "9000000019",
    },
    {
        "name": "Dr. C. Senthilkumar",
        "email": "hod.aero@srec.ac.in",
        "password": "HodAERO@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – AERO",
        "department_code": "AERO",
        "phone": "9000000020",
    },
    {
        "name": "Dr. M. Rajendran",
        "email": "hod.raa@srec.ac.in",
        "password": "HodRAA@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – RAA",
        "department_code": "RAA",
        "phone": "9000000021",
    },
    {
        "name": "Dr. T. Sivasubramanian",
        "email": "hod.eie@srec.ac.in",
        "password": "HodEIE@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – EIE",
        "department_code": "EIE",
        "phone": "9000000022",
    },
    {
        "name": "Dr. R. Arumugam",
        "email": "hod.mba@srec.ac.in",
        "password": "HodMBA@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – MBA",
        "department_code": "MBA",
        "phone": "9000000023",
    },
    {
        "name": "Dr. S. Karthikeyan",
        "email": "hod.aids@srec.ac.in",
        "password": "HodAIDS@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – AIDS",
        "department_code": "AIDS",
        "phone": "9000000024",
    },
    {
        "name": "Dr. V. Ramasamy",
        "email": "hod.mtechcse@srec.ac.in",
        "password": "HodMTECH@2024",
        "authority_type": "HOD",
        "authority_level": 8,
        "designation": "Head of Department – M.Tech CSE",
        "department_code": "MTECH_CSE",
        "phone": "9000000025",
    },
]


# ─────────────────────────────────────────────
# Seed function
# ─────────────────────────────────────────────

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
            # Skip if email already exists
            exists = await session.execute(
                text("SELECT id FROM authorities WHERE email = :email"),
                {"email": auth["email"]}
            )
            if exists.scalar_one_or_none():
                print(f"  SKIP  {auth['email']} (already exists)")
                skipped += 1
                continue

            dept_id = dept_map.get(auth["department_code"]) if auth["department_code"] else None
            hashed = pwd_ctx.hash(auth["password"])

            await session.execute(
                text("""
                    INSERT INTO authorities
                        (name, email, password_hash, phone, authority_type, department_id,
                         designation, authority_level, is_active)
                    VALUES
                        (:name, :email, :password_hash, :phone, :authority_type, :department_id,
                         :designation, :authority_level, true)
                """),
                {
                    "name": auth["name"],
                    "email": auth["email"],
                    "password_hash": hashed,
                    "phone": auth["phone"],
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
