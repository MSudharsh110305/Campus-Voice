"""
Database cleanup script.

Removes all data from tables while preserving structure.

✅ FIXED: Correct table names
✅ FIXED: Proper table order for foreign key dependencies
"""

import asyncio
from sqlalchemy import text

from src.database.connection import engine
from src.database.models import *  # Import all models to ensure they're registered

import logging
logger = logging.getLogger(__name__)


async def cleanup_database():
    """Remove all data from all tables while preserving structure."""
    print("\n" + "=" * 70)
    print("  CampusVoice Database Cleanup")
    print("=" * 70)
    print("\n⚠️  WARNING: This will delete ALL data from the database!")
    print("   Table structure will be preserved.\n")
    
    # Ask for confirmation
    confirm = input("Type 'YES' to proceed with cleanup: ")
    
    if confirm != "YES":
        print("\n❌ Cleanup cancelled.")
        return
    
    print("\n🔄 Starting database cleanup...\n")
    
    async with engine.begin() as conn:
        try:
            # Disable foreign key checks temporarily (PostgreSQL)
            await conn.execute(text("SET session_replication_role = 'replica';"))
            
            # ✅ FIXED: Correct table names and proper order
            tables_to_truncate = [
                "complaint_votes",           # ✅ Votes (child of complaints)
                "authority_updates",         # ✅ Authority updates (child of complaints)
                "complaint_status_history",  # ✅ Status history (child of complaints)
                "student_notifications",     # ✅ Notifications (child of students/complaints)
                "complaints",                # ✅ Complaints (child of students/categories)
                "students",                  # Students
                "authorities",               # Authorities
                "categories",                # ✅ FIXED: Changed from complaint_categories
                "departments",               # Departments
            ]
            
            print("📋 Tables to clean:")
            for table in tables_to_truncate:
                print(f"   - {table}")
            print()
            
            # Truncate each table
            for table_name in tables_to_truncate:
                try:
                    await conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"))
                    print(f"✅ Cleaned: {table_name}")
                except Exception as e:
                    print(f"⚠️  Warning for {table_name}: {e}")
            
            # Re-enable foreign key checks
            await conn.execute(text("SET session_replication_role = 'origin';"))
            
            print("\n✅ Database cleanup completed!")
            print("\n📊 Summary:")
            print("   - All user data removed")
            print("   - All complaints removed")
            print("   - All votes removed")
            print("   - All status history removed")
            print("   - Table structure preserved")
            print("\n💡 You can now run setup_database.py to reseed data.")
        
        except Exception as e:
            print(f"\n❌ Error during cleanup: {e}")
            import traceback
            traceback.print_exc()


async def verify_cleanup():
    """Verify that tables are empty."""
    print("\n" + "=" * 70)
    print("  Verification")
    print("=" * 70 + "\n")
    
    async with engine.connect() as conn:
        # ✅ FIXED: Correct table names
        tables_to_check = [
            "students",
            "authorities",
            "complaints",
            "complaint_votes",
            "complaint_status_history",
            "authority_updates",
            "student_notifications",
            "categories",
            "departments"
        ]
        
        all_empty = True
        
        for table_name in tables_to_check:
            try:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                status = "✅ EMPTY" if count == 0 else f"⚠️  HAS {count} ROWS"
                print(f"   {table_name:30} {status}")
                
                if count > 0:
                    all_empty = False
            except Exception as e:
                print(f"   {table_name:30} ❌ Error: {e}")
        
        print()
        if all_empty:
            print("✅ All tables are empty! Database is clean.")
        else:
            print("⚠️  Some tables still have data.")


async def recreate_seed_data():
    """Recreate essential seed data (departments and categories)."""
    print("\n" + "=" * 70)
    print("  Recreating Seed Data")
    print("=" * 70 + "\n")
    
    async with engine.begin() as conn:
        try:
            # Insert departments
            departments = [
                (1, 'Computer Science & Engineering', 'CSE'),
                (2, 'Electronics & Communication', 'ECE'),
                (3, 'Mechanical Engineering', 'MECH'),
                (4, 'Civil Engineering', 'CIVIL'),
                (5, 'Information Technology', 'IT'),
            ]
            
            for dept_id, name, code in departments:
                await conn.execute(text(
                    f"INSERT INTO departments (id, name, code, is_active) "
                    f"VALUES ({dept_id}, '{name}', '{code}', true) "
                    f"ON CONFLICT (id) DO NOTHING;"
                ))
            print("✅ Departments created")
            
            # ✅ FIXED: Insert into correct table name
            categories = [
                (1, 'Hostel', 'Hostel facilities, room issues, mess complaints'),
                (2, 'General', 'Canteen, library, playground, campus facilities'),
                (3, 'Department', 'Academic issues, lab facilities, classroom problems'),
                (4, 'Disciplinary Committee', 'Ragging, harassment, safety concerns'),
            ]
            
            for cat_id, name, desc in categories:
                # Escape single quotes in description
                desc_escaped = desc.replace("'", "''")
                await conn.execute(text(
                    f"INSERT INTO categories (id, name, description, is_active) "
                    f"VALUES ({cat_id}, '{name}', '{desc_escaped}', true) "
                    f"ON CONFLICT (id) DO NOTHING;"
                ))
            print("✅ Categories created")
            
            # Reset sequences
            await conn.execute(text("SELECT setval('departments_id_seq', (SELECT MAX(id) FROM departments));"))
            await conn.execute(text("SELECT setval('categories_id_seq', (SELECT MAX(id) FROM categories));"))
            print("✅ Sequences reset")
        
        except Exception as e:
            print(f"❌ Error recreating seed data: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main cleanup workflow."""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  CampusVoice Database Cleanup & Reset".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    try:
        # Step 1: Cleanup
        await cleanup_database()
        
        # Step 2: Verify
        await verify_cleanup()
        
        # Step 3: Recreate seed data
        print("\n💡 Would you like to recreate seed data (departments & categories)?")
        recreate = input("Type 'YES' to recreate seed data: ")
        
        if recreate == "YES":
            await recreate_seed_data()
            print("\n✅ Seed data recreated!")
        
        print("\n" + "=" * 70)
        print("  Cleanup Complete!")
        print("=" * 70)
        print("\n🚀 You can now run: python scripts/setup_database.py")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
