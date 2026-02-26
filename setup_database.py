"""
Complete database setup script.

Creates tables, seeds initial data, and creates admin user.
Synced with connection.py seeding logic for consistency.
"""

import asyncio
from sqlalchemy import text

from src.database.connection import AsyncSessionLocal, engine
from src.database.models import (
    Base, Department, ComplaintCategory, Authority,
    Student, Complaint, Vote, StatusUpdate, AuthorityUpdate, Notification
)
from src.services.auth_service import auth_service
from src.config.settings import settings
from src.config.constants import DEPARTMENTS, CATEGORIES

import logging
logger = logging.getLogger(__name__)


async def test_connection():
    """Test database connection."""
    print("Testing database connection...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"  Connected to: {version}")
            return True
    except Exception as e:
        print(f"  Connection failed: {e}")
        return False


async def drop_all_tables():
    """Drop all existing tables."""
    print("Dropping all existing tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("  All tables dropped successfully")
    except Exception as e:
        print(f"  Error dropping tables: {e}")


async def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("  Tables created successfully!")

        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"  Created tables: {', '.join(tables)}")
    except Exception as e:
        print(f"  Error creating tables: {e}")
        raise


async def seed_departments():
    """Seed departments from constants.py (all 13)."""
    print("\nSeeding departments...")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM departments"))
            count = result.scalar()

            if count > 0:
                print(f"  Departments already exist ({count} records), skipping...")
                return

            for dept_data in DEPARTMENTS:
                dept = Department(
                    code=dept_data["code"],
                    name=dept_data["name"],
                    hod_name=dept_data.get("hod_name"),
                    hod_email=dept_data.get("hod_email"),
                )
                session.add(dept)

            await session.commit()
            print(f"  Seeded {len(DEPARTMENTS)} departments")

        except Exception as e:
            await session.rollback()
            print(f"  Error seeding departments: {e}")
            raise


async def seed_categories():
    """Seed complaint categories from constants.py (5 categories)."""
    print("\nSeeding complaint categories...")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM complaint_categories"))
            count = result.scalar()

            if count > 0:
                print(f"  Categories already exist ({count} records), skipping...")
                return

            for cat_data in CATEGORIES:
                category = ComplaintCategory(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    keywords=cat_data.get("keywords", []),
                )
                session.add(category)

            await session.commit()
            print(f"  Seeded {len(CATEGORIES)} categories:")
            for cat_data in CATEGORIES:
                print(f"    - {cat_data['name']}")

        except Exception as e:
            await session.rollback()
            print(f"  Error seeding categories: {e}")
            raise


async def seed_authorities():
    """Seed canonical authority accounts only."""
    print("\nSeeding authorities...")
    async with AsyncSessionLocal() as session:
        try:
            # Fetch existing authority emails so we only insert missing accounts
            result = await session.execute(text("SELECT email FROM authorities"))
            existing_emails = {row[0] for row in result.fetchall()}

            # Get department IDs for HOD assignments
            dept_result = await session.execute(text("SELECT id, code FROM departments"))
            dept_map = {row[1]: row[0] for row in dept_result.fetchall()}

            authorities = [
                # System Admin
                {
                    "name": "Super Admin",
                    "email": "admin@srec.ac.in",
                    "password": "Admin@123456",
                    "authority_type": "Admin",
                    "authority_level": 100,
                    "designation": "System Administrator",
                    "department_id": None,
                },
                # Administrative Officer (General complaints)
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
                    "name": "Prof. S. Rajagopal",
                    "email": "dc@srec.ac.in",
                    "password": "Discip@12345",
                    "authority_type": "Disciplinary Committee",
                    "authority_level": 20,
                    "designation": "Disciplinary Committee Head",
                    "department_id": None,
                },
                # Senior Deputy Warden (shared for both hostels)
                {
                    "name": "Dr. M. Subramanian",
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
                # Men's Hostel Wardens (2)
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
                # Women's Hostel Wardens (2)
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

            # HODs for all 17 departments — canonical passwords
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
                ("ENG",       "Dr. P. Meenakshisundaram","hod.english@srec.ac.in",  "English@123"),
                ("PHY",       "Dr. K. Annamalai",       "hod.physics@srec.ac.in",  "Physics@123"),
                ("CHEM",      "Dr. R. Thirumalai",      "hod.chemistry@srec.ac.in","Chemistry@123"),
                ("MATH",      "Dr. S. Venkataraman",    "hod.mathematics@srec.ac.in","Math@123456"),
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

            added = []
            for auth_data in authorities:
                email = auth_data.get("email")
                if email in existing_emails:
                    print(f"    - Skipping existing authority: {email}")
                    continue

                password = auth_data.pop("password")
                auth_data["password_hash"] = auth_service.hash_password(password)
                authority = Authority(**auth_data)
                session.add(authority)
                added.append(auth_data)

            if added:
                await session.commit()
                print(f"  Seeded {len(added)} new authorities:")
                for auth_data in added:
                    print(f"    - {auth_data.get('designation', '?')} ({auth_data.get('authority_type', '?')}): {auth_data.get('email', '?')}")
            else:
                print("  No new authorities to seed; all configured accounts already exist.")

        except Exception as e:
            await session.rollback()
            print(f"  Error seeding authorities: {e}")
            raise


async def verify_schema():
    """Verify database schema includes all required columns."""
    print("\nVerifying database schema...")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'students'
                AND column_name IN ('year', 'roll_no', 'email', 'gender', 'stay_type')
                ORDER BY ordinal_position
            """))
            student_columns = result.fetchall()

            print("  Students table key columns:")
            for col in student_columns:
                print(f"    - {col[0]}: {col[1]} (nullable: {col[2]})")

        except Exception as e:
            print(f"  Schema verification warning: {e}")


async def print_summary():
    """Print setup summary."""
    print("\n" + "=" * 80)
    print("DATABASE SETUP SUMMARY")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        try:
            tables = {
                "departments": "Departments",
                "complaint_categories": "Categories",
                "authorities": "Authorities",
                "students": "Students",
                "complaints": "Complaints"
            }

            for table, label in tables.items():
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  {label}: {count} records")

        except Exception as e:
            print(f"  Could not generate summary: {e}")


async def main():
    """Run all setup tasks."""
    print("=" * 80)
    print("CampusVoice Database Setup")
    print("=" * 80)
    print()

    try:
        connected = await test_connection()
        if not connected:
            print("\nCannot proceed without database connection")
            return
        print()

        response = input("Drop existing tables and start fresh? (yes/no): ")
        if response.lower() == "yes":
            await drop_all_tables()
            print()

        await create_tables()
        await seed_departments()
        await seed_categories()
        await seed_authorities()
        await verify_schema()
        await print_summary()

        print()
        print("=" * 80)
        print("DATABASE SETUP COMPLETE!")
        print("=" * 80)
        print()
        print("Login Credentials (see credentials.txt for full list):")
        print()
        print("  ADMIN:")
        print(f"    Email:    admin@srec.ac.in")
        print(f"    Password: Admin@SREC2024")
        print()
        print("  ADMIN OFFICER:")
        print(f"    Email:    adminofficer@srec.ac.in")
        print(f"    Password: AdminOfficer@2024")
        print()
        print("  MEN'S HOSTEL WARDEN (Block A):")
        print(f"    Email:    mwarden1@srec.ac.in")
        print(f"    Password: MWarden1@2024")
        print()
        print("  WOMEN'S HOSTEL WARDEN (Block E):")
        print(f"    Email:    fwarden1@srec.ac.in")
        print(f"    Password: FWarden1@2024")
        print()
        print("  HOD CSE:")
        print(f"    Email:    hod.cse@srec.ac.in")
        print(f"    Password: HodCSE@2024")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print(f"Setup failed: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
