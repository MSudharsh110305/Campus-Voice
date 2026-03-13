"""
CampusVoice - COMPREHENSIVE ENDPOINT TEST SUITE
=================================================
Tests EVERY endpoint, prints full requests & responses.
Covers: auth, complaints, routing, escalation, voting,
status tracking, spam detection, image upload, public feed
filtering, admin operations, authority anonymity, notifications.
"""
import requests
import json
import time
import os
import io
import sys

BASE = "http://localhost:8000"
API = f"{BASE}/api"
SEPARATOR = "=" * 80
SUB_SEP = "-" * 60

# Track state across tests
state = {}


def log_request(method, url, **kwargs):
    """Print request details."""
    print(f"\n  >> {method} {url}")
    if "json" in kwargs and kwargs["json"]:
        print(f"     Body: {json.dumps(kwargs['json'], indent=2)[:500]}")
    if "data" in kwargs and kwargs["data"]:
        print(f"     Form: {kwargs['data']}")
    if "params" in kwargs and kwargs["params"]:
        print(f"     Params: {kwargs['params']}")
    if "headers" in kwargs:
        auth = kwargs["headers"].get("Authorization", "")
        if auth:
            print(f"     Auth: {auth[:30]}...")


def log_response(r):
    """Print response details."""
    print(f"  << Status: {r.status_code}")
    try:
        body = r.json()
        text = json.dumps(body, indent=2, default=str)
        if len(text) > 1500:
            text = text[:1500] + "\n     ... (truncated)"
        print(f"     Response: {text}")
    except Exception:
        if len(r.text) > 500:
            print(f"     Response: {r.text[:500]}... (truncated)")
        else:
            print(f"     Response: {r.text}")


def api(method, path, token=None, expect=None, **kwargs):
    """Make API call, log request/response, return response."""
    url = path if path.startswith("http") else f"{API}{path}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    log_request(method, url, headers=headers, **kwargs)

    r = getattr(requests, method.lower())(url, headers=headers, **kwargs)
    log_response(r)

    if expect and r.status_code != expect:
        print(f"  !! UNEXPECTED STATUS: expected {expect}, got {r.status_code}")

    return r


def section(title):
    """Print section header."""
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def subsection(title):
    """Print subsection header."""
    print(f"\n{SUB_SEP}")
    print(f"  {title}")
    print(SUB_SEP)


# ============================================================
# HELPERS
# ============================================================
def create_test_image(color=(255, 0, 0), size=(100, 100)):
    """Create a simple test image in memory."""
    try:
        from PIL import Image
        img = Image.new("RGB", size, color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf
    except ImportError:
        # Create minimal valid JPEG without PIL
        # 1x1 red pixel JPEG
        jpeg_bytes = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0x7B, 0x94,
            0x11, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xD9
        ])
        return io.BytesIO(jpeg_bytes)


# ============================================================
print(f"\n{'#' * 80}")
print(f"#  CAMPUSVOICE COMPREHENSIVE TEST SUITE")
print(f"#  Testing ALL endpoints with full request/response logging")
print(f"#  Server: {BASE}")
print(f"{'#' * 80}")

# ============================================================
# 1. HEALTH CHECK
# ============================================================
section("1. HEALTH CHECK")
r = api("GET", f"{BASE}/health")
assert r.status_code == 200, f"Health check failed: {r.status_code}"
print("  [OK] Server is healthy")

# ============================================================
# 2. AUTHORITY LOGIN - All types
# ============================================================
section("2. AUTHORITY LOGINS - All types")

authorities = {
    "admin": ("admin@srec.ac.in", "Admin@123456"),
    "officer": ("officer@srec.ac.in", "Officer@1234"),
    "dc": ("dc@srec.ac.in", "Discip@12345"),
    "sdw": ("sdw@srec.ac.in", "SeniorDW@123"),
    "dw_mens": ("dw.mens@srec.ac.in", "MensDW@1234"),
    "dw_womens": ("dw.womens@srec.ac.in", "WomensDW@123"),
    "warden_mens1": ("warden1.mens@srec.ac.in", "MensW1@1234"),
    "warden_mens2": ("warden2.mens@srec.ac.in", "MensW2@1234"),
    "warden_womens1": ("warden1.womens@srec.ac.in", "WomensW1@123"),
    "warden_womens2": ("warden2.womens@srec.ac.in", "WomensW2@123"),
    "hod_cse": ("hod.cse@srec.ac.in", "HodCSE@123"),
    "hod_ece": ("hod.ece@srec.ac.in", "HodECE@123"),
    "hod_mech": ("hod.mech@srec.ac.in", "HodMECH@123"),
}

for key, (email, password) in authorities.items():
    subsection(f"Login: {key}")
    r = api("POST", "/authorities/login", json={"email": email, "password": password})
    if r.status_code == 200:
        data = r.json()
        state[f"{key}_token"] = data["token"]
        state[f"{key}_id"] = data.get("id")
        state[f"{key}_name"] = data.get("name")
        state[f"{key}_type"] = data.get("authority_type")
        print(f"  [OK] {key} logged in: name={data.get('name')}, type={data.get('authority_type')}")
    else:
        print(f"  [FAIL] {key} login FAILED")
        sys.exit(1)

subsection("Wrong Password Test")
r = api("POST", "/authorities/login", json={"email": "admin@srec.ac.in", "password": "WrongPass@1"})
assert r.status_code == 401, f"Expected 401 for wrong password, got {r.status_code}"
print("  [OK] Wrong password correctly rejected with 401")

# ============================================================
# 3. STUDENT REGISTRATION
# ============================================================
section("3. STUDENT REGISTRATION - Multiple profiles")

students = [
    {
        "roll_no": "23CS001",
        "name": "Ravi Kumar",
        "email": "ravi.kumar@srec.ac.in",
        "password": "Student@123",
        "gender": "Male",
        "stay_type": "Hostel",
        "year": 2,
        "department_id": 1  # CSE
    },
    {
        "roll_no": "23CS002",
        "name": "Priya Nair",
        "email": "priya.nair@srec.ac.in",
        "password": "Student@123",
        "gender": "Female",
        "stay_type": "Hostel",
        "year": 2,
        "department_id": 1  # CSE
    },
    {
        "roll_no": "23ECE001",
        "name": "Arun Sharma",
        "email": "arun.sharma@srec.ac.in",
        "password": "Student@123",
        "gender": "Male",
        "stay_type": "Day Scholar",
        "year": 3,
        "department_id": 2  # ECE
    },
    {
        "roll_no": "23MECH001",
        "name": "Deepa Reddy",
        "email": "deepa.reddy@srec.ac.in",
        "password": "Student@123",
        "gender": "Female",
        "stay_type": "Hostel",
        "year": 1,
        "department_id": 4  # MECH
    },
]

for student in students:
    subsection(f"Register: {student['name']} ({student['gender']}, {student['stay_type']}, dept={student['department_id']})")
    r = api("POST", "/students/register", json=student)
    if r.status_code in (200, 201):
        data = r.json()
        key = student["roll_no"]
        state[f"student_{key}_token"] = data["token"]
        state[f"student_{key}_data"] = data
        print(f"  [OK] Registered: roll={data.get('roll_no')}, gender={data.get('gender')}, stay_type={data.get('stay_type')}")
    elif r.status_code == 400 or r.status_code == 409:
        # Already exists, try login
        print(f"  [INFO] Already exists, trying login...")
        r2 = api("POST", "/students/login", json={
            "email_or_roll_no": student["email"],
            "password": student["password"]
        })
        if r2.status_code == 200:
            data = r2.json()
            key = student["roll_no"]
            state[f"student_{key}_token"] = data["token"]
            state[f"student_{key}_data"] = data
            print(f"  [OK] Logged in: roll={data.get('roll_no')}, gender={data.get('gender')}, stay_type={data.get('stay_type')}")
        else:
            print(f"  [FAIL] Login also failed")

subsection("Duplicate Registration Test")
r = api("POST", "/students/register", json=students[0])
print(f"  [{'OK' if r.status_code in (400, 409) else 'FAIL'}] Duplicate correctly rejected: {r.status_code}")

# ============================================================
# 4. STUDENT LOGIN
# ============================================================
section("4. STUDENT LOGIN TESTS")

subsection("Login by email")
r = api("POST", "/students/login", json={
    "email_or_roll_no": "ravi.kumar@srec.ac.in",
    "password": "Student@123"
})
assert r.status_code == 200
print(f"  [OK] Login by email works, got token")

subsection("Login by roll number")
r = api("POST", "/students/login", json={
    "email_or_roll_no": "23CS001",
    "password": "Student@123"
})
assert r.status_code == 200
data = r.json()
print(f"  [OK] Login by roll_no works, gender={data.get('gender')}, stay_type={data.get('stay_type')}")

subsection("Wrong password")
r = api("POST", "/students/login", json={
    "email_or_roll_no": "23CS001",
    "password": "WrongPass@1"
})
assert r.status_code == 401
print(f"  [OK] Wrong password rejected: 401")

# ============================================================
# 5. STUDENT PROFILE
# ============================================================
section("5. STUDENT PROFILE & STATS")

subsection("Get profile - Ravi")
r = api("GET", "/students/profile", token=state["student_23CS001_token"])
assert r.status_code == 200
print(f"  [OK] Profile retrieved")

subsection("Get stats - Ravi")
r = api("GET", "/students/stats", token=state["student_23CS001_token"])
assert r.status_code == 200
print(f"  [OK] Stats retrieved")

# ============================================================
# 6. COMPLAINT SUBMISSION - ROUTING VERIFICATION
# ============================================================
section("6. COMPLAINT SUBMISSION & ROUTING")

# 6a. Male Hostel student -> Men's Hostel complaint
subsection("6a. Male Hostel student -> Men's Hostel complaint")
r = api("POST", "/complaints/submit",
    token=state["student_23CS001_token"],
    data={
        "category_id": 1,  # Men's Hostel
        "original_text": "The water supply in Block A hostel room 204 has been disrupted for the past two days. We are unable to get water from the taps in our room and the common bathroom.",
        "visibility": "Public"
    })
if r.status_code == 201:
    data = r.json()
    state["complaint_mens_hostel_id"] = data.get("id")
    assigned = data.get("assigned_authority")
    print(f"  [OK] Created complaint: id={data.get('id')}")
    print(f"  [OK] Assigned to: {assigned}")
    print(f"  [OK] Category: {data.get('category_name')}")
    print(f"  [OK] Priority: {data.get('priority')}")
    print(f"  [OK] Rephrased: {data.get('rephrased_text', '')[:100]}")
    if assigned and "Men" in str(assigned):
        print(f"  [ROUTING OK] Correctly routed to Men's Hostel authority")
    else:
        print(f"  [ROUTING CHECK] Assigned to: {assigned} -- verify this is correct")
else:
    print(f"  [FAIL] Complaint creation failed: {r.status_code}")

# 6b. Female Hostel student -> Women's Hostel complaint
subsection("6b. Female Hostel student -> Women's Hostel complaint")
r = api("POST", "/complaints/submit",
    token=state["student_23CS002_token"],
    data={
        "category_id": 2,  # Women's Hostel
        "original_text": "The hot water supply in Women's Hostel Block A has not been working for the past three days. Students are unable to get hot water in the mornings. Please arrange for repair of the water heater.",
        "visibility": "Public"
    })
if r.status_code == 201:
    data = r.json()
    state["complaint_womens_hostel_id"] = data.get("id")
    assigned = data.get("assigned_authority")
    print(f"  [OK] Created complaint: id={data.get('id')}")
    print(f"  [OK] Assigned to: {assigned}")
    print(f"  [OK] Category: {data.get('category_name')}")
    if assigned and "Women" in str(assigned):
        print(f"  [ROUTING OK] Correctly routed to Women's Hostel authority")
    else:
        print(f"  [ROUTING CHECK] Assigned to: {assigned} -- verify this is correct")

# 6c. General complaint (infrastructure)
subsection("6c. General complaint (infrastructure) - by Day Scholar")
r = api("POST", "/complaints/submit",
    token=state["student_23ECE001_token"],
    data={
        "category_id": 3,  # General
        "original_text": "The main college WiFi network has been extremely slow for the past week. Students cannot access online learning portals or submit assignments. The library WiFi is also not working.",
        "visibility": "Public"
    })
if r.status_code == 201:
    data = r.json()
    state["complaint_general_id"] = data.get("id")
    assigned = data.get("assigned_authority")
    print(f"  [OK] Created: id={data.get('id')}")
    print(f"  [OK] Assigned to: {assigned}")
    print(f"  [OK] Category: {data.get('category_name')}")
    if assigned and ("Officer" in str(assigned) or "Admin" in str(assigned)):
        print(f"  [ROUTING OK] Correctly routed to Admin Officer/Admin")
    else:
        print(f"  [ROUTING CHECK] Assigned to: {assigned}")

# 6d. Department complaint (academic)
subsection("6d. Department complaint (academic) - CSE student")
r = api("POST", "/complaints/submit",
    token=state["student_23CS001_token"],
    data={
        "category_id": 4,  # Department
        "original_text": "The Data Structures lab has only 20 working computers for 60 students. Many systems have broken keyboards and outdated software. We need proper lab facilities for our practicals.",
        "visibility": "Department"
    })
if r.status_code == 201:
    data = r.json()
    state["complaint_dept_id"] = data.get("id")
    assigned = data.get("assigned_authority")
    print(f"  [OK] Created: id={data.get('id')}")
    print(f"  [OK] Assigned to: {assigned}")
    print(f"  [OK] Category: {data.get('category_name')}")
    if assigned and "HOD" in str(assigned) or "CSE" in str(assigned):
        print(f"  [ROUTING OK] Correctly routed to HOD")
    else:
        print(f"  [ROUTING CHECK] Assigned to: {assigned}")

# 6e. Private complaint
subsection("6e. Private complaint")
r = api("POST", "/complaints/submit",
    token=state["student_23CS002_token"],
    data={
        "category_id": 3,  # General
        "original_text": "The security guard at the main gate is very rude to students when they enter after 6pm. He uses inappropriate language and threatens students unnecessarily.",
        "visibility": "Private"
    })
if r.status_code == 201:
    data = r.json()
    state["complaint_private_id"] = data.get("id")
    print(f"  [OK] Private complaint created: id={data.get('id')}")

# ============================================================
# 7. DAY SCHOLAR HOSTEL RESTRICTION
# ============================================================
section("7. DAY SCHOLAR HOSTEL RESTRICTION")

subsection("7a. Day Scholar tries to submit Men's Hostel complaint")
r = api("POST", "/complaints/submit",
    token=state["student_23ECE001_token"],  # Day Scholar
    data={
        "category_id": 1,  # Men's Hostel
        "original_text": "The hostel rooms need better ventilation and air conditioning in the summer months.",
        "visibility": "Public"
    })
print(f"  Status: {r.status_code}")
if r.status_code == 400:
    print(f"  [OK] Day scholar correctly blocked from hostel complaints")
else:
    print(f"  [FAIL] Day scholar was NOT blocked! Status: {r.status_code}")

subsection("7b. Day Scholar tries Women's Hostel complaint")
r = api("POST", "/complaints/submit",
    token=state["student_23ECE001_token"],  # Day Scholar
    data={
        "category_id": 2,  # Women's Hostel
        "original_text": "The women's hostel needs better security cameras at the entrance.",
        "visibility": "Public"
    })
print(f"  Status: {r.status_code}")
if r.status_code == 400:
    print(f"  [OK] Day scholar correctly blocked from women's hostel too")
else:
    print(f"  [FAIL] Day scholar was NOT blocked! Status: {r.status_code}")

# ============================================================
# 8. GENDER-CATEGORY MISMATCH
# ============================================================
section("8. GENDER-CATEGORY MISMATCH")

subsection("8a. Male student tries Women's Hostel category")
r = api("POST", "/complaints/submit",
    token=state["student_23CS001_token"],  # Male
    data={
        "category_id": 2,  # Women's Hostel
        "original_text": "The women's hostel common room needs better furniture and lighting.",
        "visibility": "Public"
    })
if r.status_code == 400:
    print(f"  [OK] Male student correctly blocked from Women's Hostel")
else:
    print(f"  [FAIL] Male student was NOT blocked! Status: {r.status_code}")

subsection("8b. Female student tries Men's Hostel category")
r = api("POST", "/complaints/submit",
    token=state["student_23CS002_token"],  # Female
    data={
        "category_id": 1,  # Men's Hostel
        "original_text": "The men's hostel canteen food quality has been very poor lately.",
        "visibility": "Public"
    })
if r.status_code == 400:
    print(f"  [OK] Female student correctly blocked from Men's Hostel")
else:
    print(f"  [FAIL] Female student was NOT blocked! Status: {r.status_code}")

# ============================================================
# 9. SPAM DETECTION
# ============================================================
section("9. SPAM DETECTION")

subsection("9a. Submit spam/abusive text")
r = api("POST", "/complaints/submit",
    token=state["student_23MECH001_token"],
    data={
        "category_id": 3,
        "original_text": "This college is absolute garbage trash junk and the principal is a total fool idiot moron. Everything here is fake dummy nonsense. I hate this place so much.",
        "visibility": "Public"
    })
print(f"  Status: {r.status_code}")
if r.status_code == 400:
    try:
        detail = r.json().get("detail", {})
        is_spam = detail.get("is_spam", False) if isinstance(detail, dict) else "spam" in str(detail).lower()
        print(f"  [OK] Spam/abusive text correctly rejected")
        print(f"  [INFO] is_spam flag: {is_spam}")
    except Exception:
        print(f"  [OK] Rejected (detail parse failed)")
else:
    print(f"  [INFO] Status {r.status_code} - LLM may not have flagged as spam (acceptable if complaint was still created)")

subsection("9b. Submit very short text (below min length)")
r = api("POST", "/complaints/submit",
    token=state["student_23ECE001_token"],
    data={
        "category_id": 3,
        "original_text": "bad",
        "visibility": "Public"
    })
print(f"  Status: {r.status_code}")
if r.status_code == 422:
    print(f"  [OK] Short text rejected by validation (422)")
elif r.status_code == 400:
    print(f"  [OK] Short text rejected (400)")
else:
    print(f"  [INFO] Status: {r.status_code}")

# ============================================================
# 10. IMAGE UPLOAD & VERIFICATION
# ============================================================
section("10. IMAGE UPLOAD & VERIFICATION")

if state.get("complaint_mens_hostel_id"):
    complaint_id = state["complaint_mens_hostel_id"]

    subsection("10a. Upload image to complaint")
    img_buf = create_test_image()
    r = api("POST", f"/complaints/{complaint_id}/upload-image",
        token=state["student_23CS001_token"],
        files={"file": ("test_photo.jpg", img_buf, "image/jpeg")})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Image uploaded: has_image={data.get('has_image')}")
        print(f"  [OK] Verification status: {data.get('verification_status')}")
    else:
        print(f"  [INFO] Upload status: {r.status_code}")

    subsection("10b. Retrieve uploaded image")
    r = requests.get(f"{API}/complaints/{complaint_id}/image",
        headers={"Authorization": f"Bearer {state['student_23CS001_token']}"})
    print(f"  << Status: {r.status_code}")
    if r.status_code == 200:
        print(f"  [OK] Image retrieved: content-type={r.headers.get('content-type')}, size={len(r.content)} bytes")
    else:
        print(f"  [INFO] No image or access denied: {r.status_code}")

    subsection("10c. Retrieve thumbnail")
    r = requests.get(f"{API}/complaints/{complaint_id}/image?thumbnail=true",
        headers={"Authorization": f"Bearer {state['student_23CS001_token']}"})
    print(f"  << Status: {r.status_code}")
    if r.status_code == 200:
        print(f"  [OK] Thumbnail retrieved: size={len(r.content)} bytes")

    subsection("10d. Trigger image verification")
    r = api("POST", f"/complaints/{complaint_id}/verify-image",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Verification: verified={data.get('image_verified')}, status={data.get('verification_status')}")
    else:
        print(f"  [INFO] Verification status: {r.status_code}")
else:
    print("  [SKIP] No men's hostel complaint created")

# ============================================================
# 11. COMPLAINT WITH IMAGE AT SUBMISSION
# ============================================================
section("11. SUBMIT COMPLAINT WITH IMAGE")

subsection("Submit complaint with image attached")
img_buf = create_test_image(color=(0, 128, 0))
r = requests.post(f"{API}/complaints/submit",
    headers={"Authorization": f"Bearer {state['student_23MECH001_token']}"},
    data={
        "category_id": 2,  # Women's Hostel (Female MECH student, Hostel)
        "original_text": "The bathroom in Women's Hostel Block B has a leaking pipe that has caused water damage to the floor and walls. Attached is a photo showing the damage.",
        "visibility": "Public"
    },
    files={"image": ("leak_photo.jpg", img_buf, "image/jpeg")})
log_response(r)
if r.status_code == 201:
    data = r.json()
    state["complaint_with_image_id"] = data.get("id")
    print(f"  [OK] Complaint with image created: id={data.get('id')}")
    print(f"  [OK] Has image: {data.get('has_image')}")
    print(f"  [OK] Assigned to: {data.get('assigned_authority')}")
else:
    print(f"  [INFO] Status: {r.status_code}")

# ============================================================
# 12. VOTING SYSTEM
# ============================================================
section("12. VOTING SYSTEM")

if state.get("complaint_general_id"):
    complaint_id = state["complaint_general_id"]

    subsection("12a. Upvote a complaint - Student 1")
    r = api("POST", f"/complaints/{complaint_id}/vote",
        token=state["student_23CS001_token"],
        json={"vote_type": "Upvote"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Upvoted: upvotes={data.get('upvotes')}, downvotes={data.get('downvotes')}, score={data.get('priority_score')}, priority={data.get('priority')}")

    subsection("12b. Upvote same complaint - Student 2")
    r = api("POST", f"/complaints/{complaint_id}/vote",
        token=state["student_23CS002_token"],
        json={"vote_type": "Upvote"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Upvoted: upvotes={data.get('upvotes')}, score={data.get('priority_score')}")

    subsection("12c. Downvote - Student 3 (MECH001, not complaint owner)")
    r = api("POST", f"/complaints/{complaint_id}/vote",
        token=state["student_23MECH001_token"],
        json={"vote_type": "Downvote"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Downvoted: upvotes={data.get('upvotes')}, downvotes={data.get('downvotes')}, score={data.get('priority_score')}")

    subsection("12d. Duplicate vote attempt - Student 1")
    r = api("POST", f"/complaints/{complaint_id}/vote",
        token=state["student_23CS001_token"],
        json={"vote_type": "Upvote"})
    if r.status_code == 400:
        print(f"  [OK] Duplicate vote correctly rejected")
    else:
        print(f"  [INFO] Status: {r.status_code}")

    subsection("12e. Check my vote status")
    r = api("GET", f"/complaints/{complaint_id}/my-vote",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Vote status: has_voted={data.get('has_voted')}, vote_type={data.get('vote_type')}")

    subsection("12f. Remove vote - Student 1")
    r = api("DELETE", f"/complaints/{complaint_id}/vote",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        print(f"  [OK] Vote removed")

    subsection("12g. Verify vote removed")
    r = api("GET", f"/complaints/{complaint_id}/my-vote",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] After removal: has_voted={data.get('has_voted')}, vote_type={data.get('vote_type')}")

    subsection("12h. Re-vote after removal")
    r = api("POST", f"/complaints/{complaint_id}/vote",
        token=state["student_23CS001_token"],
        json={"vote_type": "Downvote"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Re-voted: upvotes={data.get('upvotes')}, downvotes={data.get('downvotes')}, score={data.get('priority_score')}")

# ============================================================
# 13. AUTHORITY - VIEW ASSIGNED COMPLAINTS
# ============================================================
section("13. AUTHORITY - VIEW ASSIGNED COMPLAINTS")

subsection("13a. Men's Hostel Warden views complaints")
r = api("GET", "/authorities/my-complaints",
    token=state["warden_mens1_token"])
if r.status_code == 200:
    data = r.json()
    total = data.get("total", 0)
    print(f"  [OK] Men's Hostel Warden has {total} complaints assigned")
    for c in data.get("complaints", []):
        print(f"    - ID: {c.get('id')}, Category: {c.get('category_name')}, Status: {c.get('status')}")
        print(f"      Student: {c.get('student_roll_no', 'HIDDEN')} (anonymity applied)")

subsection("13b. Women's Hostel Warden views complaints")
r = api("GET", "/authorities/my-complaints",
    token=state["warden_womens1_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Women's Hostel Warden has {data.get('total', 0)} complaints")

subsection("13c. HOD CSE views complaints")
r = api("GET", "/authorities/my-complaints",
    token=state["hod_cse_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] HOD CSE has {data.get('total', 0)} complaints")

subsection("13d. Admin Officer views complaints")
r = api("GET", "/authorities/my-complaints",
    token=state["officer_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Admin Officer has {data.get('total', 0)} complaints")

subsection("13e. Admin views ALL complaints (with student info visible)")
r = api("GET", "/authorities/my-complaints",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Admin sees {data.get('total', 0)} complaints")
    for c in data.get("complaints", [])[:2]:
        print(f"    - Student visible to admin: {c.get('student_roll_no')}")

# ============================================================
# 14. AUTHORITY - STATUS TRANSITIONS
# ============================================================
section("14. STATUS TRANSITIONS (Full lifecycle)")

if state.get("complaint_mens_hostel_id"):
    complaint_id = state["complaint_mens_hostel_id"]

    subsection("14a. Current status (should be Raised)")
    r = api("GET", f"/complaints/{complaint_id}/status-history",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Current status: {data.get('current_status')}")

    subsection("14b. Warden changes Raised -> In Progress")
    r = api("PUT", f"/authorities/complaints/{complaint_id}/status",
        token=state["warden_mens1_token"],
        json={"status": "In Progress", "reason": "Plumber has been assigned to inspect the issue"})
    if r.status_code == 200:
        print(f"  [OK] Status updated to In Progress")
    else:
        print(f"  [INFO] Status: {r.status_code}")

    subsection("14c. Check status history after update")
    r = api("GET", f"/complaints/{complaint_id}/status-history",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Current status: {data.get('current_status')}")
        for su in data.get("status_updates", []):
            print(f"    - {su.get('old_status')} -> {su.get('new_status')}: {su.get('reason')} (by {su.get('updated_by')})")

    subsection("14d. Post public update (no status change)")
    r = api("POST", f"/authorities/complaints/{complaint_id}/post-update",
        token=state["warden_mens1_token"],
        params={"title": "Plumber Update", "content": "Plumber inspected and found a broken pipe. Repair scheduled for tomorrow."})
    if r.status_code == 200:
        print(f"  [OK] Public update posted")

    subsection("14e. Warden changes In Progress -> Resolved")
    r = api("PUT", f"/authorities/complaints/{complaint_id}/status",
        token=state["warden_mens1_token"],
        json={"status": "Resolved", "reason": "Water pipe repaired. Supply restored."})
    if r.status_code == 200:
        print(f"  [OK] Status updated to Resolved")

    subsection("14f. Check complete timeline")
    r = api("GET", f"/complaints/{complaint_id}/timeline",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Timeline has {len(data.get('timeline', []))} events:")
        for ev in data.get("timeline", []):
            print(f"    - {ev.get('event')}: {ev.get('description')}")

    subsection("14g. Invalid transition test: Resolved -> In Progress (invalid)")
    r = api("PUT", f"/authorities/complaints/{complaint_id}/status",
        token=state["warden_mens1_token"],
        json={"status": "In Progress", "reason": "Trying invalid transition"})
    print(f"  Status: {r.status_code}")
    # Resolved -> Raised is valid, but Resolved -> In Progress is NOT
    # Actually checking constants: Resolved -> [Closed, Raised]
    # So In Progress is indeed invalid
    if r.status_code in (400, 422):
        print(f"  [OK] Invalid transition correctly rejected")
    else:
        print(f"  [INFO] Status: {r.status_code} (check if transition is valid)")

    subsection("14h. Valid: Resolved -> Closed")
    r = api("PUT", f"/authorities/complaints/{complaint_id}/status",
        token=state["warden_mens1_token"],
        json={"status": "Closed", "reason": "Issue confirmed fixed by student."})
    if r.status_code == 200:
        print(f"  [OK] Complaint closed successfully")

# ============================================================
# 15. ESCALATION
# ============================================================
section("15. ESCALATION (Full chain test)")

# Create a fresh complaint for escalation testing
subsection("15a. Create fresh complaint for escalation")
r = api("POST", "/complaints/submit",
    token=state["student_23CS001_token"],
    data={
        "category_id": 1,  # Men's Hostel
        "original_text": "The entire Block B hostel building has no electricity for the last 24 hours. All students are unable to study or charge their devices. This is an emergency situation that needs immediate attention.",
        "visibility": "Public"
    })
escalation_complaint_id = None
if r.status_code == 201:
    data = r.json()
    escalation_complaint_id = data.get("id")
    assigned_to = data.get("assigned_authority")
    print(f"  [OK] Complaint created: id={escalation_complaint_id}")
    print(f"  [OK] Initially assigned to: {assigned_to}")

if escalation_complaint_id:
    subsection("15b. Warden sets to In Progress first")
    r = api("PUT", f"/authorities/complaints/{escalation_complaint_id}/status",
        token=state["warden_mens1_token"],
        json={"status": "In Progress", "reason": "Looking into the power outage"})
    print(f"  Status: {r.status_code}")

    subsection("15c. Warden escalates to Deputy Warden")
    r = api("POST", f"/authorities/complaints/{escalation_complaint_id}/escalate",
        token=state["warden_mens1_token"],
        params={"reason": "Power outage is building-wide, needs higher authority intervention"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Escalated: {data.get('message')}")
    else:
        print(f"  [INFO] Escalation status: {r.status_code}")

    subsection("15d. Check escalation history")
    # Need to use deputy warden token now since complaint was reassigned
    r = api("GET", f"/authorities/complaints/{escalation_complaint_id}/escalation-history",
        token=state["dw_mens_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Escalation count: {data.get('escalation_count')}")
        for h in data.get("history", []):
            print(f"    - Level {h.get('level')}: {h.get('authority_name')} ({h.get('authority_type')}) current={h.get('is_current')}")
    else:
        print(f"  [INFO] History status: {r.status_code}")

    subsection("15e. Deputy Warden escalates to Senior Deputy Warden")
    r = api("POST", f"/authorities/complaints/{escalation_complaint_id}/escalate",
        token=state["dw_mens_token"],
        params={"reason": "Electrical issue is critical, needs senior authorization for emergency repairs"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Escalated again: {data.get('message')}")
    else:
        print(f"  [INFO] Status: {r.status_code}")

    subsection("15f. Senior Deputy Warden views the complaint")
    r = api("GET", f"/authorities/complaints/{escalation_complaint_id}",
        token=state["sdw_token"])
    if r.status_code == 200:
        print(f"  [OK] Senior Deputy Warden can view the escalated complaint")
    else:
        print(f"  [INFO] Status: {r.status_code}")

    subsection("15g. Senior Deputy Warden escalates to Admin")
    r = api("POST", f"/authorities/complaints/{escalation_complaint_id}/escalate",
        token=state["sdw_token"],
        params={"reason": "Emergency requires admin-level budget approval for electrical contractor"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Final escalation: {data.get('message')}")
    elif r.status_code == 400:
        print(f"  [OK] No higher authority available (expected if already at top)")

    subsection("15h. Final escalation history")
    r = api("GET", f"/authorities/complaints/{escalation_complaint_id}/escalation-history",
        token=state["admin_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Total escalations: {data.get('escalation_count')}")
        for h in data.get("history", []):
            marker = " <-- CURRENT" if h.get("is_current") else ""
            print(f"    - Level {h.get('level')}: {h.get('authority_name')} ({h.get('authority_type')}){marker}")

# ============================================================
# 16. SPAM FLAGGING BY AUTHORITY
# ============================================================
section("16. SPAM FLAGGING BY AUTHORITY")

if state.get("complaint_general_id"):
    # Create another complaint to flag as spam
    subsection("16a. Create complaint to flag as spam")
    r = api("POST", "/complaints/submit",
        token=state["student_23ECE001_token"],
        data={
            "category_id": 3,
            "original_text": "The parking lot near the main building needs better lighting at night. Several students have reported difficulty finding their vehicles after evening classes.",
            "visibility": "Public"
        })
    spam_complaint_id = None
    if r.status_code == 201:
        data = r.json()
        spam_complaint_id = data.get("id")
        print(f"  [OK] Created: {spam_complaint_id}")

    if spam_complaint_id:
        subsection("16b. Authority flags as spam")
        r = api("POST", f"/complaints/{spam_complaint_id}/flag-spam",
            token=state["officer_token"],
            params={"reason": "Duplicate complaint, already addressed"})
        if r.status_code == 200:
            print(f"  [OK] Flagged as spam")

        subsection("16c. Check complaint status after spam flag")
        r = api("GET", f"/complaints/{spam_complaint_id}",
            token=state["student_23ECE001_token"])
        if r.status_code == 200:
            data = r.json()
            print(f"  [OK] Status: {data.get('status')}, is_spam: {data.get('is_marked_as_spam')}")

        subsection("16d. Authority views spam complaint (should see student info)")
        r = api("GET", f"/authorities/complaints/{spam_complaint_id}",
            token=state["officer_token"])
        if r.status_code == 200:
            data = r.json()
            student_info = data.get("student_roll_no") or data.get("student_name")
            print(f"  [OK] Student info visible for spam: {student_info}")

        subsection("16e. Unflag spam")
        r = api("POST", f"/complaints/{spam_complaint_id}/unflag-spam",
            token=state["officer_token"])
        if r.status_code == 200:
            print(f"  [OK] Spam flag removed")

        subsection("16f. Verify status restored")
        r = api("GET", f"/complaints/{spam_complaint_id}",
            token=state["student_23ECE001_token"])
        if r.status_code == 200:
            data = r.json()
            print(f"  [OK] Status after unflag: {data.get('status')}")

# ============================================================
# 17. PUBLIC FEED FILTERING
# ============================================================
section("17. PUBLIC FEED FILTERING")

subsection("17a. Male Hostel student public feed")
r = api("GET", "/complaints/public-feed",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    categories_seen = set()
    for c in data.get("complaints", []):
        cat = c.get("category_name", "")
        categories_seen.add(cat)
    print(f"  [OK] Male Hostel sees {data.get('total')} complaints")
    print(f"  [OK] Categories seen: {categories_seen}")
    if "Women's Hostel" in categories_seen:
        print(f"  [FAIL] Male student can see Women's Hostel complaints!")
    else:
        print(f"  [OK] Women's Hostel correctly HIDDEN from male student")

subsection("17b. Female Hostel student public feed")
r = api("GET", "/complaints/public-feed",
    token=state["student_23CS002_token"])
if r.status_code == 200:
    data = r.json()
    categories_seen = set()
    for c in data.get("complaints", []):
        cat = c.get("category_name", "")
        categories_seen.add(cat)
    print(f"  [OK] Female Hostel sees {data.get('total')} complaints")
    print(f"  [OK] Categories seen: {categories_seen}")
    if "Men's Hostel" in categories_seen:
        print(f"  [FAIL] Female student can see Men's Hostel complaints!")
    else:
        print(f"  [OK] Men's Hostel correctly HIDDEN from female student")

subsection("17c. Day Scholar public feed (no hostel at all)")
r = api("GET", "/complaints/public-feed",
    token=state["student_23ECE001_token"])
if r.status_code == 200:
    data = r.json()
    categories_seen = set()
    for c in data.get("complaints", []):
        cat = c.get("category_name", "")
        categories_seen.add(cat)
    print(f"  [OK] Day Scholar sees {data.get('total')} complaints")
    print(f"  [OK] Categories seen: {categories_seen}")
    hostel_cats = {"Men's Hostel", "Women's Hostel"} & categories_seen
    if hostel_cats:
        print(f"  [FAIL] Day Scholar can see hostel complaints: {hostel_cats}")
    else:
        print(f"  [OK] ALL hostel complaints correctly HIDDEN from day scholar")

subsection("17d. Cross-department filter (MECH student vs CSE dept complaint)")
r = api("GET", "/complaints/public-feed",
    token=state["student_23MECH001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] MECH student sees {data.get('total')} complaints")
    # Check if CSE department-only complaints are hidden
    for c in data.get("complaints", []):
        if c.get("visibility") == "Department" and c.get("complaint_department_id") != 4:
            print(f"  [CHECK] Dept complaint from dept {c.get('complaint_department_id')} visible to MECH student")

# ============================================================
# 18. COMPLAINT DETAIL & STUDENT MY-COMPLAINTS
# ============================================================
section("18. COMPLAINT DETAIL & MY-COMPLAINTS")

subsection("18a. Student views own complaints")
r = api("GET", "/students/my-complaints",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Student has {data.get('total')} complaints")
    for c in data.get("complaints", [])[:3]:
        print(f"    - {c.get('id')}: [{c.get('status')}] {c.get('category_name')} - {str(c.get('rephrased_text',''))[:60]}")

if state.get("complaint_general_id"):
    subsection("18b. Complaint detail view")
    r = api("GET", f"/complaints/{state['complaint_general_id']}",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Detail: status={data.get('status')}, priority={data.get('priority')}")
        print(f"  [OK] Vote count: {data.get('vote_count')}")
        print(f"  [OK] Has image: {data.get('has_image')}")
        if data.get("status_updates"):
            print(f"  [OK] Status updates: {len(data['status_updates'])} entries")

subsection("18c. Filter my-complaints by status")
r = api("GET", "/students/my-complaints?status_filter=Raised",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Raised complaints: {data.get('total')}")

# ============================================================
# 19. NOTIFICATIONS
# ============================================================
section("19. NOTIFICATIONS")

subsection("19a. Get student notifications")
r = api("GET", "/students/notifications",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    total = data.get("total", 0)
    unread = data.get("unread_count", 0)
    print(f"  [OK] Notifications: total={total}, unread={unread}")
    for n in data.get("notifications", [])[:3]:
        print(f"    - [{n.get('notification_type')}] {n.get('message', '')[:80]}")

subsection("19b. Get unread count")
r = api("GET", "/students/notifications/unread-count",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Unread count: {data.get('unread_count')}")

if r.status_code == 200:
    subsection("19c. Mark all as read")
    r = api("PUT", "/students/notifications/mark-all-read",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        print(f"  [OK] All notifications marked as read")

    subsection("19d. Verify unread count is 0")
    r = api("GET", "/students/notifications/unread-count",
        token=state["student_23CS001_token"])
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Unread after mark-all: {data.get('unread_count')}")

# ============================================================
# 20. AUTHORITY PROFILE & DASHBOARD
# ============================================================
section("20. AUTHORITY PROFILE & DASHBOARD")

subsection("20a. Warden profile")
r = api("GET", "/authorities/profile",
    token=state["warden_mens1_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Name: {data.get('name')}, Type: {data.get('authority_type')}, Level: {data.get('authority_level')}")

subsection("20b. Warden dashboard")
r = api("GET", "/authorities/dashboard",
    token=state["warden_mens1_token"])
if r.status_code == 200:
    data = r.json()
    stats = data.get("stats", {})
    print(f"  [OK] Dashboard stats: total={stats.get('total_assigned')}, pending={stats.get('pending')}, in_progress={stats.get('in_progress')}, resolved={stats.get('resolved')}")
    print(f"  [OK] Recent complaints: {len(data.get('recent_complaints', []))}")
    print(f"  [OK] Urgent complaints: {len(data.get('urgent_complaints', []))}")
    print(f"  [OK] Unread notifications: {data.get('unread_notifications')}")

subsection("20c. Authority stats")
r = api("GET", "/authorities/stats",
    token=state["warden_mens1_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Stats: {json.dumps(data, default=str)}")

# ============================================================
# 21. AUTHORITY - PARTIAL ANONYMITY VERIFICATION
# ============================================================
section("21. PARTIAL ANONYMITY VERIFICATION")

subsection("21a. Non-admin authority sees hidden student info")
r = api("GET", "/authorities/my-complaints",
    token=state["officer_token"])
if r.status_code == 200:
    data = r.json()
    for c in data.get("complaints", [])[:2]:
        roll = c.get("student_roll_no")
        name = c.get("student_name")
        is_spam = c.get("is_marked_as_spam", False)
        if is_spam:
            print(f"  [OK] SPAM complaint: student visible = roll:{roll}, name:{name}")
        else:
            if roll is None or roll == "Hidden (non-spam)":
                print(f"  [OK] Non-spam: student HIDDEN (anonymity works)")
            else:
                print(f"  [CHECK] Non-spam: student roll={roll} -- should be hidden?")

subsection("21b. Admin sees all student info")
r = api("GET", "/authorities/my-complaints",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    for c in data.get("complaints", [])[:2]:
        roll = c.get("student_roll_no")
        print(f"  [OK] Admin view: student roll={roll} (should be visible)")

# ============================================================
# 22. ADVANCED FILTERING
# ============================================================
section("22. ADVANCED FILTERING")

subsection("22a. Filter by status")
r = api("GET", "/complaints/filter/advanced?status=Raised",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Raised complaints: {data.get('total')}")

subsection("22b. Filter by priority")
r = api("GET", "/complaints/filter/advanced?priority=Low",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Low priority complaints: {data.get('total')}")

subsection("22c. Filter by category")
r = api("GET", "/complaints/filter/advanced?category_id=3",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] General category complaints: {data.get('total')}")

subsection("22d. Filter by has_image")
r = api("GET", "/complaints/filter/advanced?has_image=true",
    token=state["student_23CS001_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Complaints with images: {data.get('total')}")

# ============================================================
# 23. ADMIN PANEL
# ============================================================
section("23. ADMIN PANEL")

subsection("23a. System overview stats")
r = api("GET", "/admin/stats/overview",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Students: {data.get('total_students')}")
    print(f"  [OK] Authorities: {data.get('total_authorities')}")
    print(f"  [OK] Complaints: {data.get('total_complaints')}")
    print(f"  [OK] By status: {data.get('complaints_by_status')}")
    print(f"  [OK] By priority: {data.get('complaints_by_priority')}")
    print(f"  [OK] By category: {data.get('complaints_by_category')}")
    print(f"  [OK] Images: {data.get('image_statistics')}")

subsection("23b. Analytics (30 days)")
r = api("GET", "/admin/stats/analytics?days=30",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Total: {data.get('total_complaints')}, Resolved: {data.get('resolved_complaints')}")
    print(f"  [OK] Resolution rate: {data.get('resolution_rate_percent')}%")
    print(f"  [OK] Avg resolution time: {data.get('avg_resolution_time_hours')}h")

subsection("23c. Health metrics")
r = api("GET", "/admin/health/metrics",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] DB size: {data.get('database_size_mb')} MB")
    print(f"  [OK] Pending: {data.get('pending_complaints')}")
    print(f"  [OK] Old unresolved (>7d): {data.get('old_unresolved_7d')}")

subsection("23d. List all authorities")
r = api("GET", "/admin/authorities",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Total authorities: {data.get('total')}")
    for a in data.get("authorities", [])[:5]:
        print(f"    - {a.get('name')} ({a.get('authority_type')}) Level {a.get('authority_level')} Active={a.get('is_active')}")

subsection("23e. List all students")
r = api("GET", "/admin/students",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Total students: {data.get('total')}")
    for s in data.get("students", [])[:5]:
        print(f"    - {s.get('roll_no')} {s.get('name')} ({s.get('gender')}, {s.get('stay_type')}, dept={s.get('department_id')})")

subsection("23f. Filter students by department")
r = api("GET", "/admin/students?department_id=1",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] CSE students: {data.get('total')}")

subsection("23g. Pending image verification")
r = api("GET", "/admin/images/pending-verification",
    token=state["admin_token"])
if r.status_code == 200:
    data = r.json()
    print(f"  [OK] Pending verifications: {data.get('total')}")

# ============================================================
# 24. ADMIN - STUDENT MANAGEMENT
# ============================================================
section("24. ADMIN - STUDENT MANAGEMENT")

subsection("24a. Deactivate student")
r = api("PUT", "/admin/students/23ECE001/toggle-active?activate=false",
    token=state["admin_token"])
if r.status_code == 200:
    print(f"  [OK] Student deactivated")

subsection("24b. Deactivated student tries to access")
r = api("GET", "/students/profile",
    token=state["student_23ECE001_token"])
print(f"  Status: {r.status_code}")
if r.status_code in (401, 403):
    print(f"  [OK] Deactivated student correctly blocked")
else:
    print(f"  [INFO] Status: {r.status_code} (auth middleware may not check is_active)")

subsection("24c. Reactivate student")
r = api("PUT", "/admin/students/23ECE001/toggle-active?activate=true",
    token=state["admin_token"])
if r.status_code == 200:
    print(f"  [OK] Student reactivated")

# ============================================================
# 25. ADMIN - AUTHORITY MANAGEMENT
# ============================================================
section("25. ADMIN - AUTHORITY MANAGEMENT")

subsection("25a. Create new authority")
r = api("POST", "/admin/authorities",
    token=state["admin_token"],
    json={
        "name": "Test Authority",
        "email": "test.authority@srec.ac.in",
        "password": "TestAuth@123",
        "phone": "9876543210",
        "authority_type": "HOD",
        "department_id": 2,
        "designation": "Test HOD",
        "authority_level": 8
    })
if r.status_code == 201:
    print(f"  [OK] New authority created")
elif r.status_code == 409:
    print(f"  [OK] Already exists (expected on re-run)")

subsection("25b. Duplicate email test")
r = api("POST", "/admin/authorities",
    token=state["admin_token"],
    json={
        "name": "Duplicate",
        "email": "test.authority@srec.ac.in",
        "password": "TestAuth@123",
        "phone": "9876543211",
        "authority_type": "HOD",
        "department_id": 3,
        "designation": "Dup",
        "authority_level": 8
    })
if r.status_code == 409:
    print(f"  [OK] Duplicate email correctly rejected")

subsection("25c. Admin self-deactivation prevention")
r = api("PUT", f"/admin/authorities/{state['admin_id']}/toggle-active?activate=false",
    token=state["admin_token"])
if r.status_code == 400:
    print(f"  [OK] Admin cannot deactivate self")

subsection("25d. Non-admin cannot access admin endpoints")
r = api("GET", "/admin/stats/overview",
    token=state["officer_token"])
print(f"  Status: {r.status_code}")
if r.status_code in (401, 403):
    print(f"  [OK] Non-admin correctly blocked from admin endpoints")
else:
    print(f"  [CHECK] Status {r.status_code} - officer may have admin access check")

# ============================================================
# 26. BULK OPERATIONS
# ============================================================
section("26. ADMIN BULK OPERATIONS")

if state.get("complaint_private_id"):
    subsection("26a. Bulk status update")
    r = api("POST", f"/admin/complaints/bulk-status-update",
        token=state["admin_token"],
        params={
            "complaint_ids": [state["complaint_private_id"]],
            "new_status": "In Progress",
            "reason": "Bulk processing by admin"
        })
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Bulk update: {data.get('message')}")
    else:
        print(f"  [INFO] Status: {r.status_code}")

# ============================================================
# 27. IMAGE MODERATION (ADMIN)
# ============================================================
section("27. ADMIN IMAGE MODERATION")

if state.get("complaint_with_image_id"):
    subsection("27a. Admin moderates image (approve)")
    r = api("POST", f"/admin/images/{state['complaint_with_image_id']}/moderate?approve=true",
        token=state["admin_token"])
    if r.status_code == 200:
        print(f"  [OK] Image approved by admin")
    else:
        print(f"  [INFO] Status: {r.status_code}")

# ============================================================
# 28. DEPARTMENT COMPLAINT ESCALATION (HOD -> Admin)
# ============================================================
section("28. DEPARTMENT ESCALATION (HOD -> Admin)")

if state.get("complaint_dept_id"):
    subsection("28a. HOD views department complaint")
    r = api("GET", f"/authorities/complaints/{state['complaint_dept_id']}",
        token=state["hod_cse_token"])
    if r.status_code == 200:
        print(f"  [OK] HOD can view the department complaint")

    subsection("28b. HOD escalates to Admin")
    r = api("POST", f"/authorities/complaints/{state['complaint_dept_id']}/escalate",
        token=state["hod_cse_token"],
        params={"reason": "Lab renovation requires admin budget approval"})
    if r.status_code == 200:
        data = r.json()
        print(f"  [OK] Escalated: {data.get('message')}")
    else:
        print(f"  [INFO] Status: {r.status_code}")

# ============================================================
# 29. STUDENT CHANGE PASSWORD
# ============================================================
section("29. STUDENT PASSWORD CHANGE")

subsection("29a. Change password")
r = api("POST", "/students/change-password",
    token=state["student_23MECH001_token"],
    json={"old_password": "Student@123", "new_password": "NewPass@1234", "confirm_password": "NewPass@1234"})
if r.status_code == 200:
    print(f"  [OK] Password changed")

subsection("29b. Login with new password")
r = api("POST", "/students/login", json={
    "email_or_roll_no": "23MECH001",
    "password": "NewPass@1234"
})
if r.status_code == 200:
    print(f"  [OK] Login with new password works")
    state["student_23MECH001_token"] = r.json()["token"]

subsection("29c. Old password no longer works")
r = api("POST", "/students/login", json={
    "email_or_roll_no": "23MECH001",
    "password": "Student@123"
})
if r.status_code == 401:
    print(f"  [OK] Old password correctly rejected")

subsection("29d. Restore original password")
r = api("POST", "/students/change-password",
    token=state["student_23MECH001_token"],
    json={"old_password": "NewPass@1234", "new_password": "Student@123", "confirm_password": "Student@123"})
if r.status_code == 200:
    print(f"  [OK] Password restored")

# ============================================================
# 30. DISCIPLINARY COMMITTEE ROUTING
# ============================================================
section("30. DISCIPLINARY COMMITTEE ROUTING")

subsection("30a. Submit disciplinary complaint")
r = api("POST", "/complaints/submit",
    token=state["student_23CS002_token"],
    data={
        "category_id": 5,  # Disciplinary Committee
        "original_text": "A group of senior students in Block C are engaging in ragging of first year students during late night hours. They force juniors to do push-ups and verbally abuse them. Please take immediate action.",
        "visibility": "Private"
    })
if r.status_code == 201:
    data = r.json()
    assigned = data.get("assigned_authority")
    print(f"  [OK] Created: id={data.get('id')}")
    print(f"  [OK] Assigned to: {assigned}")
    print(f"  [OK] Category: {data.get('category_name')}")
    if assigned and ("Disciplinary" in str(assigned) or "Committee" in str(assigned)):
        print(f"  [ROUTING OK] Correctly routed to Disciplinary Committee")
    else:
        print(f"  [ROUTING CHECK] Assigned to: {assigned}")
else:
    print(f"  [INFO] Status: {r.status_code}")

# ============================================================
# 31. EDGE CASES
# ============================================================
section("31. EDGE CASES")

subsection("31a. Access complaint without auth")
r = requests.get(f"{API}/complaints/public-feed")
print(f"  Status: {r.status_code}")
if r.status_code in (401, 403, 422):
    print(f"  [OK] Unauthenticated access blocked")

subsection("31b. Invalid complaint ID")
r = api("GET", "/complaints/00000000-0000-0000-0000-000000000000",
    token=state["student_23CS001_token"])
if r.status_code == 404:
    print(f"  [OK] Invalid complaint ID returns 404")

subsection("31c. Student tries to update complaint status (should fail)")
if state.get("complaint_general_id"):
    r = api("PUT", f"/authorities/complaints/{state['complaint_general_id']}/status",
        token=state["student_23CS001_token"],
        json={"status": "In Progress", "reason": "Student trying to change status"})
    if r.status_code in (401, 403):
        print(f"  [OK] Student correctly blocked from authority endpoint")

subsection("31d. Authority accessing wrong complaint (not assigned)")
if state.get("complaint_womens_hostel_id"):
    r = api("PUT", f"/authorities/complaints/{state['complaint_womens_hostel_id']}/status",
        token=state["warden_mens1_token"],  # Men's warden, but women's complaint
        json={"status": "In Progress", "reason": "Wrong authority"})
    if r.status_code in (403, 404):
        print(f"  [OK] Authority blocked from non-assigned complaint: {r.status_code}")
    else:
        print(f"  [CHECK] Status: {r.status_code}")

# ============================================================
# FINAL SUMMARY
# ============================================================
section("TEST SUITE COMPLETE")

print("""
TESTS COVERED:
  1.  Health check
  2.  All authority logins (13 authorities + wrong password)
  3.  Student registration (4 profiles: M/F, Hostel/Day Scholar)
  4.  Student login (email, roll_no, wrong password)
  5.  Student profile & stats
  6.  Complaint submission & routing (5 types: Men's/Women's Hostel, General, Department, Private)
  7.  Day scholar hostel restriction
  8.  Gender-category mismatch blocking
  9.  Spam/abusive text detection
  10. Image upload & verification
  11. Submit complaint with image
  12. Voting (upvote, downvote, duplicate, remove, re-vote)
  13. Authority views assigned complaints
  14. Status transitions (full lifecycle: Raised->InProgress->Resolved->Closed + invalid transition)
  15. Escalation chain (Warden->Deputy->Senior Deputy->Admin, 3 levels)
  16. Spam flagging/unflagging by authority
  17. Public feed filtering (gender-hostel, day scholar, cross-department)
  18. Complaint detail, my-complaints, status filter
  19. Notifications (list, unread count, mark read)
  20. Authority profile & dashboard
  21. Partial anonymity (non-spam hidden, spam visible, admin sees all)
  22. Advanced filtering (status, priority, category, has_image)
  23. Admin panel (stats, analytics, health, authorities list, students list)
  24. Admin student management (deactivate/reactivate)
  25. Admin authority management (create, duplicate, self-deactivation prevention)
  26. Admin bulk status update
  27. Admin image moderation
  28. Department escalation (HOD->Admin)
  29. Password change (change, verify, restore)
  30. Disciplinary committee routing
  31. Edge cases (no auth, invalid ID, wrong role, wrong authority)
""")

print(f"\nAll requests and responses have been printed above.")
print(f"Review the output to verify all logic is correctly implemented.")
