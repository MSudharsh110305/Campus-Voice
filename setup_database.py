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
    """Seed all authority accounts (matching connection.py exactly)."""
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
                    "name": "Admin User",
                    "email": "admin@srec.ac.in",
                    "password": "Admin@123456",
                    "authority_type": "Admin",
                    "authority_level": 100,
                    "designation": "System Administrator",
                    "department_id": None,
                },
                # Administrative Officer (General complaints)
                {
                    "name": "Mr. Suresh Reddy",
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
                    "designation": "Disciplinary Committee Chair",
                    "department_id": None,
                },
                # Senior Deputy Warden (shared for both hostels)
                {
                    "name": "Dr. Venkat Rao",
                    "email": "sdw@srec.ac.in",
                    "password": "SeniorDW@123",
                    "authority_type": "Senior Deputy Warden",
                    "authority_level": 15,
                    "designation": "Senior Deputy Warden",
                    "department_id": None,
                },
                # Men's Hostel Deputy Warden
                {
                    "name": "Mr. Ramesh Kumar",
                    "email": "dw.mens@srec.ac.in",
                    "password": "MensDW@1234",
                    "authority_type": "Men's Hostel Deputy Warden",
                    "authority_level": 10,
                    "designation": "Deputy Warden - Men's Hostel",
                    "department_id": None,
                },
                # Men's Hostel Wardens (2)
                {
                    "name": "Mr. Srinivas Reddy",
                    "email": "warden1.mens@srec.ac.in",
                    "password": "MensW1@1234",
                    "authority_type": "Men's Hostel Warden",
                    "authority_level": 5,
                    "designation": "Warden - Men's Hostel Block A",
                    "department_id": None,
                },
                {
                    "name": "Mr. Prakash Rao",
                    "email": "warden2.mens@srec.ac.in",
                    "password": "MensW2@1234",
                    "authority_type": "Men's Hostel Warden",
                    "authority_level": 5,
                    "designation": "Warden - Men's Hostel Block B",
                    "department_id": None,
                },
                # Women's Hostel Deputy Warden
                {
                    "name": "Mrs. Lakshmi Devi",
                    "email": "dw.womens@srec.ac.in",
                    "password": "WomensDW@123",
                    "authority_type": "Women's Hostel Deputy Warden",
                    "authority_level": 10,
                    "designation": "Deputy Warden - Women's Hostel",
                    "department_id": None,
                },
                # Women's Hostel Wardens (2)
                {
                    "name": "Mrs. Padma Sharma",
                    "email": "warden1.womens@srec.ac.in",
                    "password": "WomensW1@123",
                    "authority_type": "Women's Hostel Warden",
                    "authority_level": 5,
                    "designation": "Warden - Women's Hostel Block A",
                    "department_id": None,
                },
                {
                    "name": "Mrs. Kavitha Reddy",
                    "email": "warden2.womens@srec.ac.in",
                    "password": "WomensW2@123",
                    "authority_type": "Women's Hostel Warden",
                    "authority_level": 5,
                    "designation": "Warden - Women's Hostel Block B",
                    "department_id": None,
                },
            ]

            # HODs for all departments found in DB
            hod_data = [
                ("CSE", "Dr. Priya Sharma", "hod.cse@srec.ac.in"),
                ("ECE", "Dr. Suresh Babu", "hod.ece@srec.ac.in"),
                ("MECH", "Dr. Krishna Murthy", "hod.mech@srec.ac.in"),
                ("CIVIL", "Dr. Ravi Kumar", "hod.civil@srec.ac.in"),
                ("EEE", "Dr. Narayana Rao", "hod.eee@srec.ac.in"),
                ("IT", "Dr. Srikanth Reddy", "hod.it@srec.ac.in"),
                ("BIO", "Dr. Lakshmi Prasad", "hod.bio@srec.ac.in"),
                ("AERO", "Dr. Vijay Kumar", "hod.aero@srec.ac.in"),
                ("RAA", "Dr. Satish Chandra", "hod.raa@srec.ac.in"),
                ("EIE", "Dr. Ramana Reddy", "hod.eie@srec.ac.in"),
                ("MBA", "Dr. Rajendra Prasad", "hod.mba@srec.ac.in"),
                ("AIDS", "Dr. Kiran Kumar", "hod.aids@srec.ac.in"),
                ("MTECH_CSE", "Dr. Srinivasa Rao", "hod.mtechcse@srec.ac.in"),
            ]

            for dept_code, name, email in hod_data:
                dept_id = dept_map.get(dept_code)
                if dept_id:
                    authorities.append({
                        "name": name,
                        "email": email,
                        "password": f"Hod{dept_code}@123",
                        "authority_type": "HOD",
                        "authority_level": 8,
                        "designation": f"Head of Department - {dept_code}",
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
        print("Login Credentials:")
        print()
        print("  ADMIN:")
        print(f"    Email:    admin@srec.ac.in")
        print(f"    Password: Admin@123456")
        print()
        print("  ADMIN OFFICER:")
        print(f"    Email:    officer@srec.ac.in")
        print(f"    Password: Officer@1234")
        print()
        print("  MEN'S HOSTEL WARDEN:")
        print(f"    Email:    warden1.mens@srec.ac.in")
        print(f"    Password: MensW1@1234")
        print()
        print("  WOMEN'S HOSTEL WARDEN:")
        print(f"    Email:    warden1.womens@srec.ac.in")
        print(f"    Password: WomensW1@123")
        print()
        print("  HOD CSE:")
        print(f"    Email:    hod.cse@srec.ac.in")
        print(f"    Password: HodCSE@123")
        print()
        print("  See credentials.txt for full list")
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
