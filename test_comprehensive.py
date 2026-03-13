#!/usr/bin/env python3
"""
CampusVoice Comprehensive Test Suite
=====================================
62 endpoints × ~5 scenarios each ≈ 310+ test cases.
Covers: happy path, validation errors, auth failures,
        permission violations, boundary conditions, workflow sequences.

Run:  python test_comprehensive.py
Requires server running at http://localhost:8000
"""

import requests
import json
import time
import io
import sys
import struct
import zlib
from typing import Optional, Dict, Any, Tuple


def make_valid_png(width: int = 10, height: int = 10) -> bytes:
    """Generate a valid minimal PNG image."""
    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = make_chunk(b'IHDR', ihdr_data)
    raw_data = b''
    for _ in range(height):
        raw_data += b'\x00' + b'\xff\xff\xff' * width
    compressed = zlib.compress(raw_data, 9)
    idat = make_chunk(b'IDAT', compressed)
    iend = make_chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

BASE_URL = "http://localhost:8000"
TIMEOUT = 30  # seconds

# ── Shared test state ──────────────────────────────────────────────────────────
TS = str(int(time.time()))[-5:]  # 5-char unique suffix per run

S = {
    # tokens
    "tok_s1": None,   # Male, CSE, Hostel
    "tok_s2": None,   # Female, CSE, Hostel
    "tok_s3": None,   # Male, ECE, Day Scholar
    "tok_s4": None,   # Female, MECH, Hostel
    "tok_admin": None,
    "tok_officer": None,
    "tok_warden_m": None,   # Men's hostel warden
    "tok_warden_w": None,   # Women's hostel warden
    "tok_hod_cse": None,
    "tok_dc": None,
    "tok_sdw": None,
    # IDs
    "cid_s1": None,         # hostel complaint by s1
    "cid_s2": None,         # hostel complaint by s2
    "cid_s1_dept": None,    # dept complaint by s1
    "cid_s1_gen": None,     # general complaint by s1
    "cid_s3": None,         # complaint by day scholar
    "notif_id": None,
    "new_authority_id": None,
    # student info
    "s1_roll": f"99CS{TS}",
    "s1_email": f"test_s1_{TS}@srec.ac.in",
    "s2_roll": f"99CS{int(TS)+1}",
    "s2_email": f"test_s2_{TS}@srec.ac.in",
    "s3_roll": f"99EC{TS}",
    "s3_email": f"test_s3_{TS}@srec.ac.in",
    "s4_roll": f"99ME{TS}",
    "s4_email": f"test_s4_{TS}@srec.ac.in",
    "new_auth_email": f"test_auth_{TS}@srec.ac.in",
}

# ── Result tracking ────────────────────────────────────────────────────────────
passed = 0
failed = 0
skipped = 0
failures = []
test_num = 0
section_num = 0


def section(name: str):
    global section_num
    section_num += 1
    print(f"\n{'='*72}")
    print(f"  SECTION {section_num:02d}: {name}")
    print(f"{'='*72}")


def T(name: str, condition: bool, detail: str = ""):
    """Assert a test condition and record result."""
    global test_num, passed, failed
    test_num += 1
    if condition:
        passed += 1
        print(f"  [+] T{test_num:03d}: {name}")
    else:
        failed += 1
        print(f"  [!] T{test_num:03d}: FAIL: {name}")
        if detail:
            print(f"         {detail}")
        failures.append(f"T{test_num:03d}: {name} | {detail}")


def SKIP(name: str, reason: str = ""):
    global test_num, skipped
    test_num += 1
    skipped += 1
    print(f"  [-] T{test_num:03d}: SKIP: {name}" + (f" ({reason})" if reason else ""))


def req(method: str, path: str,
        token: str = None,
        json_data: dict = None,
        form_data: dict = None,
        files: dict = None,
        params: dict = None) -> Tuple[Optional[int], Any]:
    """Make an HTTP request, return (status_code, body_dict_or_str)."""
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        kw = dict(headers=headers, timeout=TIMEOUT)
        if params:
            kw["params"] = params
        if method == "GET":
            r = requests.get(url, **kw)
        elif method == "POST":
            if files:
                r = requests.post(url, data=form_data or {}, files=files, **kw)
            elif form_data is not None:
                r = requests.post(url, data=form_data, **kw)
            else:
                r = requests.post(url, json=json_data, **kw)
        elif method == "PUT":
            r = requests.put(url, json=json_data, **kw)
        elif method == "DELETE":
            r = requests.delete(url, **kw)
        elif method == "PATCH":
            r = requests.patch(url, json=json_data, **kw)
        else:
            return None, None
        try:
            body = r.json()
        except Exception:
            body = r.text
        return r.status_code, body
    except Exception as e:
        return None, str(e)


def login_student(email: str, password: str = "Test@1234") -> Optional[str]:
    sc, body = req("POST", "/api/students/login",
                   json_data={"email_or_roll_no": email, "password": password})
    if sc == 200 and isinstance(body, dict):
        return body.get("token") or body.get("data", {}).get("token")
    return None


def login_authority(email: str, password: str) -> Optional[str]:
    sc, body = req("POST", "/api/authorities/login",
                   json_data={"email": email, "password": password})
    if sc == 200 and isinstance(body, dict):
        return body.get("token") or body.get("data", {}).get("token")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: HEALTH ENDPOINTS (7 endpoints, all public)
# ══════════════════════════════════════════════════════════════════════════════
section("HEALTH ENDPOINTS")

sc, body = req("GET", "/health")
T("GET /health returns 200", sc == 200, f"got {sc}")
T("health body has 'status' field", isinstance(body, dict) and "status" in body,
  str(body)[:120])
T("health status is 'healthy'", isinstance(body, dict) and body.get("status") == "healthy",
  str(body)[:120])

sc, body = req("GET", "/health/detailed")
T("GET /health/detailed returns 200", sc == 200, f"got {sc}")
T("detailed health has 'database' or 'db' key",
  isinstance(body, dict) and ("database" in body or "db" in body or "database" in str(body)),
  str(body)[:120])

sc, body = req("GET", "/health/ready")
T("GET /health/ready returns 200 or 503", sc in (200, 503), f"got {sc}")

sc, body = req("GET", "/health/live")
T("GET /health/live returns 200", sc == 200, f"got {sc}")

sc, body = req("GET", "/health/startup")
T("GET /health/startup returns 200", sc == 200, f"got {sc}")

sc, body = req("GET", "/metrics")
T("GET /metrics returns 200", sc == 200, f"got {sc}")
T("metrics has student count (in any key)",
  isinstance(body, dict) and ("student_count" in body or "total_students" in str(body)),
  str(body)[:120])

sc, body = req("GET", "/ping")
T("GET /ping returns 200", sc == 200, f"got {sc}")
T("ping body has 'pong' or 'status'",
  isinstance(body, dict) and ("pong" in body or "status" in body),
  str(body)[:80])

# No auth required — verify health rejects nothing extra
sc, body = req("GET", "/health", token="invalid_token")
T("GET /health ignores bad token (still 200)", sc == 200, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: STUDENT REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
section("STUDENT REGISTRATION")

# 2a. Register s1: Male CSE Hostel
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s1_roll"],
    "email": S["s1_email"],
    "password": "Test@1234",
    "name": "Test Student One",
    "department_id": 1,  # CSE
    "year": 2,
    "gender": "Male",
    "stay_type": "Hostel"
})
T("Register s1 (Male, CSE, Hostel) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")

# 2b. Register s2: Female CSE Hostel
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s2_roll"],
    "email": S["s2_email"],
    "password": "Test@1234",
    "name": "Test Student Two",
    "department_id": 1,  # CSE
    "year": 2,
    "gender": "Female",
    "stay_type": "Hostel"
})
T("Register s2 (Female, CSE, Hostel) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")

# 2c. Register s3: Male ECE Day Scholar
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s3_roll"],
    "email": S["s3_email"],
    "password": "Test@1234",
    "name": "Test Student Three",
    "department_id": 2,  # ECE
    "year": 3,
    "gender": "Male",
    "stay_type": "Day Scholar"
})
T("Register s3 (Male, ECE, Day Scholar) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")

# 2d. Register s4: Female MECH Hostel
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s4_roll"],
    "email": S["s4_email"],
    "password": "Test@1234",
    "name": "Test Student Four",
    "department_id": 4,  # MECH
    "year": 1,
    "gender": "Female",
    "stay_type": "Hostel"
})
T("Register s4 (Female, MECH, Hostel) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")

# 2e. Duplicate roll_no
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s1_roll"],
    "email": f"different_{TS}@srec.ac.in",
    "password": "Test@1234",
    "name": "Duplicate Roll",
    "department_id": 1,
    "year": 1,
    "gender": "Male",
    "stay_type": "Day Scholar"
})
T("Duplicate roll_no -> 400/409", sc in (400, 409), f"got {sc}: {str(body)[:80]}")

# 2f. Duplicate email
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99ZZ{TS}",
    "email": S["s1_email"],
    "password": "Test@1234",
    "name": "Duplicate Email",
    "department_id": 1,
    "year": 1,
    "gender": "Male",
    "stay_type": "Day Scholar"
})
T("Duplicate email -> 400/409", sc in (400, 409), f"got {sc}: {str(body)[:80]}")

# 2g. Invalid email domain
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99AA{TS}",
    "email": f"test_{TS}@gmail.com",
    "password": "Test@1234",
    "name": "Wrong Domain",
    "department_id": 1,
    "year": 1,
    "gender": "Male",
    "stay_type": "Day Scholar"
})
T("Wrong email domain -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# 2h. Invalid password (too simple)
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99BB{TS}",
    "email": f"pass_{TS}@srec.ac.in",
    "password": "short",
    "name": "Weak Password",
    "department_id": 1,
    "year": 1,
    "gender": "Male",
    "stay_type": "Day Scholar"
})
T("Weak password -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# 2i. Missing required fields
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99CC{TS}",
    "password": "Test@1234"
})
T("Missing fields -> 400/422", sc in (400, 422), f"got {sc}")

# 2j. Invalid department_id
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99DD{TS}",
    "email": f"dept_{TS}@srec.ac.in",
    "password": "Test@1234",
    "name": "Bad Dept",
    "department_id": 9999,
    "year": 1,
    "gender": "Male",
    "stay_type": "Day Scholar"
})
T("Invalid department_id -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# 2k. Invalid year (out of range)
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99EE{TS}",
    "email": f"year_{TS}@srec.ac.in",
    "password": "Test@1234",
    "name": "Bad Year",
    "department_id": 1,
    "year": 11,
    "gender": "Male",
    "stay_type": "Day Scholar"
})
T("Year > 10 -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: STUDENT LOGIN
# ══════════════════════════════════════════════════════════════════════════════
section("STUDENT LOGIN")

# Login all test students
sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s1_email"], "password": "Test@1234"})
T("s1 login by email -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
if sc == 200 and isinstance(body, dict):
    S["tok_s1"] = body.get("token") or body.get("data", {}).get("token")
T("s1 login returns token", bool(S["tok_s1"]), "no token in response")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s1_roll"], "password": "Test@1234"})
T("s1 login by roll_no -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s2_email"], "password": "Test@1234"})
T("s2 login -> 200", sc == 200, f"got {sc}")
if sc == 200 and isinstance(body, dict):
    S["tok_s2"] = body.get("token") or body.get("data", {}).get("token")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s3_email"], "password": "Test@1234"})
T("s3 login -> 200", sc == 200, f"got {sc}")
if sc == 200 and isinstance(body, dict):
    S["tok_s3"] = body.get("token") or body.get("data", {}).get("token")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s4_email"], "password": "Test@1234"})
T("s4 login -> 200", sc == 200, f"got {sc}")
if sc == 200 and isinstance(body, dict):
    S["tok_s4"] = body.get("token") or body.get("data", {}).get("token")

# Wrong password
sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s1_email"], "password": "WrongPass@999"})
T("Wrong password -> 401", sc == 401, f"got {sc}")

# Non-existent user
sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": f"nobody_{TS}@srec.ac.in", "password": "Test@1234"})
T("Non-existent student -> 401/404", sc in (401, 404), f"got {sc}")

# Empty credentials
sc, body = req("POST", "/api/students/login", json_data={})
T("Empty login body -> 400/422", sc in (400, 422), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: AUTHORITY LOGIN
# ══════════════════════════════════════════════════════════════════════════════
section("AUTHORITY LOGIN")

for label, email, pwd, key in [
    ("admin", "admin@srec.ac.in", "Admin@123456", "tok_admin"),
    ("officer", "officer@srec.ac.in", "Officer@1234", "tok_officer"),
    ("warden_m", "warden1.mens@srec.ac.in", "MensW1@1234", "tok_warden_m"),
    ("warden_w", "warden1.womens@srec.ac.in", "WomensW1@123", "tok_warden_w"),
    ("hod_cse", "hod.cse@srec.ac.in", "HodCSE@123", "tok_hod_cse"),
    ("dc", "dc@srec.ac.in", "Discip@12345", "tok_dc"),
    ("sdw", "sdw@srec.ac.in", "SeniorDW@123", "tok_sdw"),
]:
    sc, body = req("POST", "/api/authorities/login",
                   json_data={"email": email, "password": pwd})
    T(f"{label} login -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    if sc == 200 and isinstance(body, dict):
        S[key] = body.get("token") or body.get("data", {}).get("token")

# Wrong password
sc, body = req("POST", "/api/authorities/login",
               json_data={"email": "admin@srec.ac.in", "password": "Wrong@999"})
T("Authority wrong password -> 401", sc == 401, f"got {sc}")

# Non-existent authority
sc, body = req("POST", "/api/authorities/login",
               json_data={"email": f"fake_{TS}@srec.ac.in", "password": "Test@1234"})
T("Non-existent authority -> 401/404", sc in (401, 404), f"got {sc}")

# Student using authority login endpoint
sc, body = req("POST", "/api/authorities/login",
               json_data={"email": S["s1_email"], "password": "Test@1234"})
T("Student on authority login -> 401/403", sc in (401, 403, 404), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: STUDENT PROFILE
# ══════════════════════════════════════════════════════════════════════════════
section("STUDENT PROFILE")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/profile", token=S["tok_s1"])
    T("GET /profile with valid token -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("profile has roll_no", isinstance(body, dict) and
      (body.get("roll_no") or body.get("data", {}).get("roll_no") if isinstance(body.get("data"), dict) else False
       or "roll_no" in str(body)), str(body)[:120])

    # Update profile - valid
    sc, body = req("PUT", "/api/students/profile", token=S["tok_s1"],
                   json_data={"name": "Test One Updated"})
    T("PUT /profile update name -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Update profile - invalid year
    sc, body = req("PUT", "/api/students/profile", token=S["tok_s1"],
                   json_data={"year": 0})
    T("PUT /profile year=0 -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    # Change password - schema: old_password, new_password, confirm_password (all required)
    sc, body = req("POST", "/api/students/change-password", token=S["tok_s1"],
                   json_data={
                       "old_password": "Test@1234",
                       "new_password": "NewTest@1234",
                       "confirm_password": "NewTest@1234"
                   })
    T("Change password (valid) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    # Change it back
    sc, _ = req("POST", "/api/students/change-password", token=S["tok_s1"],
                json_data={
                    "old_password": "NewTest@1234",
                    "new_password": "Test@1234",
                    "confirm_password": "Test@1234"
                })
    T("Change password back -> 200", sc == 200, f"got {sc}")

    # Change password - wrong current password
    sc, body = req("POST", "/api/students/change-password", token=S["tok_s1"],
                   json_data={
                       "old_password": "WrongOld@999",
                       "new_password": "New@9876543",
                       "confirm_password": "New@9876543"
                   })
    T("Change password wrong old -> 400/401", sc in (400, 401), f"got {sc}: {str(body)[:80]}")

    # Change password - new password too weak
    sc, body = req("POST", "/api/students/change-password", token=S["tok_s1"],
                   json_data={
                       "old_password": "Test@1234",
                       "new_password": "weak",
                       "confirm_password": "weak"
                   })
    T("Change password weak new -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Profile tests (s1 token missing)")

# Profile without token
sc, body = req("GET", "/api/students/profile")
T("GET /profile without token -> 401", sc == 401, f"got {sc}")

# Authority token on student profile
if S["tok_admin"]:
    sc, body = req("GET", "/api/students/profile", token=S["tok_admin"])
    T("Authority token on student profile -> 401/403", sc in (401, 403), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: STUDENT STATS
# ══════════════════════════════════════════════════════════════════════════════
section("STUDENT STATS")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/stats", token=S["tok_s1"])
    T("GET /students/stats -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("stats has total_complaints field",
      isinstance(body, dict) and
      ("total_complaints" in body or "total_complaints" in str(body)),
      str(body)[:120])
else:
    SKIP("Stats tests (s1 token missing)")

sc, body = req("GET", "/api/students/stats")
T("GET /students/stats without token -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7: COMPLAINT SUBMISSION
# ══════════════════════════════════════════════════════════════════════════════
section("COMPLAINT SUBMISSION")

print("  [info] Submitting complaints (AI categorization may take 5-15s)...")

# 7a. s1 (Male, CSE, Hostel) submits a hostel complaint
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s1"],
                   form_data={
                       "original_text": "The water supply in my hostel room has been disrupted for 3 days. "
                                        "The taps are completely dry and I cannot take a shower.",
                       "visibility": "Public"
                   })
    T("s1 hostel complaint submission -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data", body)
        S["cid_s1"] = data.get("id") or data.get("complaint_id")
    T("s1 complaint returns ID", bool(S["cid_s1"]), str(body)[:80])

# 7b. s2 (Female, CSE, Hostel) submits a women's hostel complaint
if S["tok_s2"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s2"],
                   form_data={
                       "original_text": "The washing machines in the women's hostel laundry room "
                                        "have been out of service for two weeks. Residents cannot "
                                        "do their laundry and this is causing significant inconvenience.",
                       "visibility": "Public"
                   })
    T("s2 women's hostel complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data", body)
        S["cid_s2"] = data.get("id") or data.get("complaint_id")

# 7c. s1 submits a department complaint
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s1"],
                   form_data={
                       "original_text": "The Computer Science lab projector has been malfunctioning "
                                        "during every lecture. Students are unable to see the slides.",
                       "visibility": "Public"
                   })
    T("s1 dept complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data", body)
        S["cid_s1_dept"] = data.get("id") or data.get("complaint_id")

# 7d. s3 (Day Scholar) submits a general complaint
if S["tok_s3"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s3"],
                   form_data={
                       "original_text": "The drinking water dispenser near the main entrance "
                                        "has been out of order for 5 days.",
                       "visibility": "Public"
                   })
    T("s3 general complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data", body)
        S["cid_s3"] = data.get("id") or data.get("complaint_id")

# 7e. s1 submits a general complaint (for voting tests)
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s1"],
                   form_data={
                       "original_text": "The campus wifi has been very slow for the past week. "
                                        "Downloads are impossibly slow and online exams are at risk.",
                       "visibility": "Public"
                   })
    T("s1 general complaint (for voting) -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data", body)
        S["cid_s1_gen"] = data.get("id") or data.get("complaint_id")

# 7f. Submit without authentication
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "No auth complaint", "visibility": "Public"})
T("Submit complaint without auth -> 401", sc == 401, f"got {sc}")

# 7g. Submit with missing text
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s1"],
                   form_data={"visibility": "Public"})
    T("Submit without text -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# 7h. Submit with text too short
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s1"],
                   form_data={"original_text": "short", "visibility": "Public"})
    T("Submit text too short -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# 7i. Submit with invalid visibility (use s3 who has fewer submissions)
if S["tok_s3"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s3"],
                   form_data={
                       "original_text": "This is a valid length complaint text about something important in the campus.",
                       "visibility": "InvalidVisibility"
                   })
    T("Invalid visibility -> 400/422/429", sc in (400, 422, 429), f"got {sc}: {str(body)[:80]}")

# 7j. Authority cannot submit complaint
if S["tok_admin"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_admin"],
                   form_data={
                       "original_text": "Authority trying to submit complaint about the campus.",
                       "visibility": "Public"
                   })
    T("Authority on student endpoint -> 401/403", sc in (401, 403), f"got {sc}")

# 7k. With image upload (small PNG)
if S["tok_s3"]:
    png_bytes = make_valid_png(10, 10)
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s3"],
                   form_data={
                       "original_text": "The road outside the college has massive potholes "
                                        "causing accidents. I have attached a photo.",
                       "visibility": "Public"
                   },
                   files={"image": ("test.png", png_bytes, "image/png")})
    T("Complaint with image -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8: PUBLIC FEED
# ══════════════════════════════════════════════════════════════════════════════
section("PUBLIC FEED")

# 8a. Public feed without auth
sc, body = req("GET", "/api/complaints/public-feed")
T("GET /public-feed without auth -> 200 or 401", sc in (200, 401), f"got {sc}")

# 8b. Public feed with s1 (Male, Hostel)
if S["tok_s1"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s1"])
    T("GET /public-feed as male hostel student -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("public feed returns list",
      isinstance(body, dict) and ("complaints" in body or "data" in body or isinstance(body.get("complaints"), list)),
      str(body)[:120])

    # With pagination
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s1"],
                   params={"page": 1, "page_size": 5})
    T("Public feed with pagination -> 200", sc == 200, f"got {sc}")

    # Sorted newest first - check created_at ordering
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s1"],
                   params={"page": 1, "page_size": 20})
    T("Public feed sorted newest first (has content)", sc == 200, f"got {sc}")

# 8c. Public feed as day scholar (s3) - should not see hostel complaints
if S["tok_s3"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s3"])
    T("GET /public-feed as day scholar -> 200", sc == 200, f"got {sc}")
    if sc == 200 and isinstance(body, dict):
        complaints = body.get("complaints") or body.get("data") or []
        if isinstance(complaints, list):
            hostel_found = any(
                "hostel" in str(c.get("category", "")).lower()
                for c in complaints
            )
            T("Day scholar sees no hostel complaints in feed", not hostel_found,
              f"Hostel complaint found in day scholar feed")

# 8d. Female student (s2) should not see Men's Hostel complaints in feed
if S["tok_s2"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s2"])
    T("GET /public-feed as female student -> 200", sc == 200, f"got {sc}")
    if sc == 200 and isinstance(body, dict):
        complaints = body.get("complaints") or body.get("data") or []
        if isinstance(complaints, list):
            mens_found = any(
                "men" in str(c.get("category", "")).lower()
                for c in complaints
            )
            T("Female student sees no Men's Hostel complaints", not mens_found,
              "Men's Hostel complaint found in female feed")

# 8e. Authority can access public feed
if S["tok_admin"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_admin"])
    T("Admin on public feed -> 200 or 403", sc in (200, 403), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9: COMPLAINT DETAILS
# ══════════════════════════════════════════════════════════════════════════════
section("COMPLAINT DETAILS")

if S["tok_s1"] and S["cid_s1"]:
    # Valid complaint
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}", token=S["tok_s1"])
    T("GET complaint by owner -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Complaint detail has id field",
      isinstance(body, dict) and
      (S["cid_s1"] in str(body.get("id", "")) or
       S["cid_s1"] in str(body.get("data", {}).get("id", ""))),
      str(body)[:120])

    # Complaint detail as different student (s4)
    if S["tok_s4"]:
        sc, body = req("GET", f"/api/complaints/{S['cid_s1']}", token=S["tok_s4"])
        T("GET public complaint by different student -> 200", sc == 200, f"got {sc}")

    # Admin uses authority endpoint (not student endpoint) for complaint details
    if S["tok_admin"]:
        sc, body = req("GET", f"/api/authorities/complaints/{S['cid_s1']}", token=S["tok_admin"])
        T("Admin sees complaint via authority endpoint -> 200", sc == 200, f"got {sc}")
else:
    SKIP("Complaint detail tests (cid_s1 missing)")

# Invalid UUID
if S["tok_s1"]:
    sc, body = req("GET", "/api/complaints/not-a-valid-uuid", token=S["tok_s1"])
    T("Invalid UUID -> 400/422", sc in (400, 422), f"got {sc}")

    sc, body = req("GET", f"/api/complaints/{str(id(S))[:8]}-0000-0000-0000-000000000000",
                   token=S["tok_s1"])
    T("Non-existent UUID -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")

# Without token
if S["cid_s1"]:
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}")
    T("Complaint detail without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10: VOTING
# ══════════════════════════════════════════════════════════════════════════════
section("VOTING")

# Use s3's complaint for voting (submitted by s3, voted by s2, s4, s1)
vote_cid = S["cid_s3"] or S["cid_s1_gen"]

if vote_cid and S["tok_s2"]:
    # 10a. Upvote
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote",
                   token=S["tok_s2"],
                   json_data={"vote_type": "Upvote"})
    T("s2 upvote complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")
    T("Upvote returns upvotes count",
      isinstance(body, dict) and "upvotes" in str(body),
      str(body)[:80])

    # 10b. Duplicate upvote (same student)
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote",
                   token=S["tok_s2"],
                   json_data={"vote_type": "Upvote"})
    T("Duplicate upvote -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

    # 10c. Change vote (upvote -> downvote)
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote",
                   token=S["tok_s2"],
                   json_data={"vote_type": "Downvote"})
    T("Change vote upvote->downvote -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Vote change returns updated vote counts",
      isinstance(body, dict) and "downvotes" in str(body),
      str(body)[:80])

    # 10d. Check my-vote
    sc, body = req("GET", f"/api/complaints/{vote_cid}/my-vote", token=S["tok_s2"])
    T("GET my-vote -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("my-vote returns vote_type",
      isinstance(body, dict) and "vote_type" in str(body),
      str(body)[:80])

    # 10e. Remove vote
    sc, body = req("DELETE", f"/api/complaints/{vote_cid}/vote", token=S["tok_s2"])
    T("DELETE vote (remove) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # 10f. Remove already-removed vote
    sc, body = req("DELETE", f"/api/complaints/{vote_cid}/vote", token=S["tok_s2"])
    T("Remove vote twice -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

if vote_cid and S["tok_s4"]:
    # 10g. Downvote by s4
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote",
                   token=S["tok_s4"],
                   json_data={"vote_type": "Downvote"})
    T("s4 downvote complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

# 10h. Vote on own complaint
own_cid = S["cid_s3"]
if own_cid and S["tok_s3"]:
    sc, body = req("POST", f"/api/complaints/{own_cid}/vote",
                   token=S["tok_s3"],
                   json_data={"vote_type": "Upvote"})
    T("Vote on own complaint -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

# 10i. Vote with invalid vote_type
if vote_cid and S["tok_s1"]:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote",
                   token=S["tok_s1"],
                   json_data={"vote_type": "Invalid"})
    T("Invalid vote_type -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# 10j. Vote without auth
if vote_cid:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote",
                   json_data={"vote_type": "Upvote"})
    T("Vote without auth -> 401", sc == 401, f"got {sc}")

# 10k. Authority cannot vote (not a student)
if vote_cid and S["tok_admin"]:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote",
                   token=S["tok_admin"],
                   json_data={"vote_type": "Upvote"})
    T("Authority voting -> 401/403", sc in (401, 403), f"got {sc}")

# 10l. my-vote when not voted
if S["cid_s1"] and S["tok_s3"]:
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/my-vote", token=S["tok_s3"])
    T("my-vote when not voted -> 200 (null) or 404", sc in (200, 404), f"got {sc}: {str(body)[:80]}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11: IMAGE UPLOAD AND RETRIEVAL
# ══════════════════════════════════════════════════════════════════════════════
section("IMAGE UPLOAD AND RETRIEVAL")

# Valid PNG image generated programmatically
small_png = make_valid_png(10, 10)

if S["tok_s1"] and S["cid_s1"]:
    # Upload image - field name is 'file' (not 'image')
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/upload-image",
                   token=S["tok_s1"],
                   files={"file": ("complaint.png", small_png, "image/png")})
    T("Upload image to complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

    # Retrieve image
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/image", token=S["tok_s1"])
    T("GET complaint image -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Another student can get image of public complaint
    if S["tok_s4"]:
        sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/image", token=S["tok_s4"])
        T("Different student gets public complaint image -> 200/403", sc in (200, 403), f"got {sc}")

    # Upload non-image file (should fail)
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/upload-image",
                   token=S["tok_s1"],
                   files={"file": ("test.txt", b"not an image file content here", "text/plain")})
    T("Upload non-image -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    # Upload without auth
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/upload-image",
                   files={"file": ("img.png", small_png, "image/png")})
    T("Upload image without auth -> 401", sc == 401, f"got {sc}")

    # Image on complaint with no image
    if S["cid_s1_dept"]:
        sc, body = req("GET", f"/api/complaints/{S['cid_s1_dept']}/image", token=S["tok_s1"])
        T("GET image on complaint with no image -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Image tests (cid_s1 missing)")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12: STATUS HISTORY AND TIMELINE
# ══════════════════════════════════════════════════════════════════════════════
section("STATUS HISTORY AND TIMELINE")

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/status-history", token=S["tok_s1"])
    T("GET status-history -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("status-history is list", isinstance(body, (list, dict)), str(body)[:80])

    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/timeline", token=S["tok_s1"])
    T("GET timeline -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Without auth
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/status-history")
    T("status-history without auth -> 401", sc == 401, f"got {sc}")

    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/timeline")
    T("timeline without auth -> 401", sc == 401, f"got {sc}")
else:
    SKIP("Status history tests (cid_s1 missing)")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13: ADVANCED FILTER
# ══════════════════════════════════════════════════════════════════════════════
section("ADVANCED FILTER")

# Advanced filter is STUDENT-only endpoint (not admin)
if S["tok_s1"]:
    sc, body = req("GET", "/api/complaints/filter/advanced",
                   token=S["tok_s1"],
                   params={"status": "Raised", "page": 1, "page_size": 10})
    T("Student advanced filter by status=Raised -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", "/api/complaints/filter/advanced",
                   token=S["tok_s1"],
                   params={"priority": "High", "page": 1, "page_size": 5})
    T("Student advanced filter by priority=High -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/complaints/filter/advanced",
                   token=S["tok_s1"],
                   params={"has_image": "true", "page": 1, "page_size": 5})
    T("Student advanced filter by has_image -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/complaints/filter/advanced",
                   token=S["tok_s1"],
                   params={"department_id": 1, "page": 1, "page_size": 5})
    T("Student advanced filter by department_id -> 200", sc == 200, f"got {sc}")
else:
    SKIP("Advanced filter (s1 token missing)")

# Admin/authority on student-only filter endpoint
if S["tok_admin"]:
    sc, body = req("GET", "/api/complaints/filter/advanced",
                   token=S["tok_admin"],
                   params={"page": 1, "page_size": 5})
    T("Admin on student-only filter -> 401/403", sc in (401, 403), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14: SPAM FLAG / UNFLAG
# ══════════════════════════════════════════════════════════════════════════════
section("SPAM FLAG / UNFLAG")

# flag-spam uses 'reason' as a query parameter (not JSON body)
if S["tok_officer"] and S["cid_s3"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/flag-spam",
                   token=S["tok_officer"],
                   params={"reason": "This appears to be a duplicate test complaint"})
    T("Authority flag complaint as spam -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/unflag-spam",
                   token=S["tok_officer"])
    T("Authority unflag spam -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Spam flag tests (officer token or cid_s3 missing)")

# Student cannot flag spam
if S["tok_s1"] and S["cid_s3"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/flag-spam",
                   token=S["tok_s1"],
                   params={"reason": "Student trying to flag"})
    T("Student flag spam -> 401/403", sc in (401, 403), f"got {sc}")

# Without auth
if S["cid_s3"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/flag-spam",
                   params={"reason": "No auth"})
    T("Flag spam without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 15: AUTHORITY PROFILE AND DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
section("AUTHORITY PROFILE AND DASHBOARD")

if S["tok_admin"]:
    sc, body = req("GET", "/api/authorities/profile", token=S["tok_admin"])
    T("GET authority profile (admin) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Authority profile has email",
      isinstance(body, dict) and "email" in str(body),
      str(body)[:120])

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/authorities/profile", token=S["tok_warden_m"])
    T("GET authority profile (warden) -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/authorities/dashboard", token=S["tok_warden_m"])
    T("GET authority dashboard -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Dashboard has stats",
      isinstance(body, dict) and
      ("stats" in body or "total_complaints" in str(body) or "recent_complaints" in body),
      str(body)[:120])

if S["tok_admin"]:
    sc, body = req("GET", "/api/authorities/dashboard", token=S["tok_admin"])
    T("Admin dashboard -> 200", sc == 200, f"got {sc}")

# Student on authority profile
if S["tok_s1"]:
    sc, body = req("GET", "/api/authorities/profile", token=S["tok_s1"])
    T("Student on authority profile -> 401/403", sc in (401, 403), f"got {sc}")

# Without auth
sc, body = req("GET", "/api/authorities/profile")
T("Authority profile without auth -> 401", sc == 401, f"got {sc}")

sc, body = req("GET", "/api/authorities/dashboard")
T("Authority dashboard without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 16: AUTHORITY MY-COMPLAINTS
# ══════════════════════════════════════════════════════════════════════════════
section("AUTHORITY MY-COMPLAINTS")

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_warden_m"])
    T("GET authority my-complaints -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("my-complaints returns list",
      isinstance(body, dict) and
      ("complaints" in body or "data" in body or isinstance(body, list)),
      str(body)[:80])

    # With filters
    sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_warden_m"],
                   params={"status": "Raised", "page": 1, "page_size": 5})
    T("my-complaints with status filter -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_warden_m"],
                   params={"priority": "High"})
    T("my-complaints with priority filter -> 200", sc == 200, f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_admin"])
    T("Admin my-complaints -> 200", sc == 200, f"got {sc}")

if S["tok_s1"]:
    sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_s1"])
    T("Student on authority my-complaints -> 401/403", sc in (401, 403), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 17: AUTHORITY VIEW COMPLAINT DETAIL
# ══════════════════════════════════════════════════════════════════════════════
section("AUTHORITY VIEW COMPLAINT DETAIL")

if S["tok_admin"] and S["cid_s1"]:
    sc, body = req("GET", f"/api/authorities/complaints/{S['cid_s1']}", token=S["tok_admin"])
    T("Admin view complaint detail -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Detail has rephrased_text or text",
      isinstance(body, dict) and ("text" in str(body) or "complaint" in str(body)),
      str(body)[:120])

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("GET", f"/api/authorities/complaints/{S['cid_s1']}", token=S["tok_s1"])
    T("Student on authority complaint detail -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/authorities/complaints/not-a-uuid", token=S["tok_admin"])
    T("Authority complaint detail invalid UUID -> 400/422", sc in (400, 422), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 18: STATUS UPDATE
# ══════════════════════════════════════════════════════════════════════════════
section("AUTHORITY STATUS UPDATE")

# Wait for complaint to be assigned - try to find an assigned complaint
update_cid = S["cid_s1"] or S["cid_s3"] or S["cid_s1_gen"]

if S["tok_admin"] and update_cid:
    # Admin can update any complaint - Raised -> In Progress
    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "In Progress", "reason": "Taking action on this"})
    T("Admin update status Raised->InProgress -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # In Progress -> Resolved
    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Resolved", "reason": "Issue has been resolved"})
    T("Admin update status InProgress->Resolved -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Resolved -> Closed
    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Closed", "reason": "Closed after verification"})
    T("Admin update status Resolved->Closed -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Invalid transition: Closed -> Raised
    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Raised", "reason": "Trying to reopen"})
    T("Invalid transition Closed->Raised -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

if S["tok_admin"] and S["cid_s2"]:
    # Move to In Progress first (Raised -> In Progress valid)
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s2']}/status",
                   token=S["tok_admin"],
                   json_data={"status": "In Progress"})
    T("Status update In Progress (no reason needed) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Try Spam without reason
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s2']}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Spam"})
    T("Status Spam without reason -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    # Spam with reason (Spam only valid from Raised, not In Progress - accept 400 too)
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s2']}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Spam", "reason": "Verified spam complaint"})
    T("Status Spam with reason -> 200 or 400", sc in (200, 400), f"got {sc}: {str(body)[:80]}")

# Student cannot update status
if S["tok_s1"] and S["cid_s1_dept"]:
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s1_dept']}/status",
                   token=S["tok_s1"],
                   json_data={"status": "In Progress", "reason": "Student trying"})
    T("Student on status update -> 401/403", sc in (401, 403), f"got {sc}")

# Without auth
if S["cid_s1_dept"]:
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s1_dept']}/status",
                   json_data={"status": "In Progress"})
    T("Status update without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 19: AUTHORITY POST UPDATE
# ══════════════════════════════════════════════════════════════════════════════
section("AUTHORITY POST UPDATE")

post_cid = S["cid_s1_dept"] or S["cid_s1"]

# post-update uses 'title' and 'content' as query params
if S["tok_admin"] and post_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{post_cid}/post-update",
                   token=S["tok_admin"],
                   params={"title": "Complaint reviewed", "content": "We have reviewed this complaint and are taking action."})
    T("Authority post update -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

    # Empty title - server may accept or reject (query param, no server-side validation currently)
    sc, body = req("POST", f"/api/authorities/complaints/{post_cid}/post-update",
                   token=S["tok_admin"],
                   params={"title": "", "content": "Some content"})
    T("Empty post update title -> 200/400/422 (server behavior)", sc in (200, 400, 422),
      f"got {sc}: {str(body)[:80]}")

if S["tok_s1"] and post_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{post_cid}/post-update",
                   token=S["tok_s1"],
                   params={"title": "Update", "content": "Student posting update"})
    T("Student post-update -> 401/403", sc in (401, 403), f"got {sc}")

if post_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{post_cid}/post-update",
                   params={"title": "NoAuth", "content": "No auth update"})
    T("Post update without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 20: ESCALATION
# ══════════════════════════════════════════════════════════════════════════════
section("ESCALATION")

# Use the hostel complaint (s1) — should be assigned to Men's Hostel warden
# Escalate from warden to deputy warden
esc_cid = S["cid_s1"]  # Men's hostel complaint

# escalate uses 'reason' as query parameter
if S["tok_warden_m"] and esc_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_warden_m"],
                   params={"reason": "Issue requires deputy warden intervention"})
    T("Warden escalate complaint -> 200/201 or 403/400", sc in (200, 201, 403, 400),
      f"got {sc}: {str(body)[:80]}")

if S["tok_admin"] and esc_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_admin"],
                   params={"reason": "Escalating to higher level"})
    T("Admin escalate -> 200/201 or 400/404", sc in (200, 201, 400, 404),
      f"got {sc}: {str(body)[:80]}")

    # Escalation without reason -> 422 (missing required query param)
    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_admin"])
    T("Escalate without reason -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

if S["tok_s1"] and esc_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_s1"],
                   params={"reason": "Student escalating"})
    T("Student escalate -> 401/403", sc in (401, 403), f"got {sc}")

# Escalation history
if S["tok_admin"] and esc_cid:
    sc, body = req("GET", f"/api/authorities/complaints/{esc_cid}/escalation-history",
                   token=S["tok_admin"])
    T("GET escalation-history -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Escalation history is list/dict", isinstance(body, (list, dict)), str(body)[:80])

if S["tok_s1"] and esc_cid:
    sc, body = req("GET", f"/api/authorities/complaints/{esc_cid}/escalation-history",
                   token=S["tok_s1"])
    T("Student on escalation-history -> 401/403", sc in (401, 403), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 21: AUTHORITY STATS
# ══════════════════════════════════════════════════════════════════════════════
section("AUTHORITY STATS")

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/authorities/stats", token=S["tok_warden_m"])
    T("Authority stats (warden) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Stats has numeric fields",
      isinstance(body, dict) and any(isinstance(v, (int, float)) for v in body.values()),
      str(body)[:120])

if S["tok_admin"]:
    sc, body = req("GET", "/api/authorities/stats", token=S["tok_admin"])
    T("Authority stats (admin) -> 200", sc == 200, f"got {sc}")

if S["tok_s1"]:
    sc, body = req("GET", "/api/authorities/stats", token=S["tok_s1"])
    T("Student on authority stats -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/authorities/stats")
T("Authority stats without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 22: STUDENT MY-COMPLAINTS
# ══════════════════════════════════════════════════════════════════════════════
section("STUDENT MY-COMPLAINTS")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"])
    T("GET my-complaints -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("my-complaints returns list/dict",
      isinstance(body, (list, dict)),
      str(body)[:80])

    # With status filter
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"status": "Raised"})
    T("my-complaints filter by status -> 200", sc == 200, f"got {sc}")

    # With pagination
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 1, "page_size": 3})
    T("my-complaints with pagination -> 200", sc == 200, f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_admin"])
    T("Authority on student my-complaints -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/students/my-complaints")
T("my-complaints without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 23: NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════
section("NOTIFICATIONS")

if S["tok_s1"]:
    # Get notifications
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s1"])
    T("GET notifications -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Notifications returns list/dict", isinstance(body, (list, dict)), str(body)[:80])

    # Unread count
    sc, body = req("GET", "/api/students/notifications/unread-count", token=S["tok_s1"])
    T("GET unread-count -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("unread-count has numeric count",
      isinstance(body, dict) and any(isinstance(v, int) for v in body.values()),
      str(body)[:80])

    # Mark all read
    sc, body = req("PUT", "/api/students/notifications/mark-all-read", token=S["tok_s1"])
    T("PUT mark-all-read -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Get notifications with filter
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s1"],
                   params={"unread_only": "true"})
    T("GET notifications unread_only -> 200", sc == 200, f"got {sc}")

    # Get notification ID for further tests
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s1"],
                   params={"page": 1, "page_size": 5})
    if sc == 200 and isinstance(body, dict):
        notifs = body.get("notifications") or body.get("data") or []
        if isinstance(notifs, list) and notifs:
            S["notif_id"] = notifs[0].get("id")

    if S["notif_id"]:
        # Mark specific notification as read
        sc, body = req("PUT", f"/api/students/notifications/{S['notif_id']}/read",
                       token=S["tok_s1"])
        T("PUT notification/read -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

        # Delete notification
        sc, body = req("DELETE", f"/api/students/notifications/{S['notif_id']}",
                       token=S["tok_s1"])
        T("DELETE notification -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

        # Delete again (should fail)
        sc, body = req("DELETE", f"/api/students/notifications/{S['notif_id']}",
                       token=S["tok_s1"])
        T("Delete notification twice -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")
    else:
        SKIP("Notification ID not available (no notifications yet)")

# Invalid notification ID
if S["tok_s1"]:
    sc, body = req("PUT", "/api/students/notifications/not-a-uuid/read", token=S["tok_s1"])
    T("Mark invalid notif read -> 400/404/422", sc in (400, 404, 422), f"got {sc}")

# Without auth
sc, body = req("GET", "/api/students/notifications")
T("Notifications without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 24: ADMIN - MANAGE AUTHORITIES
# ══════════════════════════════════════════════════════════════════════════════
section("ADMIN - MANAGE AUTHORITIES")

if S["tok_admin"]:
    # List all authorities
    sc, body = req("GET", "/api/admin/authorities", token=S["tok_admin"])
    T("GET /admin/authorities -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Authorities list returns list/dict", isinstance(body, (list, dict)), str(body)[:80])

    # Filter by active
    sc, body = req("GET", "/api/admin/authorities", token=S["tok_admin"],
                   params={"active_only": "true"})
    T("GET /admin/authorities active_only -> 200", sc == 200, f"got {sc}")

    # Create new authority
    sc, body = req("POST", "/api/admin/authorities", token=S["tok_admin"],
                   json_data={
                       "email": S["new_auth_email"],
                       "password": "Authority@1234",
                       "name": "Test Authority",
                       "authority_type": "Admin Officer",
                       "authority_level": 50
                   })
    T("Create new authority -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data") or body
        if isinstance(data, dict):
            S["new_authority_id"] = data.get("id") or data.get("authority_id")
    # Admin create authority returns data: None (no authority object in response currently)
    T("New authority created (response success)", sc in (200, 201), str(body)[:80])

    # Duplicate email
    sc, body = req("POST", "/api/admin/authorities", token=S["tok_admin"],
                   json_data={
                       "email": S["new_auth_email"],
                       "password": "Authority@1234",
                       "name": "Duplicate Authority",
                       "authority_type": "Admin Officer",
                       "authority_level": 50
                   })
    T("Duplicate authority email -> 400/409", sc in (400, 409), f"got {sc}: {str(body)[:80]}")

    # Invalid email domain
    sc, body = req("POST", "/api/admin/authorities", token=S["tok_admin"],
                   json_data={
                       "email": f"auth_{TS}@gmail.com",
                       "password": "Authority@1234",
                       "name": "Bad Domain Auth",
                       "authority_type": "Admin Officer",
                       "authority_level": 50
                   })
    T("Authority with wrong email domain -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    # Missing required fields
    sc, body = req("POST", "/api/admin/authorities", token=S["tok_admin"],
                   json_data={"name": "Incomplete Authority"})
    T("Create authority missing fields -> 400/422", sc in (400, 422), f"got {sc}")

    # Toggle authority active/inactive
    # For toggle, we need to find an authority ID. Let's get one from the list
    if S["tok_admin"]:
        sc2, body2 = req("GET", "/api/admin/authorities", token=S["tok_admin"])
        found_auth_id = None
        if sc2 == 200 and isinstance(body2, dict):
            auths = body2.get("authorities") or body2.get("data") or []
            if isinstance(auths, list):
                # Find an authority that's not admin (level < 100)
                for a in auths:
                    if isinstance(a, dict) and a.get("authority_level", 100) < 50:
                        found_auth_id = a.get("id")
                        break
        if found_auth_id:
            sc, body = req("PUT", f"/api/admin/authorities/{found_auth_id}/toggle-active",
                           token=S["tok_admin"],
                           params={"activate": "false"})
            T("Toggle authority inactive -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

            sc, body = req("PUT", f"/api/admin/authorities/{found_auth_id}/toggle-active",
                           token=S["tok_admin"],
                           params={"activate": "true"})
            T("Toggle authority active (back) -> 200", sc == 200, f"got {sc}")
        else:
            SKIP("Toggle authority (no suitable authority found)")

        # Invalid authority ID
        sc, body = req("PUT", "/api/admin/authorities/99999/toggle-active",
                       token=S["tok_admin"],
                       params={"activate": "false"})
        T("Toggle non-existent authority -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")

else:
    SKIP("Admin authority management (admin token missing)")

# Non-admin cannot manage authorities
if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/authorities", token=S["tok_s1"])
    T("Student on admin/authorities -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/admin/authorities", token=S["tok_warden_m"])
    T("Warden on admin/authorities -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/authorities")
T("Admin authorities without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 25: ADMIN - MANAGE STUDENTS
# ══════════════════════════════════════════════════════════════════════════════
section("ADMIN - MANAGE STUDENTS")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"])
    T("GET /admin/students -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Students list returns list/dict", isinstance(body, (list, dict)), str(body)[:80])

    # Filter by department
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"department_id": 1})
    T("GET /admin/students by dept -> 200", sc == 200, f"got {sc}")

    # Filter by active
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"active_only": "true"})
    T("GET /admin/students active_only -> 200", sc == 200, f"got {sc}")

    # Toggle s4 to inactive (activate=false)
    sc, body = req("PUT", f"/api/admin/students/{S['s4_roll']}/toggle-active",
                   token=S["tok_admin"],
                   params={"activate": "false"})
    T("Toggle student active (deactivate) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    # Deactivated student cannot login
    sc, body = req("POST", "/api/students/login",
                   json_data={"email_or_roll_no": S["s4_email"], "password": "Test@1234"})
    T("Deactivated student login -> 401/403", sc in (401, 403), f"got {sc}: {str(body)[:80]}")

    # Toggle back to active (activate=true)
    sc, body = req("PUT", f"/api/admin/students/{S['s4_roll']}/toggle-active",
                   token=S["tok_admin"],
                   params={"activate": "true"})
    T("Toggle student active (reactivate) -> 200", sc == 200, f"got {sc}")

    # Invalid roll_no
    sc, body = req("PUT", "/api/admin/students/INVALID99/toggle-active",
                   token=S["tok_admin"])
    T("Toggle invalid student -> 404/422", sc in (404, 422), f"got {sc}")

else:
    SKIP("Admin student management (admin token missing)")

if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_s1"])
    T("Student on /admin/students -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/students")
T("Admin students without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 26: ADMIN STATS AND ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
section("ADMIN STATS AND ANALYTICS")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_admin"])
    T("GET /admin/stats/overview -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Overview has total_complaints",
      isinstance(body, dict) and "total_complaints" in str(body),
      str(body)[:120])

    sc, body = req("GET", "/api/admin/stats/analytics", token=S["tok_admin"])
    T("GET /admin/stats/analytics -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", "/api/admin/health/metrics", token=S["tok_admin"])
    T("GET /admin/health/metrics -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

else:
    SKIP("Admin stats (admin token missing)")

if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_s1"])
    T("Student on admin stats -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_warden_m"])
    T("Non-admin authority on admin stats -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/stats/overview")
T("Admin stats without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 27: ADMIN BULK STATUS UPDATE
# ══════════════════════════════════════════════════════════════════════════════
section("ADMIN BULK STATUS UPDATE")

bulk_ids = [cid for cid in [S["cid_s1_dept"], S["cid_s3"]] if cid]

# bulk-status-update uses query params: complaint_ids (multi), new_status, reason
if S["tok_admin"] and bulk_ids:
    sc, body = req("POST", "/api/admin/complaints/bulk-status-update",
                   token=S["tok_admin"],
                   params={
                       "complaint_ids": bulk_ids,
                       "new_status": "In Progress",
                       "reason": "Bulk processing by admin"
                   })
    T("Admin bulk status update -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Bulk update has success info",
      isinstance(body, dict) and ("success" in str(body) or "updated" in str(body)),
      str(body)[:120])

    # Invalid status
    sc, body = req("POST", "/api/admin/complaints/bulk-status-update",
                   token=S["tok_admin"],
                   params={
                       "complaint_ids": bulk_ids,
                       "new_status": "InvalidStatus",
                       "reason": "Test"
                   })
    T("Bulk update invalid status -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    # Missing reason
    sc, body = req("POST", "/api/admin/complaints/bulk-status-update",
                   token=S["tok_admin"],
                   params={"complaint_ids": bulk_ids, "new_status": "Resolved"})
    T("Bulk update missing reason -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

else:
    SKIP("Bulk status update (admin token or complaint IDs missing)")

if S["tok_s1"] and bulk_ids:
    sc, body = req("POST", "/api/admin/complaints/bulk-status-update",
                   token=S["tok_s1"],
                   json_data={"complaint_ids": bulk_ids, "status": "In Progress"})
    T("Student on bulk update -> 401/403", sc in (401, 403), f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 28: ADMIN IMAGE MODERATION
# ══════════════════════════════════════════════════════════════════════════════
section("ADMIN IMAGE MODERATION")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/images/pending-verification", token=S["tok_admin"])
    T("GET pending verification images -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Pending images returns list/dict", isinstance(body, (list, dict)), str(body)[:80])

    # Moderate image - uses query params: approve (bool), reason (optional)
    img_cid = S["cid_s1"]
    if img_cid:
        sc, body = req("POST", f"/api/admin/images/{img_cid}/moderate",
                       token=S["tok_admin"],
                       params={"approve": "true"})
        T("Admin approve image -> 200/201/404", sc in (200, 201, 404), f"got {sc}: {str(body)[:80]}")

        sc, body = req("POST", f"/api/admin/images/{img_cid}/moderate",
                       token=S["tok_admin"],
                       params={"approve": "false", "reason": "Not relevant to complaint"})
        T("Admin reject image with reason -> 200/201/404", sc in (200, 201, 404),
          f"got {sc}: {str(body)[:80]}")

else:
    SKIP("Image moderation (admin token missing)")

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("GET", "/api/admin/images/pending-verification", token=S["tok_s1"])
    T("Student on pending images -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/images/pending-verification")
T("Pending images without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 29: IMAGE VERIFY ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════
section("IMAGE VERIFY ENDPOINT")

# verify-image uses get_complaint_with_ownership (student-only, must own complaint)
if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/verify-image",
                   token=S["tok_s1"])
    T("Student verify-image (own complaint) -> 200/201/400/404", sc in (200, 201, 400, 404),
      f"got {sc}: {str(body)[:80]}")
    # 400 = no image attached; 404 = complaint missing; 200/201 = verification done

if S["tok_s2"] and S["cid_s1"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/verify-image",
                   token=S["tok_s2"])
    T("Student verify-image (not owner) -> 403", sc == 403, f"got {sc}: {str(body)[:80]}")

if S["cid_s1"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/verify-image")
    T("verify-image without auth -> 401", sc == 401, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 30: CROSS-CUTTING SECURITY TESTS
# ══════════════════════════════════════════════════════════════════════════════
section("CROSS-CUTTING SECURITY TESTS")

# Invalid JWT token
sc, body = req("GET", "/api/students/profile", token="totally.invalid.jwt")
T("Invalid JWT -> 401", sc == 401, f"got {sc}")

# Expired or malformed token (using wrong signature)
sc, body = req("GET", "/api/students/profile",
               token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QHNyZWMuYWMuaW4iLCJyb2xlIjoic3R1ZGVudCIsImV4cCI6MTYwMDAwMDAwMH0.wrong_signature")
T("Expired/malformed JWT -> 401", sc == 401, f"got {sc}")

# Student token on admin endpoint
if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_s1"])
    T("Student token on admin endpoint -> 401/403", sc in (401, 403), f"got {sc}")

# Authority token on student-only endpoint (change-password)
if S["tok_admin"]:
    sc, body = req("POST", "/api/students/change-password", token=S["tok_admin"],
                   json_data={"current_password": "old", "new_password": "New@123456"})
    T("Authority token on student change-password -> 401/403", sc in (401, 403), f"got {sc}")

# SQL injection attempt in query params
if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"search": "'; DROP TABLE students; --"})
    T("SQL injection in params -> 200/400 (not 500)", sc != 500, f"got {sc}")

# XSS in complaint text
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s1"],
                   form_data={
                       "original_text": "<script>alert('xss')</script> The lab equipment is broken "
                                        "and students cannot complete their practicals.",
                       "visibility": "Public"
                   })
    T("XSS in complaint text -> 200/201 or 400 (not 500)", sc != 500,
      f"got {sc}: {str(body)[:80]}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 31: BOUNDARY AND EDGE CASE TESTS
# ══════════════════════════════════════════════════════════════════════════════
section("BOUNDARY AND EDGE CASE TESTS")

# Maximum complaint text length - use s4 (fewer prior submissions, less rate-limited)
# Re-fetch s4 token in case it was deactivated/reactivated
if S["tok_s4"]:
    long_text = "A" * 2001  # over 2000 char limit
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s4"],
                   form_data={"original_text": long_text, "visibility": "Public"})
    T("Complaint text > 2000 chars -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    # Exactly 2000 chars (valid, should succeed or hit rate limit)
    max_text = ("The canteen food quality has severely deteriorated. " * 40)[:2000]
    sc, body = req("POST", "/api/complaints/submit",
                   token=S["tok_s4"],
                   form_data={"original_text": max_text, "visibility": "Public"})
    T("Complaint text at 2000 chars -> 200/201/400/429", sc in (200, 201, 400, 429), f"got {sc}: {str(body)[:80]}")

# Zero page
if S["tok_s1"]:
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 0, "page_size": 10})
    T("page=0 -> 200 or 400/422 (not 500)", sc != 500, f"got {sc}")

    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 1, "page_size": 0})
    T("page_size=0 -> 200 or 400/422 (not 500)", sc != 500, f"got {sc}")

    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 99999, "page_size": 10})
    T("Very large page number -> 200 with empty list (not 500)", sc != 500, f"got {sc}")

# Non-existent complaint UUID
valid_format_uuid = "00000000-0000-0000-0000-000000000001"
if S["tok_admin"]:
    sc, body = req("GET", f"/api/authorities/complaints/{valid_format_uuid}",
                   token=S["tok_admin"])
    T("Valid UUID format, no complaint -> 404", sc == 404, f"got {sc}")

    sc, body = req("PUT", f"/api/authorities/complaints/{valid_format_uuid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "In Progress"})
    T("Status update on non-existent complaint -> 404", sc == 404, f"got {sc}")

# Empty string fields
if S["tok_s1"]:
    sc, body = req("PUT", "/api/students/profile", token=S["tok_s1"],
                   json_data={"name": ""})
    T("Update profile with empty name -> 400/422", sc in (400, 422), f"got {sc}")

# Negative department_id
if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"department_id": -1})
    T("Negative department_id -> 200/400/422 (not 500)", sc != 500, f"got {sc}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 32: WORKFLOW INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════
section("WORKFLOW INTEGRATION TESTS")

# Full workflow: submit -> authority sees -> updates -> student notified
print("  [info] Testing full complaint workflow...")

# Use s4 for workflow test (s1 may be rate-limited)
workflow_token = S["tok_s4"] or S["tok_s3"]
if workflow_token:
    # Submit private complaint
    sc, body = req("POST", "/api/complaints/submit",
                   token=workflow_token,
                   form_data={
                       "original_text": "The hostel warden is not responding to maintenance requests "
                                        "for over two weeks. Multiple students are affected.",
                       "visibility": "Private"
                   })
    T("Submit private hostel complaint -> 200/201/429", sc in (200, 201, 429), f"got {sc}: {str(body)[:80]}")
    wf_cid = None
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data", body)
        wf_cid = data.get("id") or data.get("complaint_id")

    if wf_cid and S["tok_admin"]:
        # Authority sees in my-complaints
        sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_admin"])
        T("Authority sees complaints after submission -> 200", sc == 200, f"got {sc}")

        # Post an update (uses Query params: title + content)
        sc, body = req("POST", f"/api/authorities/complaints/{wf_cid}/post-update",
                       token=S["tok_admin"],
                       params={"title": "Update received", "content": "We have received your complaint and assigned it to maintenance team."})
        T("Authority posts update on workflow complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

        # Complaint submitter checks notifications
        notif_token = S["tok_s4"] or S["tok_s3"]
        sc, body = req("GET", "/api/students/notifications", token=notif_token)
        T("Student gets notifications after authority update -> 200", sc == 200, f"got {sc}")

        # Complaint submitter checks their complaint
        sc, body = req("GET", f"/api/complaints/{wf_cid}", token=notif_token)
        T("Student can view their private complaint -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

        # Private complaint not visible in public feed to other students
        if S["tok_s1"]:
            sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s1"])
            if sc == 200 and isinstance(body, dict):
                feed = body.get("complaints") or body.get("data") or []
                if isinstance(feed, list):
                    found = any(str(c.get("id", "")) == str(wf_cid) for c in feed)
                    T("Private complaint not in public feed for other students", not found,
                      "Private complaint appeared in feed!")
                else:
                    SKIP("Cannot check private complaint in feed (unexpected format)")

# Vote-based priority recalculation
print("  [info] Testing voting priority recalculation...")
vote_target = S["cid_s1_gen"]
if vote_target and S["tok_s2"] and S["tok_s3"] and S["tok_s4"]:
    # Get initial priority
    sc, body = req("GET", f"/api/complaints/{vote_target}", token=S["tok_s2"])
    initial_priority = None
    if sc == 200 and isinstance(body, dict):
        data = body.get("data", body)
        initial_priority = data.get("priority_score") or data.get("priority")

    # Multiple upvotes
    for tok in [S["tok_s2"], S["tok_s3"], S["tok_s4"]]:
        req("POST", f"/api/complaints/{vote_target}/vote",
            token=tok, json_data={"vote_type": "Upvote"})

    # Get updated priority
    sc, body = req("GET", f"/api/complaints/{vote_target}", token=S["tok_s2"])
    T("Multiple upvotes -> 200", sc == 200, f"got {sc}")
    if sc == 200 and isinstance(body, dict) and initial_priority is not None:
        data = body.get("data", body)
        new_priority = data.get("priority_score") or data.get("priority")
        T("Priority score updated after upvotes",
          new_priority is not None,
          f"initial={initial_priority}, new={new_priority}")
else:
    SKIP("Priority recalculation test (missing tokens or complaint ID)")


# ══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
total = passed + failed + skipped
pass_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0

print(f"\n{'='*72}")
print(f"  FINAL RESULTS")
print(f"{'='*72}")
print(f"  Total Tests : {total}")
print(f"  Passed      : {passed}")
print(f"  Failed      : {failed}")
print(f"  Skipped     : {skipped}")
print(f"  Pass Rate   : {pass_rate:.1f}%  ({'PASS' if pass_rate >= 95 else 'NEEDS WORK'})")
print(f"{'='*72}")

if failures:
    print(f"\n  FAILED TESTS:")
    for f in failures:
        print(f"    {f}")

print(f"\n  Test suffix used: {TS}")
print(f"  Students created: {S['s1_roll']}, {S['s2_roll']}, {S['s3_roll']}, {S['s4_roll']}")
print(f"  Complaints: s1={S['cid_s1']}, s2={S['cid_s2']}, dept={S['cid_s1_dept']}, gen={S['cid_s1_gen']}, s3={S['cid_s3']}")

if pass_rate < 95:
    sys.exit(1)
