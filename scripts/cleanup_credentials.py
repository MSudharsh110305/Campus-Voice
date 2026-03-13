"""
One-off cleanup script: Deactivate stale authority accounts and reset passwords
for the canonical authority set.

Run: python scripts/cleanup_credentials.py
"""

import asyncio
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from src.database.connection import AsyncSessionLocal
from src.database.models import Authority
from src.services.auth_service import auth_service

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== STALE ACCOUNTS TO DEACTIVATE ====================

STALE_EMAILS = [
    "adminofficer@srec.ac.in",
    "discipline@srec.ac.in",
    "srdepwarden@srec.ac.in",
    "mdeputywarden1@srec.ac.in",
    "mdeputywarden2@srec.ac.in",
    "fdeputywarden1@srec.ac.in",
    "mwarden1@srec.ac.in",
    "mwarden2@srec.ac.in",
    "mwarden3@srec.ac.in",
    "fwarden1@srec.ac.in",
    "fwarden2@srec.ac.in",
]

# ==================== CANONICAL ACCOUNTS: email -> password ====================

CANONICAL_CREDENTIALS = {
    "admin@srec.ac.in":           "Admin@123456",
    "officer@srec.ac.in":         "Officer@1234",
    "dc@srec.ac.in":              "Discip@12345",
    "sdw@srec.ac.in":             "SeniorDW@123",
    "dw.mens@srec.ac.in":         "MensDW@1234",
    "warden1.mens@srec.ac.in":    "MensW1@1234",
    "warden2.mens@srec.ac.in":    "MensW2@1234",
    "dw.womens@srec.ac.in":       "WomensDW@123",
    "warden1.womens@srec.ac.in":  "WomensW1@123",
    "warden2.womens@srec.ac.in":  "WomensW2@123",
    "hod.cse@srec.ac.in":         "HodCSE@123",
    "hod.ece@srec.ac.in":         "HodECE@123",
    "hod.mech@srec.ac.in":        "HodMECH@123",
    "hod.civil@srec.ac.in":       "HodCIVIL@123",
    "hod.eee@srec.ac.in":         "HodEEE@123",
    "hod.it@srec.ac.in":          "HodIT@123",
    "hod.bio@srec.ac.in":         "HodBIO@123",
    "hod.aero@srec.ac.in":        "HodAERO@123",
    "hod.raa@srec.ac.in":         "HodRAA@123",
    "hod.eie@srec.ac.in":         "HodEIE@123",
    "hod.mba@srec.ac.in":         "HodMBA@123",
    "hod.aids@srec.ac.in":        "HodAIDS@123",
    "hod.mtechcse@srec.ac.in":    "HodMTECH_CSE@123",
}


async def main():
    print("=" * 70)
    print("CampusVoice — Credential Cleanup Script")
    print("=" * 70)
    print()

    async with AsyncSessionLocal() as session:
        # ------------------------------------------------------------------
        # STEP 1: Deactivate stale accounts
        # ------------------------------------------------------------------
        print("[1] Deactivating stale accounts...")
        deactivated = []
        not_found_stale = []

        for email in STALE_EMAILS:
            result = await session.execute(
                select(Authority).where(Authority.email == email)
            )
            authority = result.scalar_one_or_none()

            if authority is None:
                not_found_stale.append(email)
                print(f"    NOT FOUND (skipping): {email}")
                continue

            if authority.is_active:
                authority.is_active = False
                deactivated.append(email)
                print(f"    DEACTIVATED: {email}  (was active)")
            else:
                print(f"    already inactive: {email}")

        await session.commit()
        print(f"\n  => Deactivated {len(deactivated)} accounts.")
        if not_found_stale:
            print(f"  => {len(not_found_stale)} stale accounts not present in DB (no action needed).")

        print()

        # ------------------------------------------------------------------
        # STEP 2: Reset passwords for canonical accounts
        # ------------------------------------------------------------------
        print("[2] Resetting passwords for canonical accounts...")
        passwords_reset = []
        not_found_canonical = []

        for email, plain_password in CANONICAL_CREDENTIALS.items():
            result = await session.execute(
                select(Authority).where(Authority.email == email)
            )
            authority = result.scalar_one_or_none()

            if authority is None:
                not_found_canonical.append(email)
                print(f"    NOT FOUND (cannot reset): {email}")
                continue

            new_hash = auth_service.hash_password(plain_password)
            authority.password_hash = new_hash
            # Ensure canonical accounts are active
            if not authority.is_active:
                authority.is_active = True
                print(f"    RESET + REACTIVATED: {email}")
            else:
                print(f"    RESET: {email}")
            passwords_reset.append(email)

        await session.commit()
        print(f"\n  => Reset passwords for {len(passwords_reset)} canonical accounts.")
        if not_found_canonical:
            print(f"  => {len(not_found_canonical)} canonical accounts not found in DB:")
            for em in not_found_canonical:
                print(f"       {em}")
            print("     (These must be seeded first via setup_database.py)")

        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  Stale accounts deactivated : {len(deactivated)}")
        print(f"  Canonical passwords reset  : {len(passwords_reset)}")
        print(f"  Stale not in DB            : {len(not_found_stale)}")
        print(f"  Canonical not in DB        : {len(not_found_canonical)}")
        print()
        print("Cleanup complete.")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
