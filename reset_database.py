"""
Database reset script.

⚠️  WARNING: This will DROP ALL TABLES and recreate them!

✅ FIXED: Correct table names for verification
"""

import asyncio
from sqlalchemy import text

from src.database.connection import AsyncSessionLocal, engine
from src.database.models import (
    Base,
    Student, Authority, Department, ComplaintCategory,
    Complaint, Vote, StatusUpdate, AuthorityUpdate, Notification
)

import logging
logger = logging.getLogger(__name__)


async def reset_database():
    """Drop all tables and recreate them."""
    print("=" * 80)
    print("⚠️  DATABASE RESET - THIS WILL DELETE ALL DATA!")
    print("=" * 80)
    
    # Confirm
    response = input("\nAre you sure you want to reset the database? (yes/no): ")
    
    if response.lower() != "yes":
        print("❌ Reset cancelled")
        return
    
    try:
        # Step 1: Drop all tables
        print("\n1. Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("   ✅ All tables dropped")
        
        # Step 2: Create all tables
        print("\n2. Creating all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("   ✅ All tables created")
        
        # Step 3: Verify tables
        print("\n3. Verifying tables...")
        async with AsyncSessionLocal() as session:
            # ✅ FIXED: Check correct table names
            tables_to_check = [
                "departments",
                "categories",                # ✅ Changed from complaint_categories
                "students",
                "authorities",
                "complaints",
                "complaint_votes",           # ✅ Changed from votes
                "complaint_status_history",  # ✅ Added
                "authority_updates",         # ✅ Added
                "student_notifications"      # ✅ Changed from notifications
            ]
            
            for table in tables_to_check:
                try:
                    result = await session.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    )
                    count = result.scalar()
                    print(f"   ✅ {table}: {count} records")
                except Exception as e:
                    print(f"   ❌ {table}: {e}")
        
        print("\n" + "=" * 80)
        print("✅ DATABASE RESET COMPLETE!")
        print("=" * 80)
        print("\n💡 Next steps:")
        print("   1. Run 'python scripts/setup_database.py' to seed initial data")
        print("   2. Run 'python main.py' to start the application")
    
    except Exception as e:
        print(f"\n❌ Reset failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(reset_database())
