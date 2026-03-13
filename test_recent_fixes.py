"""
Test suite for recent fixes:
1. Admin students endpoint limit=200 now works (was failing with 422 due to le=100)
2. assigned_authority_name returned in public feed and my-complaints
3. Admin stats overview returns students_by_department and complaints_by_department
4. Escalations endpoint returns all three sections (escalated, critical, overdue)
"""
import requests
import json
import sys

BASE = "http://localhost:8000"
API = f"{BASE}/api"
PASS = 0
FAIL = 0


def colored(text, code):
    return f"\033[{code}m{text}\033[0m"


def ok(label, detail=""):
    global PASS
    PASS += 1
    print(colored(f"  [PASS] {label}", "32") + (f" — {detail}" if detail else ""))


def fail(label, detail=""):
    global FAIL
    FAIL += 1
    print(colored(f"  [FAIL] {label}", "31") + (f" — {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def api(method, path, token=None, **kwargs):
    url = f"{API}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.request(method, url, headers=headers, timeout=15, **kwargs)
    return r


# ─── Admin Login ──────────────────────────────────────────────
section("0. Admin Login")
r = api("POST", "/authorities/login", json={
    "email": "admin@srec.ac.in",
    "password": "Admin@123456"
})
if r.status_code == 200:
    admin_token = r.json().get("token") or r.json().get("access_token")
    ok("Admin login", f"role={r.json().get('authority_type')}")
else:
    fail("Admin login", f"status={r.status_code} body={r.text[:300]}")
    print("Cannot proceed without admin token")
    sys.exit(1)

# ─── Student Register + Login ─────────────────────────────────
section("0b. Student Setup (register + login)")
reg = api("POST", "/students/register", json={
    "roll_no": "23CS001",
    "name": "Ravi Kumar",
    "email": "ravi.kumar@srec.ac.in",
    "password": "Student@123",
    "gender": "Male",
    "stay_type": "Hostel",
    "year": 2,
    "department_id": 1
})
print(f"  Register: {reg.status_code} ({reg.json().get('error','ok') if reg.status_code != 201 else 'created'})")

r = api("POST", "/students/login", json={
    "email_or_roll_no": "ravi.kumar@srec.ac.in",
    "password": "Student@123"
})
if r.status_code == 200:
    student_token = r.json().get("token") or r.json().get("access_token")
    ok("Student login", f"roll_no={r.json().get('roll_no')}")
else:
    fail("Student login", f"status={r.status_code} body={r.text[:200]}")
    student_token = None


# ─── Test 1: Admin students limit=200 (previously failed 422) ─
section("1. Admin /admin/students?limit=200 — was 422, now should be 200")
r = api("GET", "/admin/students?limit=200&department_code=CSE", token=admin_token)
if r.status_code == 200:
    data = r.json()
    ok("limit=200 accepted", f"total={data.get('total')}, returned={len(data.get('students',[]))}")
elif r.status_code == 422:
    fail("limit=200 STILL gives 422", r.text[:200])
else:
    fail(f"Unexpected status {r.status_code}", r.text[:200])

r = api("GET", "/admin/students?limit=500", token=admin_token)
if r.status_code == 200:
    ok("limit=500 accepted")
else:
    fail(f"limit=500 gives {r.status_code}", r.text[:100])

r = api("GET", "/admin/students?limit=501", token=admin_token)
if r.status_code == 422:
    ok("limit=501 correctly rejected (>500)")
else:
    fail(f"limit=501 gives {r.status_code} — should be 422")


# ─── Test 2: Overview includes dept counts ────────────────────
section("2. Admin Overview — students_by_department & complaints_by_department")
r = api("GET", "/admin/stats/overview", token=admin_token)
if r.status_code != 200:
    fail("GET /admin/stats/overview", f"status={r.status_code}")
else:
    data = r.json()
    sbd = data.get("students_by_department")
    cbd = data.get("complaints_by_department")

    if isinstance(sbd, dict) and len(sbd) > 0:
        ok("students_by_department present", f"depts={list(sbd.keys())[:5]}, sample={dict(list(sbd.items())[:3])}")
    else:
        fail("students_by_department missing/empty", f"got: {sbd}")

    if isinstance(cbd, dict) and len(cbd) >= 0:
        ok("complaints_by_department present", f"sample={dict(list(cbd.items())[:3])}")
    else:
        fail("complaints_by_department missing", f"got: {cbd}")

    # Check CSE specifically
    if isinstance(sbd, dict) and "CSE" in sbd:
        ok(f"CSE has {sbd['CSE']} students (from sbd)")
    elif isinstance(sbd, dict):
        print(f"  INFO: departments in sbd: {list(sbd.keys())[:10]}")


# ─── Test 3: Public feed returns assigned_authority_name ──────
section("3. Public Feed — assigned_authority_name in each complaint item")
if student_token:
    r = api("GET", "/complaints/public-feed?limit=5", token=student_token)
    if r.status_code == 200:
        data = r.json()
        complaints = data.get("complaints", [])
        if not complaints:
            ok("Public feed returns 200 (no complaints yet to check fields)")
        else:
            missing = [c.get("id","?")[:8] for c in complaints if "assigned_authority_name" not in c]
            if not missing:
                vals = [c.get("assigned_authority_name") for c in complaints]
                ok("assigned_authority_name present in all public feed items", f"values={vals}")
            else:
                fail("assigned_authority_name MISSING from some complaints", f"ids={missing}")
    else:
        fail("GET /complaints/public-feed", f"status={r.status_code} {r.text[:100]}")
else:
    print("  SKIP: no student token")


# ─── Test 4: My complaints returns assigned_authority_name ────
section("4. My Complaints — assigned_authority_name field present")
if student_token:
    r = api("GET", "/students/my-complaints?limit=5", token=student_token)
    if r.status_code == 200:
        data = r.json()
        complaints = data.get("complaints", [])
        if not complaints:
            ok("GET /students/my-complaints returns 200 (no complaints yet)")
        else:
            missing = [c.get("id","?")[:8] for c in complaints if "assigned_authority_name" not in c]
            if not missing:
                ok("assigned_authority_name present in my-complaints")
            else:
                fail("assigned_authority_name missing", f"complaint ids: {missing}")
    else:
        fail("GET /students/my-complaints", f"status={r.status_code}")
else:
    print("  SKIP: no student token")


# ─── Test 5: Escalations — all three sections ─────────────────
section("5. Escalations — escalated, critical, overdue all present")
r = api("GET", "/admin/escalations", token=admin_token)
if r.status_code == 200:
    data = r.json()
    for key in ("escalated", "critical", "overdue", "summary"):
        if key in data:
            count = len(data[key]) if isinstance(data[key], list) else data[key]
            ok(f"'{key}' section present", f"value={count}")
        else:
            fail(f"'{key}' section MISSING from escalations response")
    if "summary" in data:
        s = data["summary"]
        print(f"  Summary: escalated={s.get('escalated_count',0)}, "
              f"critical={s.get('critical_count',0)}, overdue={s.get('overdue_count',0)}")
else:
    fail("GET /admin/escalations", f"status={r.status_code} {r.text[:300]}")


# ─── Test 6: Admin complaints list ────────────────────────────
section("6. Admin Complaints — basic functionality")
r = api("GET", "/admin/complaints?limit=5", token=admin_token)
if r.status_code == 200:
    data = r.json()
    complaints = data.get("complaints", [])
    ok("GET /admin/complaints", f"total={data.get('total')}, returned={len(complaints)}")
    if complaints:
        sample = complaints[0]
        if "assigned_authority_name" in sample:
            ok("assigned_authority_name present in admin complaint view")
        else:
            print("  INFO: assigned_authority_name not in admin complaints (uses different field)")
else:
    fail("GET /admin/complaints", f"status={r.status_code}")


# ─── Test 7: Department detail students (tests limit fix) ──────
section("7. Department detail — student count via dept filter (limit=200)")
r = api("GET", "/admin/students?limit=200&department_code=CSE", token=admin_token)
if r.status_code == 200:
    data = r.json()
    total = data.get("total", 0)
    returned = len(data.get("students", []))
    ok(f"CSE students loaded successfully", f"total={total}, returned={returned}")
    if total > 0:
        ok("CSE has students (dept detail page will show correct count)")
    else:
        print("  INFO: No CSE students in DB yet")
else:
    fail("Dept filter students", f"status={r.status_code}")


# ─── Summary ──────────────────────────────────────────────────
print(f"\n{'='*60}")
total_tests = PASS + FAIL
print(f"  Results: {colored(str(PASS)+' passed', '32')}  "
      f"{colored(str(FAIL)+' failed', '31' if FAIL else '32')}  "
      f"/ {total_tests} total")
print(f"{'='*60}")
sys.exit(0 if FAIL == 0 else 1)
