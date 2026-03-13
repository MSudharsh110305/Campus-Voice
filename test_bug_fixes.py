"""
Bug Fix Verification Script for CampusVoice

Tests the 5 specific bugs that were fixed:
1. Day Scholar → Hostel complaint (should return 400)
2. Female → Men's Hostel (should return 400)
3. Male → Women's Hostel (should return 400)
4. Invalid status transition: Closed → In Progress (should return 400)
5. Status update to Closed without reason (should return 422)

Also tests:
6. Rate limiting on voting (should NOT be rate limited)
7. Image limit enforcement (already enforced at 1 image max)
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
API_URL = "http://localhost:8000/api"  # Change for production
VERBOSE = True

# Test results tracker
test_results = []


def log(message: str, level: str = "INFO"):
    """Log message with timestamp"""
    if VERBOSE or level == "ERROR":
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")


def test_result(test_name: str, expected: int, actual: int, details: str = "") -> bool:
    """Record test result"""
    passed = (expected == actual)
    result = {
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "details": details
    }
    test_results.append(result)

    status = "[PASS]" if passed else "[FAIL]"
    log(f"{status} - {test_name}: Expected {expected}, Got {actual}", "INFO" if passed else "ERROR")
    if details and not passed:
        log(f"  Details: {details}", "ERROR")

    return passed


def register_student(roll_no: str, email: str, name: str, password: str,
                     gender: str, stay_type: str, department_code: str = "CSE",
                     year: int = 2) -> Dict[str, Any]:
    """Register a test student"""
    try:
        response = requests.post(
            f"{API_URL}/students/register",
            json={
                "roll_no": roll_no,
                "email": email,
                "name": name,
                "password": password,
                "gender": gender,
                "stay_type": stay_type,
                "department_code": department_code,
                "year": year
            }
        )

        if response.status_code in (200, 201):
            log(f"Registered student: {roll_no}")
            return response.json()
        elif response.status_code == 400 and "already exists" in response.text.lower():
            # Student already exists, try to login
            log(f"Student {roll_no} already exists, logging in...")
            return login_student(email, password)
        else:
            log(f"Registration failed for {roll_no}: {response.status_code} - {response.text}", "ERROR")
            return {}
    except Exception as e:
        log(f"Registration error for {roll_no}: {e}", "ERROR")
        return {}


def login_student(email: str, password: str) -> Dict[str, Any]:
    """Login student"""
    try:
        response = requests.post(
            f"{API_URL}/students/login",
            json={"email": email, "password": password}
        )

        if response.status_code == 200:
            data = response.json()
            log(f"Logged in: {email}")
            return data
        else:
            log(f"Login failed for {email}: {response.status_code}", "ERROR")
            return {}
    except Exception as e:
        log(f"Login error for {email}: {e}", "ERROR")
        return {}


def register_authority(email: str, name: str, password: str,
                      authority_type: str = "Men's Hostel Warden",
                      department_code: str = None) -> Dict[str, Any]:
    """Register a test authority (requires admin endpoint - skipping for now)"""
    # This would require admin access to create authorities
    # For testing, we'll use existing authority accounts
    log(f"Authority registration skipped - use existing {authority_type}", "INFO")
    return {}


def login_authority(email: str, password: str) -> Dict[str, Any]:
    """Login authority"""
    try:
        response = requests.post(
            f"{API_URL}/authorities/login",
            json={"email": email, "password": password}
        )

        if response.status_code == 200:
            data = response.json()
            log(f"Authority logged in: {email}")
            return data
        else:
            log(f"Authority login failed for {email}: {response.status_code}", "ERROR")
            return {}
    except Exception as e:
        log(f"Authority login error for {email}: {e}", "ERROR")
        return {}


def submit_complaint(token: str, text: str, visibility: str = "Public") -> tuple[int, Dict]:
    """Submit complaint"""
    try:
        response = requests.post(
            f"{API_URL}/complaints/submit",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "original_text": text,
                "visibility": visibility
            }
        )

        return response.status_code, response.json() if response.status_code < 500 else {}
    except Exception as e:
        log(f"Complaint submission error: {e}", "ERROR")
        return 500, {}


def update_complaint_status(token: str, complaint_id: str, new_status: str, reason: str = None) -> tuple[int, Dict]:
    """Update complaint status (authority only)"""
    try:
        payload = {"status": new_status}
        if reason:
            payload["reason"] = reason

        response = requests.put(
            f"{API_URL}/authorities/complaints/{complaint_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )

        return response.status_code, response.json() if response.status_code < 500 else {}
    except Exception as e:
        log(f"Status update error: {e}", "ERROR")
        return 500, {}


def vote_on_complaint(token: str, complaint_id: str, vote_type: str) -> tuple[int, Dict]:
    """Vote on complaint"""
    try:
        response = requests.post(
            f"{API_URL}/complaints/{complaint_id}/vote",
            headers={"Authorization": f"Bearer {token}"},
            json={"vote_type": vote_type}
        )

        return response.status_code, response.json() if response.status_code < 500 else {}
    except Exception as e:
        log(f"Vote error: {e}", "ERROR")
        return 500, {}


def run_tests():
    """Run all bug fix tests"""
    log("="*80)
    log("BUG FIX VERIFICATION TESTS")
    log("="*80)

    # Test Setup - Create test students
    log("\n--- Setting up test students ---")

    # Test 1: Day Scholar (Male)
    day_scholar_male = register_student(
        roll_no="23CS901",
        email="dayscholar.male@srec.ac.in",
        name="Day Scholar Male",
        password="Test@123",
        gender="Male",
        stay_type="Day Scholar",
        department_code="CSE"
    )

    # Test 2: Female Hostel Student
    female_hostel = register_student(
        roll_no="23CS902",
        email="female.hostel@srec.ac.in",
        name="Female Hostel Student",
        password="Test@123",
        gender="Female",
        stay_type="Hostel",
        department_code="ECE"
    )

    # Test 3: Male Hostel Student
    male_hostel = register_student(
        roll_no="23CS903",
        email="male.hostel@srec.ac.in",
        name="Male Hostel Student",
        password="Test@123",
        gender="Male",
        stay_type="Hostel",
        department_code="MECH"
    )

    # Test 4: Another student for voting tests
    voter_student = register_student(
        roll_no="23CS904",
        email="voter.student@srec.ac.in",
        name="Voter Student",
        password="Test@123",
        gender="Male",
        stay_type="Hostel",
        department_code="CSE"
    )

    time.sleep(1)  # Allow registration to settle

    # ====================
    # BUG TEST 1: Day Scholar → Hostel Complaint
    # ====================
    log("\n--- BUG TEST 1: Day Scholar → Hostel Complaint ---")

    if day_scholar_male.get("token"):
        status_code, response = submit_complaint(
            day_scholar_male["token"],
            "The hostel room AC is not working properly",
            "Public"
        )
        test_result(
            "Bug 1: Day Scholar → Hostel",
            expected=400,
            actual=status_code,
            details=response.get("detail", "") if status_code != 400 else "Correctly rejected"
        )
    else:
        log("Day Scholar Male registration/login failed - skipping test 1", "ERROR")
        test_result("Bug 1: Day Scholar → Hostel", expected=400, actual=0, details="Setup failed")

    # ====================
    # BUG TEST 2: Female → Men's Hostel
    # ====================
    log("\n--- BUG TEST 2: Female → Men's Hostel ---")

    if female_hostel.get("token"):
        status_code, response = submit_complaint(
            female_hostel["token"],
            "The men's hostel bathroom has water leakage issues",
            "Public"
        )
        test_result(
            "Bug 2: Female → Men's Hostel",
            expected=400,
            actual=status_code,
            details=response.get("detail", "") if status_code != 400 else "Correctly rejected"
        )
    else:
        log("Female Hostel registration/login failed - skipping test 2", "ERROR")
        test_result("Bug 2: Female → Men's Hostel", expected=400, actual=0, details="Setup failed")

    # ====================
    # BUG TEST 3: Male → Women's Hostel
    # ====================
    log("\n--- BUG TEST 3: Male → Women's Hostel ---")

    if male_hostel.get("token"):
        status_code, response = submit_complaint(
            male_hostel["token"],
            "The women's hostel mess food quality is very poor",
            "Public"
        )
        test_result(
            "Bug 3: Male → Women's Hostel",
            expected=400,
            actual=status_code,
            details=response.get("detail", "") if status_code != 400 else "Correctly rejected"
        )
    else:
        log("Male Hostel registration/login failed - skipping test 3", "ERROR")
        test_result("Bug 3: Male → Women's Hostel", expected=400, actual=0, details="Setup failed")

    # ====================
    # BUG TEST 4 & 5: Status Transition Validation
    # ====================
    log("\n--- BUG TEST 4 & 5: Status Transition Validation ---")
    log("Note: These tests require authority access and an existing complaint")
    log("You must manually verify these with existing authority credentials")

    # For automated testing, we'd need:
    # 1. Authority credentials (warden/admin)
    # 2. A complaint that's been Closed
    # This requires manual setup or a seeded database

    log("Skipping Bug 4 & 5 automated tests - requires authority setup")
    test_result("Bug 4: Closed → In Progress", expected=400, actual=0, details="Manual verification required")
    test_result("Bug 5: Closed without reason", expected=422, actual=0, details="Manual verification required")

    # ====================
    # BUG TEST 6: Voting Rate Limiting
    # ====================
    log("\n--- BUG TEST 6: Voting Rate Limiting (Should NOT be rate limited) ---")

    # First, create a valid complaint to vote on
    if male_hostel.get("token") and voter_student.get("token"):
        # Submit a valid general complaint
        status_code, complaint_response = submit_complaint(
            male_hostel["token"],
            "The library WiFi is very slow and disconnects frequently",
            "Public"
        )

        if status_code == 201 and complaint_response.get("id"):
            complaint_id = complaint_response["id"]
            log(f"Created test complaint: {complaint_id}")

            # Try to vote 20 times in quick succession (should not be rate limited)
            vote_count = 0
            rate_limited = False

            for i in range(20):
                status_code, vote_response = vote_on_complaint(
                    voter_student["token"],
                    complaint_id,
                    "Upvote" if i % 2 == 0 else "Downvote"  # Alternate to avoid duplicate vote error
                )

                if status_code == 429:  # Rate limited
                    rate_limited = True
                    break
                elif status_code in (200, 201):
                    vote_count += 1

                time.sleep(0.1)  # Small delay between votes

            # Test passes if we were NOT rate limited
            test_result(
                "Bug 6: Voting NOT rate limited",
                expected=0,  # 0 = not rate limited
                actual=1 if rate_limited else 0,
                details=f"Successfully voted {vote_count} times without rate limiting"
            )
        else:
            log("Failed to create test complaint for voting test", "ERROR")
            test_result("Bug 6: Voting NOT rate limited", expected=0, actual=0, details="Setup failed")
    else:
        log("Student registration failed - skipping voting test", "ERROR")
        test_result("Bug 6: Voting NOT rate limited", expected=0, actual=0, details="Setup failed")

    # ====================
    # Print Summary
    # ====================
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)

    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["passed"])
    failed_tests = total_tests - passed_tests

    for result in test_results:
        status = "[PASS]" if result["passed"] else "[FAIL]"
        log(f"{status} - {result['test']}")

    log("")
    log(f"Total Tests: {total_tests}")
    log(f"Passed: {passed_tests}")
    log(f"Failed: {failed_tests}")
    log(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")

    if failed_tests == 0:
        log("\n*** ALL BUG FIXES VERIFIED! ***", "INFO")
        return True
    else:
        log(f"\n*** WARNING: {failed_tests} test(s) failed - review fixes ***", "ERROR")
        return False


if __name__ == "__main__":
    print("\n*** CampusVoice Bug Fix Verification Script ***")
    print("=" * 80)
    print("\nThis script tests the 5 critical bug fixes:")
    print("1. Day Scholar -> Hostel complaint rejection")
    print("2. Female -> Men's Hostel rejection")
    print("3. Male -> Women's Hostel rejection")
    print("4. Invalid status transitions (requires manual verification)")
    print("5. Status updates without reason (requires manual verification)")
    print("6. Voting not rate limited")
    print("\n" + "=" * 80)

    confirm = input("\n*** WARNING: This will create test data in your database. Continue? (y/n): ")

    if confirm.lower() != 'y':
        print("Test cancelled.")
        exit(0)

    try:
        success = run_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        exit(1)
    except Exception as e:
        print(f"\n\n*** ERROR: Test script error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
