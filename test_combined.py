#!/usr/bin/env python3
"""
CampusVoice — Combined Test Suite
====================================
Merges test_comprehensive.py (~247 TCs, 32 sections) and
test_llm_routing.py (~181 TCs, 12 sections) into one unified script.

43 sections  |  ~428 TCs  |  Estimated runtime: 25–35 minutes
Target  : https://campusvoice-api-h528.onrender.com
Log     : combined_YYYYMMDD_HHMMSS.log
Run     : python test_combined.py
"""

import requests
import json
import time
import datetime
import os
import sys
import struct
import zlib
from typing import Optional, Any, Tuple

# ════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

BASE_URL       = "https://campusvoice-api-h528.onrender.com"
TIMEOUT        = 120
CD_LLM         = 40   # wait after every LLM complaint submission (Render is slow)
CD_WRITE       = 5    # after state-changing non-LLM ops
CD_AUTH        = 3    # after login / register
CD_READ        = 2    # after read-only GETs
PASS_THRESHOLD = 80   # overall threshold (LLM sections can have occasional misclassifications)

# ════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ════════════════════════════════════════════════════════════════════════════

RUN_TS    = str(int(time.time()))[-5:]
NOW_STR   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE  = f"combined_{NOW_STR}.log"
CRED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.txt")

_log_fh = open(LOG_FILE, "w", encoding="utf-8", buffering=1)

def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")

def log(msg: str = ""):
    try:
        print(msg)
    except (UnicodeEncodeError, UnicodeDecodeError):
        print(msg.encode("ascii", "replace").decode("ascii"))
    _log_fh.write(msg + "\n")

def logf(msg: str = ""):
    _log_fh.write(msg + "\n")

def pause(seconds: float, reason: str = ""):
    seconds = min(float(seconds), 60)
    msg = f"\n  [wait {_now()}] Pausing {seconds:.0f}s" + (f" — {reason}" if reason else "")
    log(msg)
    time.sleep(seconds)

# ════════════════════════════════════════════════════════════════════════════
#  PNG HELPER
# ════════════════════════════════════════════════════════════════════════════

def make_valid_png(width: int = 10, height: int = 10) -> bytes:
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

# ════════════════════════════════════════════════════════════════════════════
#  COMPLAINT TEXTS (from test_llm_routing.py — unambiguous, real-world)
# ════════════════════════════════════════════════════════════════════════════

MH_TEXTS = [
    "The water supply in Block-A men's hostel room 204 has been completely cut off for 3 days. "
    "We cannot shower or use the toilets. Despite informing the hostel watchman, no action has been taken.",

    "The cleaning staff for men's hostel Block-A has not reported for duty for the past eight days. "
    "Despite repeated complaints submitted to the hostel watchman's register, no replacement staff has been assigned.",

    "The ceiling fan in my men's hostel room (Block B, Room 312) stopped working 5 days ago. "
    "The hostel maintenance register complaint has not been addressed yet.",

    "The men's hostel mess is repeatedly serving stale food. This morning's breakfast had spoilt "
    "sambar and the rice at lunch had an unusual smell. Several students felt unwell afterwards.",

    "The night security staff at Block C men's hostel has been absent during late hours multiple times this week. "
    "Unauthorized persons have been noticed entering the hostel after 11 PM without being stopped or registered.",
]

WH_TEXTS = [
    "All three washing machines in the women's hostel laundry room have been non-functional for "
    "10 days. Residents are unable to wash clothes and the management has not arranged a repair.",

    "The women's hostel authorities changed the hot water availability schedule without any notice. "
    "Hot water is now only available between 5-6 AM, making it impossible for students with early morning classes to bathe properly.",

    "The women's hostel management has not assigned any staff for night corridor duty on the 2nd floor since last week. "
    "Students returning late from the library have to navigate the wing without supervision, creating a safety concern.",

    "Rats have been sighted repeatedly in the women's hostel storeroom near the kitchen. This is "
    "a major hygiene risk and students are afraid to store food in their rooms.",

    "The women's hostel common room TV and cable connection have stopped working for 3 days. "
    "We use it for relaxation and news updates. Please send a technician for repairs.",
]

GEN_TEXTS = [
    "The campus WiFi network has been extremely slow and dropping connections for the past week. "
    "Streaming lectures and submitting online assignments is nearly impossible for all students.",

    "The main college library does not have adequate seating during exam season. During peak "
    "hours, over 40 students are standing or sitting on the floor because all chairs are occupied.",

    "The outdoor sports courts have been closed by administration for over two weeks without any notice or timeline for reopening. "
    "Students who rely on them for physical exercise during free periods have no alternative facilities available.",

    "The main campus canteen has not displayed a valid food hygiene or FSSAI certification for several months. "
    "Multiple students reported stomach issues after eating there on Tuesday and we are concerned about food safety compliance.",

    "Several streetlights on the main campus road between the admin block and the library have "
    "not been working for over two weeks. Night walks after library closing time are dangerous.",
]

CSE_DEPT_TEXTS = [
    "Fifteen out of thirty computers in CSE Lab 3 (2nd floor, main block) are non-functional due "
    "to hardware failures. Programming practicals for CS301 are severely disrupted this week.",

    "The IntelliJ IDEA and PyCharm software licenses in the CSE department lab expired last "
    "month. Students cannot use professional IDE features required for their semester projects.",

    "The laser printer in the CSE department office has been out of order for two weeks. "
    "We are unable to print lab observation books and project reports as mandated by faculty.",
]

ECE_DEPT_TEXTS = [
    "Four out of eight oscilloscopes in ECE Electronics Lab 2 show erratic readings and are "
    "clearly uncalibrated. Students are submitting incorrect lab records due to faulty equipment.",

    "The PCB etching equipment and soldering stations in ECE fabrication lab have not been "
    "serviced this semester. Several stations are non-operational and lab batches are delayed.",
]

DC_TEXTS = [
    "I am formally reporting a ragging incident during my first week. Senior students from "
    "2nd year forcibly made me perform humiliating tasks in the hostel corridor late at night.",

    "A group of classmates has been systematically bullying me by spreading false rumours, "
    "isolating me from group projects, and making derogatory remarks about my academic performance.",

    "I witnessed a violent physical altercation between two students near the library building "
    "yesterday at 4 PM. This kind of violent behaviour is unacceptable and must be investigated.",

    "I am being targeted on social media by fellow students. They are sharing morphed photos "
    "of me with offensive captions in class group chats. I request strict disciplinary action.",

    "A student in my batch has been caught cheating in three internal exams using hidden cheat "
    "sheets. This repeated academic dishonesty is unfair to honest students and must be penalised.",
]

UPDATE_TEST_TEXT = (
    "The projector in CSE Seminar Hall (3rd floor, main academic block) has not been working "
    "for over a week. Multiple faculty lectures and student presentations have been disrupted. "
    "The AV technician has been informed twice but no repair has been carried out."
)

EDGE_HOSTEL_FROM_DAY_SCHOLAR = (
    "The hostel AC unit in room 105 is broken and making a loud noise all night. "
    "Students residing there cannot sleep properly and need it repaired urgently."
)
EDGE_AMBIGUOUS = (
    "There is excessive noise near our study area every evening due to construction work. "
    "This is affecting our ability to concentrate and study for upcoming semester exams."
)
EDGE_CROSS_DEPT = (
    "As an ECE student working on my final-year project, I need access to the CSE department's "
    "server room and computing cluster. Despite sending requests to the CSE lab in-charge three "
    "times, no access has been granted and my project submission date is approaching."
)
EDGE_MALE_WOMENS_HOSTEL = (
    "The women's hostel laundry machines are broken. My sister is a student here and she told "
    "me about the problem. Can the management please fix the washing machines in the women's block?"
)
EDGE_RAGGING_GENERAL_PHRASING = (
    "Some seniors are pressurising juniors to perform tasks against their will. "
    "This is happening regularly in the campus corridors and needs immediate attention."
)

# ════════════════════════════════════════════════════════════════════════════
#  TEST COUNTERS & SHARED STATE
# ════════════════════════════════════════════════════════════════════════════

test_num = section_num = passed = failed = skipped = 0
failures: list = []
S: dict = {}
TS = RUN_TS

# ── Comprehensive test users (prefix 99) ──────────────────────────────────
S["s1_roll"]  = f"99CS{TS}"         ; S["s1_email"]  = f"test_s1_{TS}@srec.ac.in"
S["s2_roll"]  = f"99CS{int(TS)+1}"  ; S["s2_email"]  = f"test_s2_{TS}@srec.ac.in"
S["s3_roll"]  = f"99EC{TS}"         ; S["s3_email"]  = f"test_s3_{TS}@srec.ac.in"
S["s4_roll"]  = f"99ME{TS}"         ; S["s4_email"]  = f"test_s4_{TS}@srec.ac.in"
S["new_auth_email"] = f"test_auth_{TS}@srec.ac.in"
COMP_PWD = "Test@1234"

# ── LLM routing test users (prefix L) ────────────────────────────────────
S["mh_roll"]  = f"LMH{TS}"   ; S["mh_email"]  = f"lmh{TS}@srec.ac.in"
S["wh_roll"]  = f"LWH{TS}"   ; S["wh_email"]  = f"lwh{TS}@srec.ac.in"
S["gen_roll"] = f"LGN{TS}"   ; S["gen_email"] = f"lgn{TS}@srec.ac.in"
S["cse_roll"] = f"LCSE{TS}"  ; S["cse_email"] = f"lcse{TS}@srec.ac.in"
S["ece_roll"] = f"LECE{TS}"  ; S["ece_email"] = f"lece{TS}@srec.ac.in"
S["dc_roll"]  = f"LDC{TS}"   ; S["dc_email"]  = f"ldc{TS}@srec.ac.in"
S["obs_roll"] = f"LOBS{TS}"  ; S["obs_email"] = f"lobs{TS}@srec.ac.in"
S["upd_roll"] = f"LUPD{TS}"  ; S["upd_email"] = f"lupd{TS}@srec.ac.in"
S["edg_roll"] = f"LEDG{TS}"  ; S["edg_email"] = f"ledg{TS}@srec.ac.in"
LLM_PWD = "LLMTest@1234"

# ── Null-initialize all IDs / tokens ─────────────────────────────────────
for _k in (
    "tok_s1","tok_s2","tok_s3","tok_s4",
    "tok_admin","tok_officer","tok_warden_m","tok_warden_w",
    "tok_hod_cse","tok_hod_ece","tok_dc","tok_sdw",
    "tok_s_mh","tok_s_wh","tok_s_gen","tok_s_cse",
    "tok_s_ece","tok_s_dc","tok_s_obs","tok_s_upd","tok_s_edg",
    "cid_s1","cid_s2","cid_s1_dept","cid_s1_gen","cid_s3",
    "notif_id","new_authority_id",
    "mh_cid","wh_cid","gen_cid","dc_cid","upd_cid",
    "notice_id_mh","notice_id_wh","notice_id_admin","notice_id_hod",
):
    S[_k] = None

# ── Authority credentials ─────────────────────────────────────────────────
AUTH_CREDS = {
    "admin":    ("admin@srec.ac.in",          "Admin@123456"),
    "officer":  ("officer@srec.ac.in",         "Officer@1234"),
    "dc":       ("dc@srec.ac.in",              "Discip@12345"),
    "sdw":      ("sdw@srec.ac.in",             "SeniorDW@123"),
    "warden_m": ("warden1.mens@srec.ac.in",    "MensW1@1234"),
    "warden_w": ("warden1.womens@srec.ac.in",  "WomensW1@123"),
    "hod_cse":  ("hod.cse@srec.ac.in",         "HodCSE@123"),
    "hod_ece":  ("hod.ece@srec.ac.in",         "HodECE@123"),
}

CAT_IDS = {
    "Men's Hostel": 1, "Women's Hostel": 2, "General": 3,
    "Department": 4, "Disciplinary Committee": 5,
}

# ════════════════════════════════════════════════════════════════════════════
#  HTTP HELPERS
# ════════════════════════════════════════════════════════════════════════════

def req(method: str, path: str,
        token: str = None,
        json_data: dict = None,
        form_data: dict = None,
        files: dict = None,
        params: dict = None) -> Tuple[Optional[int], Any]:
    url     = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    logf(f"\n{'─'*60}")
    logf(f"[{_now()}] >>> {method} {url}")
    logf(f"    Params : {json.dumps(params, default=str) if params else 'none'}")
    if json_data  is not None: logf(f"    Body   : {json.dumps(json_data, default=str)}")
    if form_data  is not None: logf(f"    Form   : {json.dumps(form_data, default=str)}")
    if files:                  logf(f"    Files  : {list(files.keys())}")
    if token:                  logf(f"    Auth   : Bearer ***{token[-12:]}")

    t0 = time.time()
    try:
        kw = dict(headers=headers, timeout=TIMEOUT)
        if params: kw["params"] = params
        if   method == "GET":    r = requests.get(url, **kw)
        elif method == "POST":
            if files:                      r = requests.post(url, data=form_data or {}, files=files, **kw)
            elif form_data is not None:    r = requests.post(url, data=form_data, **kw)
            else:                          r = requests.post(url, json=json_data, **kw)
        elif method == "PUT":
            kw2 = dict(headers=headers, timeout=TIMEOUT)
            if params: kw2["params"] = params
            r = requests.put(url, json=json_data, **kw2) if json_data is not None else requests.put(url, **kw2)
        elif method == "DELETE": r = requests.delete(url, **kw)
        elif method == "PATCH":  r = requests.patch(url, json=json_data, **kw)
        else:                    return None, None

        elapsed = time.time() - t0
        try:    body = r.json()
        except: body = r.text
        logf(f"[{_now()}] <<< {r.status_code}  ({elapsed:.2f}s)")
        body_str = json.dumps(body, default=str, indent=2) if isinstance(body, (dict, list)) else str(body)
        logf(f"    Response body:\n{body_str[:5000]}")
        return r.status_code, body

    except Exception as e:
        elapsed = time.time() - t0
        logf(f"[{_now()}] <<< ERROR ({elapsed:.2f}s): {e}")
        log(f"  [err] {method} {path} failed: {e}")
        return None, str(e)


def login_student(identifier: str, pwd: str = COMP_PWD) -> Optional[str]:
    sc, body = req("POST", "/api/students/login",
                   json_data={"email_or_roll_no": identifier, "password": pwd})
    if sc == 200 and isinstance(body, dict):
        return body.get("token") or (body.get("data") or {}).get("token")
    return None


def login_authority(email: str, pwd: str) -> Optional[str]:
    sc, body = req("POST", "/api/authorities/login",
                   json_data={"email": email, "password": pwd})
    if sc == 200 and isinstance(body, dict):
        return body.get("token") or (body.get("data") or {}).get("token")
    return None


def register_student(roll: str, name: str, email: str,
                     gender: str, stay: str, dept_id: int,
                     year: int = 2, pwd: str = LLM_PWD) -> int:
    sc, _ = req("POST", "/api/students/register", json_data={
        "roll_no": roll, "name": name, "email": email,
        "password": pwd, "gender": gender,
        "stay_type": stay, "department_id": dept_id, "year": year,
    })
    return sc or 0


def submit_complaint(token: str, text: str,
                     visibility: str = "Public") -> Tuple[int, dict]:
    """Submit via multipart form with LLM wait. Returns (status_code, body)."""
    sc, body = req("POST", "/api/complaints/submit",
                   form_data={"original_text": text, "visibility": visibility},
                   files={"_": ("", b"", "text/plain")},
                   token=token)
    pause(CD_LLM, "waiting for LLM categorisation")
    if isinstance(body, dict):
        return sc or 0, body
    return sc or 0, {}


def get_field(body: dict, *keys):
    for k in keys:
        v = body.get(k)
        if v is not None:
            return v
    return None

# ════════════════════════════════════════════════════════════════════════════
#  TEST HARNESS
# ════════════════════════════════════════════════════════════════════════════

def section(name: str):
    global section_num
    section_num += 1
    bar = "=" * 72
    log(f"\n{bar}")
    log(f"  SECTION {section_num:02d}: {name}")
    log(f"{bar}")
    logf(f"[{_now()}] ── SECTION {section_num:02d}: {name} ──")


def T(name: str, condition: bool, detail: str = ""):
    global test_num, passed, failed
    test_num += 1
    if condition:
        passed += 1
        log(f"  [+] T{test_num:03d}: {name}")
        logf(f"[{_now()}] PASS T{test_num:03d}: {name}")
    else:
        failed += 1
        log(f"  [!] T{test_num:03d}: FAIL: {name}")
        if detail:
            log(f"         {detail}")
        failures.append(f"T{test_num:03d}: {name} | {detail}")
        logf(f"[{_now()}] FAIL T{test_num:03d}: {name} | {detail}")


def SKIP(name: str, reason: str = ""):
    global test_num, skipped
    test_num += 1
    skipped += 1
    msg = f"  [-] T{test_num:03d}: SKIP: {name}" + (f" ({reason})" if reason else "")
    log(msg)
    logf(f"[{_now()}] SKIP T{test_num:03d}: {name}")


def check_submission(label: str, sc: int, body: dict,
                     expected_cat: str, check_dept_code: str = None):
    """Assert 3 standard TCs for each LLM complaint submission."""
    T(f"{label} — submission accepted (200/201)",
      sc in (200, 201), f"got {sc}")

    cat = get_field(body, "category")
    T(f"{label} — categorised as '{expected_cat}'",
      cat == expected_cat, f"got category={cat!r}")

    auth = get_field(body, "assigned_authority")
    T(f"{label} — assigned to an authority",
      bool(auth), f"assigned_authority={auth!r}")

    if check_dept_code:
        dept_code = get_field(body, "target_department_code")
        T(f"{label} — routed to {check_dept_code} department",
          dept_code == check_dept_code or
          (auth and check_dept_code.lower() in str(auth).lower()),
          f"dept_code={dept_code!r}, authority={auth!r}")


def append_credentials(students: list):
    lines = [
        "",
        "=" * 80,
        f"  COMBINED TEST STUDENTS  (Run: {NOW_STR} | Suffix: {RUN_TS})",
        "=" * 80,
        f"  Comprehensive pwd: {COMP_PWD}   |   LLM pwd: {LLM_PWD}",
        "",
    ]
    for s in students:
        lines.append(
            f"  {s['roll']:12} | {s['email']:40} | {s['gender']:7} | "
            f"{s['stay']:12} | dept={s['dept']} | pwd={s.get('pwd', LLM_PWD)} | {s['label']}"
        )
    lines.append("")
    with open(CRED_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"\n  [info] Appended {len(students)} new students to {os.path.basename(CRED_FILE)}")


# ════════════════════════════════════════════════════════════════════════════
#  BANNER + WARM-UP
# ════════════════════════════════════════════════════════════════════════════

log("=" * 72)
log("  CampusVoice — Combined Test Suite  (Comprehensive + LLM Routing)")
log(f"  Target  : {BASE_URL}")
log(f"  Log     : {LOG_FILE}")
log(f"  Suffix  : {RUN_TS}")
log(f"  Started : {_now()}")
log("=" * 72)

log("\n[WAKE-UP] Pinging server...")
try:
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/health", timeout=90)
    log(f"[WAKE-UP] HTTP {r.status_code} in {time.time()-t0:.1f}s")
except Exception as e:
    log(f"[WAKE-UP] Warning: {e}")
pause(5, "server stabilise")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 01 — HEALTH ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
section("HEALTH ENDPOINTS")

sc, body = req("GET", "/health")
T("GET /health -> 200", sc == 200, f"got {sc}")
T("health body has 'status' field", isinstance(body, dict) and "status" in body, str(body)[:120])
T("health status is 'healthy'", isinstance(body, dict) and body.get("status") == "healthy", str(body)[:120])

sc, body = req("GET", "/health/detailed")
T("GET /health/detailed -> 200", sc == 200, f"got {sc}")
T("detailed health has 'database' key",
  isinstance(body, dict) and ("database" in body or "db" in body or "database" in str(body)),
  str(body)[:120])

sc, body = req("GET", "/health/ready")
T("GET /health/ready -> 200 or 503", sc in (200, 503), f"got {sc}")

sc, body = req("GET", "/health/live")
T("GET /health/live -> 200", sc == 200, f"got {sc}")

sc, body = req("GET", "/health/startup")
T("GET /health/startup -> 200", sc == 200, f"got {sc}")

sc, body = req("GET", "/metrics")
T("GET /metrics -> 200", sc == 200, f"got {sc}")
T("metrics has student count",
  isinstance(body, dict) and ("student_count" in body or "total_students" in str(body)),
  str(body)[:120])

sc, body = req("GET", "/ping")
T("GET /ping -> 200", sc == 200, f"got {sc}")
T("ping has 'pong' or 'status'",
  isinstance(body, dict) and ("pong" in body or "status" in body), str(body)[:80])

sc, body = req("GET", "/health", token="invalid_token")
T("GET /health ignores bad token (still 200)", sc == 200, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 02 — AUTHORITY LOGINS
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY LOGINS")

for key, (email, pwd) in AUTH_CREDS.items():
    tok = login_authority(email, pwd)
    S[f"tok_{key}"] = tok
    T(f"{key} ({email}) login", tok is not None, "got None")
    pause(CD_AUTH)

# Wrong password
sc, body = req("POST", "/api/authorities/login",
               json_data={"email": "admin@srec.ac.in", "password": "Wrong@999"})
T("Authority wrong password -> 401", sc == 401, f"got {sc}")

# Non-existent authority
sc, body = req("POST", "/api/authorities/login",
               json_data={"email": f"fake_{TS}@srec.ac.in", "password": "Test@1234"})
T("Non-existent authority -> 401/404", sc in (401, 404), f"got {sc}")

# Student email used on authority login endpoint (using a pre-registered student if possible)
sc, body = req("POST", "/api/authorities/login",
               json_data={"email": S["s1_email"], "password": "Test@1234"})
T("Non-authority email on authority login -> 401/403/404", sc in (401, 403, 404), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 03 — COMPREHENSIVE STUDENT REGISTRATION + VALIDATION
# ════════════════════════════════════════════════════════════════════════════
section("COMPREHENSIVE STUDENT REGISTRATION + VALIDATION")

# Register s1: Male, CSE, Hostel
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s1_roll"], "email": S["s1_email"], "password": COMP_PWD,
    "name": "Test Student One", "department_id": 1,
    "year": 2, "gender": "Male", "stay_type": "Hostel"
})
T("Register s1 (Male, CSE, Hostel) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")
pause(CD_AUTH)

# Register s2: Female, CSE, Hostel
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s2_roll"], "email": S["s2_email"], "password": COMP_PWD,
    "name": "Test Student Two", "department_id": 1,
    "year": 2, "gender": "Female", "stay_type": "Hostel"
})
T("Register s2 (Female, CSE, Hostel) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")
pause(CD_AUTH)

# Register s3: Male, ECE, Day Scholar
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s3_roll"], "email": S["s3_email"], "password": COMP_PWD,
    "name": "Test Student Three", "department_id": 2,
    "year": 3, "gender": "Male", "stay_type": "Day Scholar"
})
T("Register s3 (Male, ECE, Day Scholar) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")
pause(CD_AUTH)

# Register s4: Female, MECH, Hostel
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s4_roll"], "email": S["s4_email"], "password": COMP_PWD,
    "name": "Test Student Four", "department_id": 4,
    "year": 1, "gender": "Female", "stay_type": "Hostel"
})
T("Register s4 (Female, MECH, Hostel) -> 201", sc == 201, f"got {sc}: {str(body)[:120]}")
pause(CD_AUTH)

# Duplicate roll_no
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": S["s1_roll"], "email": f"different_{TS}@srec.ac.in",
    "password": COMP_PWD, "name": "Duplicate Roll",
    "department_id": 1, "year": 1, "gender": "Male", "stay_type": "Day Scholar"
})
T("Duplicate roll_no -> 400/409", sc in (400, 409), f"got {sc}: {str(body)[:80]}")

# Duplicate email
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99ZZ{TS}", "email": S["s1_email"],
    "password": COMP_PWD, "name": "Duplicate Email",
    "department_id": 1, "year": 1, "gender": "Male", "stay_type": "Day Scholar"
})
T("Duplicate email -> 400/409", sc in (400, 409), f"got {sc}: {str(body)[:80]}")

# Invalid email domain
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99AA{TS}", "email": f"test_{TS}@gmail.com",
    "password": COMP_PWD, "name": "Wrong Domain",
    "department_id": 1, "year": 1, "gender": "Male", "stay_type": "Day Scholar"
})
T("Wrong email domain -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# Invalid password (too simple)
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99BB{TS}", "email": f"pass_{TS}@srec.ac.in",
    "password": "short", "name": "Weak Password",
    "department_id": 1, "year": 1, "gender": "Male", "stay_type": "Day Scholar"
})
T("Weak password -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# Missing required fields
sc, body = req("POST", "/api/students/register",
               json_data={"roll_no": f"99CC{TS}", "password": COMP_PWD})
T("Missing fields -> 400/422", sc in (400, 422), f"got {sc}")

# Invalid department_id
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99DD{TS}", "email": f"dept_{TS}@srec.ac.in",
    "password": COMP_PWD, "name": "Bad Dept",
    "department_id": 9999, "year": 1, "gender": "Male", "stay_type": "Day Scholar"
})
T("Invalid department_id -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# Year out of range
sc, body = req("POST", "/api/students/register", json_data={
    "roll_no": f"99EE{TS}", "email": f"year_{TS}@srec.ac.in",
    "password": COMP_PWD, "name": "Bad Year",
    "department_id": 1, "year": 11, "gender": "Male", "stay_type": "Day Scholar"
})
T("Year > 10 -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 04 — STUDENT LOGIN (COMPREHENSIVE)
# ════════════════════════════════════════════════════════════════════════════
section("STUDENT LOGIN — COMPREHENSIVE")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s1_email"], "password": COMP_PWD})
T("s1 login by email -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
if sc == 200 and isinstance(body, dict):
    S["tok_s1"] = body.get("token") or body.get("data", {}).get("token")
T("s1 login returns token", bool(S["tok_s1"]), "no token in response")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s1_roll"], "password": COMP_PWD})
T("s1 login by roll_no -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s2_email"], "password": COMP_PWD})
T("s2 login -> 200", sc == 200, f"got {sc}")
if sc == 200 and isinstance(body, dict):
    S["tok_s2"] = body.get("token") or body.get("data", {}).get("token")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s3_email"], "password": COMP_PWD})
T("s3 login -> 200", sc == 200, f"got {sc}")
if sc == 200 and isinstance(body, dict):
    S["tok_s3"] = body.get("token") or body.get("data", {}).get("token")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s4_email"], "password": COMP_PWD})
T("s4 login -> 200", sc == 200, f"got {sc}")
if sc == 200 and isinstance(body, dict):
    S["tok_s4"] = body.get("token") or body.get("data", {}).get("token")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s1_email"], "password": "WrongPass@999"})
T("Wrong password -> 401", sc == 401, f"got {sc}")

sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": f"nobody_{TS}@srec.ac.in", "password": COMP_PWD})
T("Non-existent student -> 401/404", sc in (401, 404), f"got {sc}")

sc, body = req("POST", "/api/students/login", json_data={})
T("Empty login body -> 400/422", sc in (400, 422), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 05 — STUDENT PROFILE
# ════════════════════════════════════════════════════════════════════════════
section("STUDENT PROFILE")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/profile", token=S["tok_s1"])
    T("GET /profile with valid token -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("profile has roll_no", isinstance(body, dict) and "roll_no" in str(body), str(body)[:120])

    sc, body = req("PUT", "/api/students/profile", token=S["tok_s1"],
                   json_data={"name": "Test One Updated"})
    T("PUT /profile update name -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("PUT", "/api/students/profile", token=S["tok_s1"],
                   json_data={"year": 0})
    T("PUT /profile year=0 -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", "/api/students/change-password", token=S["tok_s1"],
                   json_data={"old_password": COMP_PWD,
                              "new_password": "NewTest@1234",
                              "confirm_password": "NewTest@1234"})
    T("Change password (valid) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    # Change back
    sc, _ = req("POST", "/api/students/change-password", token=S["tok_s1"],
                json_data={"old_password": "NewTest@1234",
                           "new_password": COMP_PWD,
                           "confirm_password": COMP_PWD})
    T("Change password back -> 200", sc == 200, f"got {sc}")

    sc, body = req("POST", "/api/students/change-password", token=S["tok_s1"],
                   json_data={"old_password": "WrongOld@999",
                              "new_password": "New@9876543",
                              "confirm_password": "New@9876543"})
    T("Change password wrong old -> 400/401", sc in (400, 401), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", "/api/students/change-password", token=S["tok_s1"],
                   json_data={"old_password": COMP_PWD, "new_password": "weak",
                              "confirm_password": "weak"})
    T("Change password weak new -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")
else:
    for _ in range(6): SKIP("Profile test", "tok_s1 missing")

sc, body = req("GET", "/api/students/profile")
T("GET /profile without token -> 401", sc == 401, f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/students/profile", token=S["tok_admin"])
    T("Authority token on student profile -> 401/403", sc in (401, 403), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 06 — STUDENT STATS
# ════════════════════════════════════════════════════════════════════════════
section("STUDENT STATS")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/stats", token=S["tok_s1"])
    T("GET /students/stats -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("stats has total_complaints",
      isinstance(body, dict) and "total_complaints" in str(body), str(body)[:120])
else:
    SKIP("Stats (tok_s1 missing)")

sc, body = req("GET", "/api/students/stats")
T("GET /students/stats without token -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 07 — COMPLAINT SUBMISSION (COMPREHENSIVE)
# ════════════════════════════════════════════════════════════════════════════
section("COMPLAINT SUBMISSION — COMPREHENSIVE")

log("  [info] Submitting complaints via LLM (each waits ~40s on Render)...")

# s1 hostel complaint
if S["tok_s1"]:
    sc, body = submit_complaint(S["tok_s1"],
        "The water supply in my hostel room has been disrupted for 3 days. "
        "The taps are completely dry and I cannot take a shower.")
    T("s1 hostel complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201):
        data = body.get("data", body)
        S["cid_s1"] = data.get("id") or data.get("complaint_id")
    T("s1 complaint returns ID", bool(S["cid_s1"]), str(body)[:80])

# s2 women's hostel complaint
if S["tok_s2"]:
    sc, body = submit_complaint(S["tok_s2"],
        "The washing machines in the women's hostel laundry room "
        "have been out of service for two weeks. Residents cannot "
        "do their laundry and this is causing significant inconvenience.")
    T("s2 women's hostel complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201):
        data = body.get("data", body)
        S["cid_s2"] = data.get("id") or data.get("complaint_id")

# s1 dept complaint
if S["tok_s1"]:
    sc, body = submit_complaint(S["tok_s1"],
        "The Computer Science lab projector has been malfunctioning "
        "during every lecture. Students are unable to see the slides.")
    T("s1 dept complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201):
        data = body.get("data", body)
        S["cid_s1_dept"] = data.get("id") or data.get("complaint_id")

# s3 general complaint
if S["tok_s3"]:
    sc, body = submit_complaint(S["tok_s3"],
        "The drinking water dispenser near the main entrance "
        "has been out of order for 5 days.")
    T("s3 general complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201):
        data = body.get("data", body)
        S["cid_s3"] = data.get("id") or data.get("complaint_id")

# s1 general complaint (for voting tests)
if S["tok_s1"]:
    sc, body = submit_complaint(S["tok_s1"],
        "The campus wifi has been very slow for the past week. "
        "Downloads are impossibly slow and online exams are at risk.")
    T("s1 general complaint (for voting) -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:120]}")
    if sc in (200, 201):
        data = body.get("data", body)
        S["cid_s1_gen"] = data.get("id") or data.get("complaint_id")

# Submit without authentication
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "No auth complaint", "visibility": "Public"})
T("Submit complaint without auth -> 401", sc == 401, f"got {sc}")

# Submit with missing text
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_s1"],
                   form_data={"visibility": "Public"})
    T("Submit without text -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# Submit with text too short (5 chars)
if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_s1"],
                   form_data={"original_text": "short", "visibility": "Public"})
    T("Submit text too short -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

# Invalid visibility
if S["tok_s3"]:
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_s3"],
                   form_data={"original_text": "This is a valid length complaint text about something important.",
                              "visibility": "InvalidVisibility"})
    T("Invalid visibility -> 400/422/429", sc in (400, 422, 429), f"got {sc}: {str(body)[:80]}")

# Authority cannot submit complaint
if S["tok_admin"]:
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_admin"],
                   form_data={"original_text": "Authority trying to submit complaint about the campus.",
                              "visibility": "Public"})
    T("Authority on student endpoint -> 401/403", sc in (401, 403), f"got {sc}")

# With image upload (valid PNG)
if S["tok_s3"]:
    png_bytes = make_valid_png(10, 10)
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_s3"],
                   form_data={"original_text": "The road outside the college has massive potholes "
                                               "causing accidents. I have attached a photo.",
                              "visibility": "Public"},
                   files={"image": ("test.png", png_bytes, "image/png")})
    T("Complaint with image -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")
    if sc in (200, 201):
        pause(CD_LLM, "LLM processing image complaint")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 08 — PUBLIC FEED
# ════════════════════════════════════════════════════════════════════════════
section("PUBLIC FEED")

sc, body = req("GET", "/api/complaints/public-feed")
T("GET /public-feed without auth -> 200 or 401", sc in (200, 401), f"got {sc}")

if S["tok_s1"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s1"])
    T("GET /public-feed as male hostel student -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("public feed returns list",
      isinstance(body, dict) and ("complaints" in body or "data" in body), str(body)[:120])

    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s1"],
                   params={"page": 1, "page_size": 5})
    T("Public feed with pagination -> 200", sc == 200, f"got {sc}")

if S["tok_s3"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s3"])
    T("GET /public-feed as day scholar -> 200", sc == 200, f"got {sc}")
    if sc == 200 and isinstance(body, dict):
        complaints = body.get("complaints") or body.get("data") or []
        if isinstance(complaints, list):
            hostel_found = any("hostel" in str(c.get("category", "")).lower() for c in complaints)
            T("Day scholar sees no hostel complaints", not hostel_found,
              "Hostel complaint found in day scholar feed")

if S["tok_s2"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s2"])
    T("GET /public-feed as female student -> 200", sc == 200, f"got {sc}")
    if sc == 200 and isinstance(body, dict):
        complaints = body.get("complaints") or body.get("data") or []
        if isinstance(complaints, list):
            mens_found = any(c.get("category") == "Men's Hostel" for c in complaints)
            T("Female student sees no Men's Hostel complaints", not mens_found,
              "Men's Hostel complaint found in female feed")

if S["tok_admin"]:
    sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_admin"])
    T("Admin on public feed -> 200 or 403", sc in (200, 403), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 09 — COMPLAINT DETAILS
# ════════════════════════════════════════════════════════════════════════════
section("COMPLAINT DETAILS")

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}", token=S["tok_s1"])
    T("GET complaint by owner -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Complaint detail has id field",
      isinstance(body, dict) and S["cid_s1"] in str(body), str(body)[:120])

    if S["tok_s4"]:
        sc, body = req("GET", f"/api/complaints/{S['cid_s1']}", token=S["tok_s4"])
        T("GET public complaint by different student -> 200", sc == 200, f"got {sc}")

    if S["tok_admin"]:
        sc, body = req("GET", f"/api/authorities/complaints/{S['cid_s1']}", token=S["tok_admin"])
        T("Admin sees complaint via authority endpoint -> 200", sc == 200, f"got {sc}")
else:
    SKIP("Complaint detail tests", "cid_s1 missing")

if S["tok_s1"]:
    sc, body = req("GET", "/api/complaints/not-a-valid-uuid", token=S["tok_s1"])
    T("Invalid UUID -> 400/422", sc in (400, 422), f"got {sc}")

    sc, body = req("GET", f"/api/complaints/00000000-0000-0000-0000-{TS.zfill(12)}",
                   token=S["tok_s1"])
    T("Non-existent UUID -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")

if S["cid_s1"]:
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}")
    T("Complaint detail without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 10 — VOTING
# ════════════════════════════════════════════════════════════════════════════
section("VOTING")

vote_cid = S["cid_s3"] or S["cid_s1_gen"]

if vote_cid and S["tok_s2"]:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote", token=S["tok_s2"],
                   json_data={"vote_type": "Upvote"})
    T("s2 upvote -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")
    T("Upvote returns upvotes count", isinstance(body, dict) and "upvotes" in str(body), str(body)[:80])

    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote", token=S["tok_s2"],
                   json_data={"vote_type": "Upvote"})
    T("Duplicate upvote -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote", token=S["tok_s2"],
                   json_data={"vote_type": "Downvote"})
    T("Change vote upvote->downvote -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", f"/api/complaints/{vote_cid}/my-vote", token=S["tok_s2"])
    T("GET my-vote -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("my-vote returns vote_type", isinstance(body, dict) and "vote_type" in str(body), str(body)[:80])

    sc, body = req("DELETE", f"/api/complaints/{vote_cid}/vote", token=S["tok_s2"])
    T("DELETE vote (remove) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("DELETE", f"/api/complaints/{vote_cid}/vote", token=S["tok_s2"])
    T("Remove vote twice -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

if vote_cid and S["tok_s4"]:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote", token=S["tok_s4"],
                   json_data={"vote_type": "Downvote"})
    T("s4 downvote -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

# Vote on own complaint
if S["cid_s3"] and S["tok_s3"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/vote", token=S["tok_s3"],
                   json_data={"vote_type": "Upvote"})
    T("Vote on own complaint -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

if vote_cid and S["tok_s1"]:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote", token=S["tok_s1"],
                   json_data={"vote_type": "Invalid"})
    T("Invalid vote_type -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

if vote_cid:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote", json_data={"vote_type": "Upvote"})
    T("Vote without auth -> 401", sc == 401, f"got {sc}")

if vote_cid and S["tok_admin"]:
    sc, body = req("POST", f"/api/complaints/{vote_cid}/vote", token=S["tok_admin"],
                   json_data={"vote_type": "Upvote"})
    T("Authority voting -> 401/403", sc in (401, 403), f"got {sc}")

if S["cid_s1"] and S["tok_s3"]:
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/my-vote", token=S["tok_s3"])
    T("my-vote when not voted -> 200 or 404", sc in (200, 404), f"got {sc}: {str(body)[:80]}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 11 — IMAGE UPLOAD AND RETRIEVAL
# ════════════════════════════════════════════════════════════════════════════
section("IMAGE UPLOAD AND RETRIEVAL")

small_png = make_valid_png(10, 10)

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/upload-image",
                   token=S["tok_s1"],
                   files={"file": ("complaint.png", small_png, "image/png")})
    T("Upload image to complaint -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/image", token=S["tok_s1"])
    T("GET complaint image -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    if S["tok_s4"]:
        sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/image", token=S["tok_s4"])
        T("Different student gets public complaint image -> 200/403", sc in (200, 403), f"got {sc}")

    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/upload-image", token=S["tok_s1"],
                   files={"file": ("test.txt", b"not an image file content here", "text/plain")})
    T("Upload non-image -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/upload-image",
                   files={"file": ("img.png", small_png, "image/png")})
    T("Upload image without auth -> 401", sc == 401, f"got {sc}")

    if S["cid_s1_dept"]:
        sc, body = req("GET", f"/api/complaints/{S['cid_s1_dept']}/image", token=S["tok_s1"])
        T("GET image on complaint with no image -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Image tests", "cid_s1 missing")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 12 — STATUS HISTORY AND TIMELINE
# ════════════════════════════════════════════════════════════════════════════
section("STATUS HISTORY AND TIMELINE")

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/status-history", token=S["tok_s1"])
    T("GET status-history -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("status-history is list or dict", isinstance(body, (list, dict)), str(body)[:80])

    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/timeline", token=S["tok_s1"])
    T("GET timeline -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/status-history")
    T("status-history without auth -> 401", sc == 401, f"got {sc}")

    sc, body = req("GET", f"/api/complaints/{S['cid_s1']}/timeline")
    T("timeline without auth -> 401", sc == 401, f"got {sc}")
else:
    SKIP("Status history tests", "cid_s1 missing")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 13 — ADVANCED FILTER
# ════════════════════════════════════════════════════════════════════════════
section("ADVANCED FILTER")

if S["tok_s1"]:
    sc, body = req("GET", "/api/complaints/filter/advanced", token=S["tok_s1"],
                   params={"status": "Raised", "page": 1, "page_size": 10})
    T("Student advanced filter by status=Raised -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", "/api/complaints/filter/advanced", token=S["tok_s1"],
                   params={"priority": "High", "page": 1, "page_size": 5})
    T("Student advanced filter by priority=High -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/complaints/filter/advanced", token=S["tok_s1"],
                   params={"has_image": "true", "page": 1, "page_size": 5})
    T("Student advanced filter by has_image -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/complaints/filter/advanced", token=S["tok_s1"],
                   params={"department_id": 1, "page": 1, "page_size": 5})
    T("Student advanced filter by department_id -> 200", sc == 200, f"got {sc}")
else:
    SKIP("Advanced filter", "tok_s1 missing")

if S["tok_admin"]:
    sc, body = req("GET", "/api/complaints/filter/advanced", token=S["tok_admin"],
                   params={"page": 1, "page_size": 5})
    T("Admin on student-only filter -> 401/403", sc in (401, 403), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 14 — SPAM FLAG / UNFLAG
# ════════════════════════════════════════════════════════════════════════════
section("SPAM FLAG / UNFLAG")

if S["tok_officer"] and S["cid_s3"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/flag-spam",
                   token=S["tok_officer"],
                   params={"reason": "This appears to be a duplicate test complaint"})
    T("Authority flag complaint as spam -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/unflag-spam",
                   token=S["tok_officer"])
    T("Authority unflag spam -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Spam flag tests", "officer token or cid_s3 missing")

if S["tok_s1"] and S["cid_s3"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/flag-spam", token=S["tok_s1"],
                   params={"reason": "Student trying to flag"})
    T("Student flag spam -> 401/403", sc in (401, 403), f"got {sc}")

if S["cid_s3"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s3']}/flag-spam",
                   params={"reason": "No auth"})
    T("Flag spam without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 15 — AUTHORITY PROFILE AND DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY PROFILE AND DASHBOARD")

if S["tok_admin"]:
    sc, body = req("GET", "/api/authorities/profile", token=S["tok_admin"])
    T("GET authority profile (admin) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Authority profile has email", isinstance(body, dict) and "email" in str(body), str(body)[:120])

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

if S["tok_s1"]:
    sc, body = req("GET", "/api/authorities/profile", token=S["tok_s1"])
    T("Student on authority profile -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/authorities/profile")
T("Authority profile without auth -> 401", sc == 401, f"got {sc}")

sc, body = req("GET", "/api/authorities/dashboard")
T("Authority dashboard without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 16 — AUTHORITY MY-COMPLAINTS
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY MY-COMPLAINTS")

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_warden_m"])
    T("GET authority my-complaints -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("my-complaints returns list or dict",
      isinstance(body, (list, dict)), str(body)[:80])

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


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 17 — AUTHORITY VIEW COMPLAINT DETAIL
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY VIEW COMPLAINT DETAIL")

if S["tok_admin"] and S["cid_s1"]:
    sc, body = req("GET", f"/api/authorities/complaints/{S['cid_s1']}", token=S["tok_admin"])
    T("Admin view complaint detail -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Detail has text",
      isinstance(body, dict) and ("text" in str(body) or "complaint" in str(body)),
      str(body)[:120])

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("GET", f"/api/authorities/complaints/{S['cid_s1']}", token=S["tok_s1"])
    T("Student on authority complaint detail -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/authorities/complaints/not-a-uuid", token=S["tok_admin"])
    T("Authority complaint detail invalid UUID -> 400/422", sc in (400, 422), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 18 — AUTHORITY STATUS UPDATE
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY STATUS UPDATE")

update_cid = S["cid_s1"] or S["cid_s3"] or S["cid_s1_gen"]

if S["tok_admin"] and update_cid:
    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "In Progress", "reason": "Taking action on this"})
    T("Admin update Raised->InProgress -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Resolved", "reason": "Issue has been resolved"})
    T("Admin update InProgress->Resolved -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Closed", "reason": "Closed after verification"})
    T("Admin update Resolved->Closed -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

    sc, body = req("PUT", f"/api/authorities/complaints/{update_cid}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Raised", "reason": "Trying to reopen"})
    T("Invalid transition Closed->Raised -> 400", sc == 400, f"got {sc}: {str(body)[:80]}")

if S["tok_admin"] and S["cid_s2"]:
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s2']}/status",
                   token=S["tok_admin"], json_data={"status": "In Progress"})
    T("Status update In Progress (no reason) -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s2']}/status",
                   token=S["tok_admin"], json_data={"status": "Spam"})
    T("Status Spam without reason -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s2']}/status",
                   token=S["tok_admin"],
                   json_data={"status": "Spam", "reason": "Verified spam complaint"})
    T("Status Spam with reason -> 200 or 400", sc in (200, 400), f"got {sc}: {str(body)[:80]}")

if S["tok_s1"] and S["cid_s1_dept"]:
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s1_dept']}/status",
                   token=S["tok_s1"],
                   json_data={"status": "In Progress", "reason": "Student trying"})
    T("Student on status update -> 401/403", sc in (401, 403), f"got {sc}")

if S["cid_s1_dept"]:
    sc, body = req("PUT", f"/api/authorities/complaints/{S['cid_s1_dept']}/status",
                   json_data={"status": "In Progress"})
    T("Status update without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 19 — AUTHORITY POST UPDATE
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY POST UPDATE")

post_cid = S["cid_s1_dept"] or S["cid_s1"]

if S["tok_admin"] and post_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{post_cid}/post-update",
                   token=S["tok_admin"],
                   params={"title": "Complaint reviewed",
                           "content": "We have reviewed this complaint and are taking action."})
    T("Authority post update -> 200/201", sc in (200, 201), f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

    sc, body = req("POST", f"/api/authorities/complaints/{post_cid}/post-update",
                   token=S["tok_admin"],
                   params={"title": "", "content": "Some content"})
    T("Empty post update title -> 200/400/422", sc in (200, 400, 422),
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


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 20 — ESCALATION
# ════════════════════════════════════════════════════════════════════════════
section("ESCALATION")

esc_cid = S["cid_s1"]  # Men's hostel complaint

if S["tok_warden_m"] and esc_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_warden_m"],
                   params={"reason": "Issue requires deputy warden intervention"})
    T("Warden escalate -> 200/201 or 400/403", sc in (200, 201, 403, 400),
      f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

if S["tok_admin"] and esc_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_admin"],
                   params={"reason": "Escalating to higher level"})
    T("Admin escalate -> 200/201 or 400/404", sc in (200, 201, 400, 404),
      f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_admin"])
    T("Escalate without reason -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

if S["tok_s1"] and esc_cid:
    sc, body = req("POST", f"/api/authorities/complaints/{esc_cid}/escalate",
                   token=S["tok_s1"], params={"reason": "Student escalating"})
    T("Student escalate -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_admin"] and esc_cid:
    sc, body = req("GET", f"/api/authorities/complaints/{esc_cid}/escalation-history",
                   token=S["tok_admin"])
    T("GET escalation-history -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Escalation history is list or dict", isinstance(body, (list, dict)), str(body)[:80])

if S["tok_s1"] and esc_cid:
    sc, body = req("GET", f"/api/authorities/complaints/{esc_cid}/escalation-history",
                   token=S["tok_s1"])
    T("Student on escalation-history -> 401/403", sc in (401, 403), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 21 — AUTHORITY STATS
# ════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 22 — STUDENT MY-COMPLAINTS
# ════════════════════════════════════════════════════════════════════════════
section("STUDENT MY-COMPLAINTS")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"])
    T("GET my-complaints -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("my-complaints returns list or dict", isinstance(body, (list, dict)), str(body)[:80])

    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"status": "Raised"})
    T("my-complaints filter by status -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 1, "page_size": 3})
    T("my-complaints with pagination -> 200", sc == 200, f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_admin"])
    T("Authority on student my-complaints -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/students/my-complaints")
T("my-complaints without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 23 — NOTIFICATIONS
# ════════════════════════════════════════════════════════════════════════════
section("NOTIFICATIONS")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s1"])
    T("GET notifications -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Notifications returns list or dict", isinstance(body, (list, dict)), str(body)[:80])

    sc, body = req("GET", "/api/students/notifications/unread-count", token=S["tok_s1"])
    T("GET unread-count -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("unread-count has numeric count",
      isinstance(body, dict) and any(isinstance(v, int) for v in body.values()),
      str(body)[:80])

    sc, body = req("PUT", "/api/students/notifications/mark-all-read", token=S["tok_s1"])
    T("PUT mark-all-read -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", "/api/students/notifications", token=S["tok_s1"],
                   params={"unread_only": "true"})
    T("GET notifications unread_only -> 200", sc == 200, f"got {sc}")

    # Get a notification ID
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s1"],
                   params={"page": 1, "page_size": 5})
    if sc == 200 and isinstance(body, dict):
        notifs = body.get("notifications") or body.get("data") or []
        if isinstance(notifs, list) and notifs:
            S["notif_id"] = notifs[0].get("id")

    if S["notif_id"]:
        sc, body = req("PUT", f"/api/students/notifications/{S['notif_id']}/read",
                       token=S["tok_s1"])
        T("PUT notification/read -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

        sc, body = req("DELETE", f"/api/students/notifications/{S['notif_id']}",
                       token=S["tok_s1"])
        T("DELETE notification -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

        sc, body = req("DELETE", f"/api/students/notifications/{S['notif_id']}",
                       token=S["tok_s1"])
        T("Delete notification twice -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")
    else:
        SKIP("Notification ID tests", "no notifications available")

    sc, body = req("PUT", "/api/students/notifications/not-a-uuid/read", token=S["tok_s1"])
    T("Mark invalid notif read -> 400/404/422", sc in (400, 404, 422), f"got {sc}")

sc, body = req("GET", "/api/students/notifications")
T("Notifications without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 24 — ADMIN: MANAGE AUTHORITIES
# ════════════════════════════════════════════════════════════════════════════
section("ADMIN — MANAGE AUTHORITIES")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/authorities", token=S["tok_admin"])
    T("GET /admin/authorities -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Authorities list returns list or dict", isinstance(body, (list, dict)), str(body)[:80])

    sc, body = req("GET", "/api/admin/authorities", token=S["tok_admin"],
                   params={"active_only": "true"})
    T("GET /admin/authorities active_only -> 200", sc == 200, f"got {sc}")

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
    T("New authority response success", sc in (200, 201), str(body)[:80])
    pause(CD_WRITE)

    sc, body = req("POST", "/api/admin/authorities", token=S["tok_admin"],
                   json_data={"email": S["new_auth_email"], "password": "Authority@1234",
                              "name": "Duplicate Authority", "authority_type": "Admin Officer",
                              "authority_level": 50})
    T("Duplicate authority email -> 400/409", sc in (400, 409), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", "/api/admin/authorities", token=S["tok_admin"],
                   json_data={"email": f"auth_{TS}@gmail.com", "password": "Authority@1234",
                              "name": "Bad Domain Auth", "authority_type": "Admin Officer",
                              "authority_level": 50})
    T("Authority wrong email domain -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", "/api/admin/authorities", token=S["tok_admin"],
                   json_data={"name": "Incomplete Authority"})
    T("Create authority missing fields -> 400/422", sc in (400, 422), f"got {sc}")

    # Toggle active
    sc2, body2 = req("GET", "/api/admin/authorities", token=S["tok_admin"])
    found_auth_id = None
    if sc2 == 200 and isinstance(body2, (dict, list)):
        auths = (body2.get("authorities") or body2.get("data") or []) if isinstance(body2, dict) else body2
        for a in auths:
            if isinstance(a, dict) and a.get("authority_level", 100) < 50:
                found_auth_id = a.get("id")
                break
    if found_auth_id:
        sc, body = req("PUT", f"/api/admin/authorities/{found_auth_id}/toggle-active",
                       token=S["tok_admin"], params={"activate": "false"})
        T("Toggle authority inactive -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
        sc, body = req("PUT", f"/api/admin/authorities/{found_auth_id}/toggle-active",
                       token=S["tok_admin"], params={"activate": "true"})
        T("Toggle authority active back -> 200", sc == 200, f"got {sc}")
    else:
        SKIP("Toggle authority", "no suitable authority found")

    sc, body = req("PUT", "/api/admin/authorities/99999/toggle-active",
                   token=S["tok_admin"], params={"activate": "false"})
    T("Toggle non-existent authority -> 404", sc == 404, f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Admin authority management", "admin token missing")

if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/authorities", token=S["tok_s1"])
    T("Student on admin/authorities -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/admin/authorities", token=S["tok_warden_m"])
    T("Warden on admin/authorities -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/authorities")
T("Admin authorities without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 25 — ADMIN: MANAGE STUDENTS
# ════════════════════════════════════════════════════════════════════════════
section("ADMIN — MANAGE STUDENTS")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"])
    T("GET /admin/students -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Students list returns list or dict", isinstance(body, (list, dict)), str(body)[:80])

    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"department_id": 1})
    T("GET /admin/students by dept -> 200", sc == 200, f"got {sc}")

    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"active_only": "true"})
    T("GET /admin/students active_only -> 200", sc == 200, f"got {sc}")

    sc, body = req("PUT", f"/api/admin/students/{S['s4_roll']}/toggle-active",
                   token=S["tok_admin"], params={"activate": "false"})
    T("Toggle student deactivate -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    pause(CD_WRITE)

    sc, body = req("POST", "/api/students/login",
                   json_data={"email_or_roll_no": S["s4_email"], "password": COMP_PWD})
    T("Deactivated student login -> 401/403", sc in (401, 403), f"got {sc}: {str(body)[:80]}")

    sc, body = req("PUT", f"/api/admin/students/{S['s4_roll']}/toggle-active",
                   token=S["tok_admin"], params={"activate": "true"})
    T("Toggle student reactivate -> 200", sc == 200, f"got {sc}")
    pause(CD_WRITE)

    sc, body = req("PUT", "/api/admin/students/INVALID99/toggle-active",
                   token=S["tok_admin"])
    T("Toggle invalid student -> 404/422", sc in (404, 422), f"got {sc}")
else:
    SKIP("Admin student management", "admin token missing")

if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_s1"])
    T("Student on /admin/students -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/students")
T("Admin students without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 26 — ADMIN STATS AND ANALYTICS
# ════════════════════════════════════════════════════════════════════════════
section("ADMIN STATS AND ANALYTICS")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_admin"])
    T("GET /admin/stats/overview -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Overview has total_complaints",
      isinstance(body, dict) and "total_complaints" in str(body), str(body)[:120])

    sc, body = req("GET", "/api/admin/stats/analytics", token=S["tok_admin"])
    T("GET /admin/stats/analytics -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

    sc, body = req("GET", "/api/admin/health/metrics", token=S["tok_admin"])
    T("GET /admin/health/metrics -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Admin stats", "admin token missing")

if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_s1"])
    T("Student on admin stats -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_warden_m"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_warden_m"])
    T("Non-admin authority on admin stats -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/stats/overview")
T("Admin stats without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 27 — ADMIN BULK STATUS UPDATE
# ════════════════════════════════════════════════════════════════════════════
section("ADMIN BULK STATUS UPDATE")

bulk_ids = [cid for cid in [S["cid_s1_dept"], S["cid_s3"]] if cid]

if S["tok_admin"] and bulk_ids:
    sc, body = req("POST", "/api/admin/complaints/bulk-status-update",
                   token=S["tok_admin"],
                   params={"complaint_ids": bulk_ids, "new_status": "In Progress",
                           "reason": "Bulk processing by admin"})
    T("Admin bulk status update -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Bulk update has success info",
      isinstance(body, dict) and ("success" in str(body) or "updated" in str(body)),
      str(body)[:120])
    pause(CD_WRITE)

    sc, body = req("POST", "/api/admin/complaints/bulk-status-update",
                   token=S["tok_admin"],
                   params={"complaint_ids": bulk_ids, "new_status": "InvalidStatus",
                           "reason": "Test"})
    T("Bulk update invalid status -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    sc, body = req("POST", "/api/admin/complaints/bulk-status-update",
                   token=S["tok_admin"],
                   params={"complaint_ids": bulk_ids, "new_status": "Resolved"})
    T("Bulk update missing reason -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Bulk status update", "admin token or complaint IDs missing")

if S["tok_s1"] and bulk_ids:
    sc, body = req("POST", "/api/admin/complaints/bulk-status-update", token=S["tok_s1"],
                   json_data={"complaint_ids": bulk_ids, "status": "In Progress"})
    T("Student on bulk update -> 401/403", sc in (401, 403), f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 28 — ADMIN IMAGE MODERATION
# ════════════════════════════════════════════════════════════════════════════
section("ADMIN IMAGE MODERATION")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/images/pending-verification", token=S["tok_admin"])
    T("GET pending verification images -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")
    T("Pending images returns list or dict", isinstance(body, (list, dict)), str(body)[:80])

    img_cid = S["cid_s1"]
    if img_cid:
        sc, body = req("POST", f"/api/admin/images/{img_cid}/moderate",
                       token=S["tok_admin"], params={"approve": "true"})
        T("Admin approve image -> 200/201/404", sc in (200, 201, 404),
          f"got {sc}: {str(body)[:80]}")

        sc, body = req("POST", f"/api/admin/images/{img_cid}/moderate",
                       token=S["tok_admin"],
                       params={"approve": "false", "reason": "Not relevant to complaint"})
        T("Admin reject image -> 200/201/404", sc in (200, 201, 404),
          f"got {sc}: {str(body)[:80]}")
else:
    SKIP("Image moderation", "admin token missing")

if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/images/pending-verification", token=S["tok_s1"])
    T("Student on pending images -> 401/403", sc in (401, 403), f"got {sc}")

sc, body = req("GET", "/api/admin/images/pending-verification")
T("Pending images without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 29 — IMAGE VERIFY ENDPOINT
# ════════════════════════════════════════════════════════════════════════════
section("IMAGE VERIFY ENDPOINT")

if S["tok_s1"] and S["cid_s1"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/verify-image", token=S["tok_s1"])
    T("Student verify-image (own) -> 200/201/400/404", sc in (200, 201, 400, 404),
      f"got {sc}: {str(body)[:80]}")

if S["tok_s2"] and S["cid_s1"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/verify-image", token=S["tok_s2"])
    T("Student verify-image (not owner) -> 403", sc == 403, f"got {sc}: {str(body)[:80]}")

if S["cid_s1"]:
    sc, body = req("POST", f"/api/complaints/{S['cid_s1']}/verify-image")
    T("verify-image without auth -> 401", sc == 401, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 30 — CROSS-CUTTING SECURITY TESTS
# ════════════════════════════════════════════════════════════════════════════
section("CROSS-CUTTING SECURITY TESTS")

sc, body = req("GET", "/api/students/profile", token="totally.invalid.jwt")
T("Invalid JWT -> 401", sc == 401, f"got {sc}")

sc, body = req("GET", "/api/students/profile",
               token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
                     ".eyJzdWIiOiJ0ZXN0QHNyZWMuYWMuaW4iLCJyb2xlIjoic3R1ZGVudCIsImV4cCI6MTYwMDAwMDAwMH0"
                     ".wrong_signature")
T("Expired/malformed JWT -> 401", sc == 401, f"got {sc}")

if S["tok_s1"]:
    sc, body = req("GET", "/api/admin/stats/overview", token=S["tok_s1"])
    T("Student token on admin endpoint -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_admin"]:
    sc, body = req("POST", "/api/students/change-password", token=S["tok_admin"],
                   json_data={"current_password": "old", "new_password": "New@123456"})
    T("Authority token on student change-password -> 401/403", sc in (401, 403), f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"search": "'; DROP TABLE students; --"})
    T("SQL injection in params -> not 500", sc != 500, f"got {sc}")

if S["tok_s1"]:
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_s1"],
                   form_data={"original_text": "<script>alert('xss')</script> The lab equipment is "
                                               "broken and students cannot complete their practicals.",
                              "visibility": "Public"})
    T("XSS in complaint text -> not 500", sc != 500, f"got {sc}: {str(body)[:80]}")
    if sc in (200, 201):
        pause(CD_LLM, "LLM processing XSS complaint")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 31 — BOUNDARY AND EDGE CASE TESTS
# ════════════════════════════════════════════════════════════════════════════
section("BOUNDARY AND EDGE CASE TESTS")

# s4 for boundary (re-fetch token after reactivation)
sc, body = req("POST", "/api/students/login",
               json_data={"email_or_roll_no": S["s4_email"], "password": COMP_PWD})
if sc == 200 and isinstance(body, dict):
    S["tok_s4"] = body.get("token") or body.get("data", {}).get("token")

if S["tok_s4"]:
    long_text = "A" * 2001
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_s4"],
                   form_data={"original_text": long_text, "visibility": "Public"})
    T("Complaint text > 2000 chars -> 400/422", sc in (400, 422), f"got {sc}: {str(body)[:80]}")

    max_text = ("The canteen food quality has severely deteriorated. " * 40)[:2000]
    sc, body = req("POST", "/api/complaints/submit", token=S["tok_s4"],
                   form_data={"original_text": max_text, "visibility": "Public"})
    T("Complaint at 2000 chars -> 200/201/400/429", sc in (200, 201, 400, 429),
      f"got {sc}: {str(body)[:80]}")
    if sc in (200, 201):
        pause(CD_LLM, "LLM boundary complaint")

if S["tok_s1"]:
    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 0, "page_size": 10})
    T("page=0 -> not 500", sc != 500, f"got {sc}")

    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 1, "page_size": 0})
    T("page_size=0 -> not 500", sc != 500, f"got {sc}")

    sc, body = req("GET", "/api/students/my-complaints", token=S["tok_s1"],
                   params={"page": 99999, "page_size": 10})
    T("Very large page -> not 500", sc != 500, f"got {sc}")

valid_uuid = "00000000-0000-0000-0000-000000000001"
if S["tok_admin"]:
    sc, body = req("GET", f"/api/authorities/complaints/{valid_uuid}", token=S["tok_admin"])
    T("Valid UUID format, no complaint -> 404", sc == 404, f"got {sc}")

    sc, body = req("PUT", f"/api/authorities/complaints/{valid_uuid}/status",
                   token=S["tok_admin"], json_data={"status": "In Progress"})
    T("Status update on non-existent complaint -> 404", sc == 404, f"got {sc}")

if S["tok_s1"]:
    sc, body = req("PUT", "/api/students/profile", token=S["tok_s1"],
                   json_data={"name": ""})
    T("Update profile empty name -> 400/422", sc in (400, 422), f"got {sc}")

if S["tok_admin"]:
    sc, body = req("GET", "/api/admin/students", token=S["tok_admin"],
                   params={"department_id": -1})
    T("Negative department_id -> not 500", sc != 500, f"got {sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 32 — WORKFLOW INTEGRATION TESTS
# ════════════════════════════════════════════════════════════════════════════
section("WORKFLOW INTEGRATION TESTS")

workflow_token = S["tok_s4"] or S["tok_s3"]
if workflow_token:
    sc, body = submit_complaint(workflow_token,
        "The hostel warden is not responding to maintenance requests "
        "for over two weeks. Multiple students are affected.",
        visibility="Private")
    T("Submit private hostel complaint -> 200/201/429", sc in (200, 201, 429),
      f"got {sc}: {str(body)[:80]}")
    wf_cid = None
    if sc in (200, 201) and isinstance(body, dict):
        data = body.get("data", body)
        wf_cid = data.get("id") or data.get("complaint_id")

    if wf_cid and S["tok_admin"]:
        sc, body = req("GET", "/api/authorities/my-complaints", token=S["tok_admin"])
        T("Authority sees complaints after submission -> 200", sc == 200, f"got {sc}")

        sc, body = req("POST", f"/api/authorities/complaints/{wf_cid}/post-update",
                       token=S["tok_admin"],
                       params={"title": "Received",
                               "content": "We have received your complaint."})
        T("Authority posts update on workflow complaint -> 200/201", sc in (200, 201),
          f"got {sc}: {str(body)[:80]}")
        pause(CD_WRITE)

        sc, body = req("GET", "/api/students/notifications", token=workflow_token)
        T("Student gets notifications after authority update -> 200", sc == 200, f"got {sc}")

        sc, body = req("GET", f"/api/complaints/{wf_cid}", token=workflow_token)
        T("Student can view private complaint -> 200", sc == 200, f"got {sc}: {str(body)[:80]}")

        if S["tok_s1"]:
            sc, body = req("GET", "/api/complaints/public-feed", token=S["tok_s1"])
            if sc == 200 and isinstance(body, dict):
                feed = body.get("complaints") or body.get("data") or []
                if isinstance(feed, list):
                    found = any(str(c.get("id", "")) == str(wf_cid) for c in feed)
                    T("Private complaint not in public feed", not found,
                      "Private complaint appeared in feed!")
else:
    SKIP("Workflow integration", "no student token available")

# Vote-based priority recalculation
vote_target = S["cid_s1_gen"]
if vote_target and S["tok_s2"] and S["tok_s3"] and S["tok_s4"]:
    for tok in [S["tok_s2"], S["tok_s3"], S["tok_s4"]]:
        req("POST", f"/api/complaints/{vote_target}/vote",
            token=tok, json_data={"vote_type": "Upvote"})

    sc, body = req("GET", f"/api/complaints/{vote_target}", token=S["tok_s2"])
    T("Multiple upvotes -> complaint still accessible", sc == 200, f"got {sc}")
    if sc == 200 and isinstance(body, dict):
        data = body.get("data", body)
        priority = data.get("priority_score") or data.get("priority")
        T("Priority field present after upvotes", priority is not None,
          f"priority={priority}")


# ════════════════════════════════════════════════════════════════════════════
# ████  PHASE 3 — LLM ROUTING TESTS  (SECTIONS 33–43)  ████
# ════════════════════════════════════════════════════════════════════════════

log(f"\n{'█'*72}")
log(f"  PHASE 3 START — LLM ROUTING & NOTICE TESTS  [{_now()}]")
log(f"  Each complaint submission waits {CD_LLM}s for Groq LLM.")
log(f"  Estimated remaining time: ~25 minutes.")
log(f"{'█'*72}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 33 — LLM STUDENT REGISTRATION & LOGIN
# ════════════════════════════════════════════════════════════════════════════
section("LLM STUDENT REGISTRATION & LOGIN")

new_students = [
    {"roll": S["mh_roll"],  "name": "LLM MH Student",     "email": S["mh_email"],  "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "Men's Hostel tests"},
    {"roll": S["wh_roll"],  "name": "LLM WH Student",     "email": S["wh_email"],  "gender": "Female", "stay": "Hostel",      "dept": 2,  "label": "Women's Hostel tests"},
    {"roll": S["gen_roll"], "name": "LLM Gen Student",    "email": S["gen_email"], "gender": "Male",   "stay": "Day Scholar", "dept": 10, "label": "General (Day Scholar)"},
    {"roll": S["cse_roll"], "name": "LLM CSE Student",    "email": S["cse_email"], "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "CSE Dept tests"},
    {"roll": S["ece_roll"], "name": "LLM ECE Student",    "email": S["ece_email"], "gender": "Female", "stay": "Hostel",      "dept": 2,  "label": "ECE Dept tests"},
    {"roll": S["dc_roll"],  "name": "LLM DC Student",     "email": S["dc_email"],  "gender": "Male",   "stay": "Day Scholar", "dept": 4,  "label": "Disciplinary tests"},
    {"roll": S["obs_roll"], "name": "LLM Observer",       "email": S["obs_email"], "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "Observer/visibility"},
    {"roll": S["upd_roll"], "name": "LLM Upd Student",    "email": S["upd_email"], "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "Authority-update target"},
    {"roll": S["edg_roll"], "name": "LLM Edge Student",   "email": S["edg_email"], "gender": "Male",   "stay": "Day Scholar", "dept": 1,  "label": "Edge-case submissions"},
]

for s in new_students:
    sc = register_student(s["roll"], s["name"], s["email"],
                          s["gender"], s["stay"], s["dept"])
    T(f"Register {s['label']} ({s['roll']})", sc in (200, 201, 400, 409),
      f"got {sc}")  # 400/409 = already exists from previous run
    pause(CD_AUTH)

all_students = new_students + [
    {"roll": S["s1_roll"], "email": S["s1_email"], "gender": "Male", "stay": "Hostel", "dept": 1, "label": "Comprehensive s1", "pwd": COMP_PWD},
    {"roll": S["s2_roll"], "email": S["s2_email"], "gender": "Female", "stay": "Hostel", "dept": 1, "label": "Comprehensive s2", "pwd": COMP_PWD},
    {"roll": S["s3_roll"], "email": S["s3_email"], "gender": "Male", "stay": "Day Scholar", "dept": 2, "label": "Comprehensive s3", "pwd": COMP_PWD},
    {"roll": S["s4_roll"], "email": S["s4_email"], "gender": "Female", "stay": "Hostel", "dept": 4, "label": "Comprehensive s4", "pwd": COMP_PWD},
]
append_credentials(all_students)

for key in ("mh", "wh", "gen", "cse", "ece", "dc", "obs", "upd", "edg"):
    tok = login_student(S[f"{key}_email"], LLM_PWD)
    S[f"tok_s_{key}"] = tok
    T(f"LLM student '{key}' login", tok is not None, "got None")
    pause(CD_AUTH)


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 34 — MEN'S HOSTEL LLM CATEGORISATION  [15 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("MEN'S HOSTEL LLM CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Male Hostel student (CSE) submitting 5 hostel complaints")
log("  [info] Expected: category='Men\\'s Hostel', assigned to Men's Hostel Warden")

for i, text in enumerate(MH_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_mh"], text)
    check_submission(f"MH-{i}", sc, body, "Men's Hostel")
    if i == 1:
        S["mh_cid"] = body.get("id")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 35 — WOMEN'S HOSTEL LLM CATEGORISATION  [15 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("WOMEN'S HOSTEL LLM CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Female Hostel student (ECE) submitting 5 hostel complaints")
log("  [info] Expected: category='Women\\'s Hostel', assigned to Women's Hostel Warden")

for i, text in enumerate(WH_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_wh"], text)
    check_submission(f"WH-{i}", sc, body, "Women's Hostel")
    if i == 1:
        S["wh_cid"] = body.get("id")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 36 — GENERAL LLM CATEGORISATION  [15 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("GENERAL LLM CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Day Scholar student (IT dept) submitting 5 general campus complaints")
log("  [info] Expected: category='General', assigned to Admin Officer")

for i, text in enumerate(GEN_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_gen"], text)
    check_submission(f"GEN-{i}", sc, body, "General")
    if i == 1:
        S["gen_cid"] = body.get("id")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 37 — DEPARTMENT LLM CATEGORISATION  [15 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("DEPARTMENT LLM CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] CSE student -> 3 CSE lab complaints -> expected HOD CSE")
log("  [info] ECE student -> 2 ECE lab complaints -> expected HOD ECE")

for i, text in enumerate(CSE_DEPT_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_cse"], text)
    check_submission(f"DEPT-CSE-{i}", sc, body, "Department", check_dept_code="CSE")

for i, text in enumerate(ECE_DEPT_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_ece"], text)
    check_submission(f"DEPT-ECE-{i}", sc, body, "Department", check_dept_code="ECE")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 38 — DISCIPLINARY COMMITTEE LLM CATEGORISATION  [15 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("DISCIPLINARY COMMITTEE LLM CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Day Scholar student submitting 5 disciplinary complaints")
log("  [info] Expected: category='Disciplinary Committee', assigned to DC")

for i, text in enumerate(DC_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_dc"], text)
    check_submission(f"DC-{i}", sc, body, "Disciplinary Committee")
    if i == 1:
        S["dc_cid"] = body.get("id")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 39 — LLM EDGE CASES & BOUNDARY CONDITIONS
# ════════════════════════════════════════════════════════════════════════════
section("LLM EDGE CASES & BOUNDARY CONDITIONS")

# Edge-1: Day Scholar submits hostel-phrased complaint
log("  [edge-1] Day Scholar submits hostel-phrased complaint")
sc, body = submit_complaint(S["tok_s_edg"], EDGE_HOSTEL_FROM_DAY_SCHOLAR)
if sc in (400, 422):
    T("Edge-1: Day Scholar hostel complaint blocked at submission", True)
    SKIP("Edge-1: re-categorisation check", "submission rejected as expected")
elif sc in (200, 201):
    T("Edge-1: Day Scholar hostel complaint handled", True)
    cat = body.get("category", "")
    T("Edge-1: re-categorised AWAY from hostel categories",
      cat not in ("Men's Hostel", "Women's Hostel"),
      f"got category={cat!r}")
else:
    T("Edge-1: Day Scholar hostel complaint handled", False, f"sc={sc}")
    SKIP("Edge-1: re-categorisation check", "unexpected error")

# Edge-2: Ambiguous complaint
log("  [edge-2] Ambiguous complaint — noise near study area")
sc, body = submit_complaint(S["tok_s_edg"], EDGE_AMBIGUOUS)
T("Edge-2: Ambiguous complaint submitted/handled", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat = body.get("category")
    auth = body.get("assigned_authority")
    T("Edge-2: Gets a valid category", cat in CAT_IDS, f"got category={cat!r}")
    T("Edge-2: Assigned to authority", bool(auth), f"assigned_authority={auth!r}")
else:
    SKIP("Edge-2: category check", f"sc={sc}")
    SKIP("Edge-2: authority assignment check", f"sc={sc}")

# Edge-3: ECE student about CSE lab (cross-department)
log("  [edge-3] ECE student complains about CSE lab (cross-department)")
sc, body = submit_complaint(S["tok_s_ece"], EDGE_CROSS_DEPT)
T("Edge-3: Cross-dept complaint submitted", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat       = body.get("category", "")
    dept_code = body.get("target_department_code", "")
    cross     = body.get("cross_department", False)
    T("Edge-3: Cross-dept categorised as Department",
      cat == "Department", f"got category={cat!r}")
    T("Edge-3: Cross-dept flag or target dept code present",
      bool(dept_code) or cross,
      f"target_dept={dept_code!r}, cross_department={cross}")
else:
    SKIP("Edge-3: cross-dept category", f"sc={sc}")
    SKIP("Edge-3: cross_department flag", f"sc={sc}")

# Edge-4: Male student about women's hostel
log("  [edge-4] Male Hostel student submits women's hostel-phrased complaint")
sc, body = submit_complaint(S["tok_s_cse"], EDGE_MALE_WOMENS_HOSTEL)
T("Edge-4: Male student women's hostel complaint handled", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat = body.get("category", "")
    T("Edge-4: NOT routed to Women's Hostel",
      cat != "Women's Hostel", f"got category={cat!r}")
else:
    SKIP("Edge-4: routing check", f"sc={sc}")

# Edge-5: Ragging with vague phrasing
log("  [edge-5] Ragging/DC complaint with vague phrasing")
sc, body = submit_complaint(S["tok_s_edg"], EDGE_RAGGING_GENERAL_PHRASING)
T("Edge-5: Ragging (vague) complaint submitted", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat  = body.get("category", "")
    auth = body.get("assigned_authority")
    T("Edge-5: Ragging complaint routed to DC or has authority",
      cat == "Disciplinary Committee" or bool(auth),
      f"category={cat!r}, auth={auth!r}")
else:
    SKIP("Edge-5: DC routing check", f"sc={sc}")

# Edge-6: Empty text
log("  [edge-6] Empty complaint text -> expect 400/422")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "", "visibility": "Public"},
               files={"_": ("", b"", "text/plain")},
               token=S["tok_s_obs"])
pause(CD_READ)
T("Edge-6: Empty text rejected (400/422)", sc in (400, 422), f"sc={sc}")

# Edge-7: Too-short text (9 chars, MIN=10)
log("  [edge-7] Too-short complaint text (9 chars)")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "Too hot.", "visibility": "Public"},
               files={"_": ("", b"", "text/plain")},
               token=S["tok_s_obs"])
pause(CD_READ)
T("Edge-7: Short text (9 chars) rejected (400/422)", sc in (400, 422), f"sc={sc}")

# Edge-8: Invalid visibility
log("  [edge-8] Invalid visibility value")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "The WiFi is broken on campus.", "visibility": "Classified"},
               files={"_": ("", b"", "text/plain")},
               token=S["tok_s_obs"])
pause(CD_READ)
T("Edge-8: Invalid visibility rejected (400/422/429)", sc in (400, 422, 429), f"sc={sc}")

# Edge-9: No auth
log("  [edge-9] Unauthenticated submission")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "Campus lights are off near main gate.", "visibility": "Public"},
               files={"_": ("", b"", "text/plain")})
pause(CD_READ)
T("Edge-9: Unauthenticated submission rejected (401)", sc == 401, f"sc={sc}")

# Edge-10: Check DC complaint exists
log("  [edge-10] DC complaint accessible after submission")
if S.get("dc_cid"):
    sc, body = req("GET", f"/api/complaints/{S['dc_cid']}", token=S["tok_s_dc"])
    pause(CD_READ)
    T("Edge-10: DC complaint returns 200", sc == 200, f"sc={sc}")
else:
    SKIP("Edge-10: DC complaint check", "no DC complaint ID")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 40 — AUTHORITY POST-UPDATE FEATURE  [10 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY POST-UPDATE FEATURE  [10 TCs]")

log("  [info] Submitting update-test complaint (CSE Seminar Hall projector issue)")
sc, body = submit_complaint(S["tok_s_upd"], UPDATE_TEST_TEXT, visibility="Public")
S["upd_cid"] = body.get("id")
T("Update-test complaint submitted (200/201)", sc in (200, 201), f"sc={sc}")
T("Update-test complaint has an ID", bool(S.get("upd_cid")), f"id={S.get('upd_cid')!r}")
T("Update-test complaint categorised as Department",
  body.get("category") == "Department",
  f"category={body.get('category')!r}")

if not S.get("upd_cid"):
    for _ in range(7): SKIP("Update feature test", "no complaint ID — submission failed")
else:
    cid = S["upd_cid"]

    sc, body = req("GET", f"/api/complaints/{cid}", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Complaint owner can fetch complaint (200)", sc == 200, f"sc={sc}")

    log("  [info] Admin posting update: 'Investigation Initiated'")
    sc, body = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                   params={"title": "Investigation Initiated",
                           "content": "We have acknowledged your complaint. "
                                      "A technician has been dispatched to inspect the projector."},
                   token=S["tok_admin"])
    pause(CD_WRITE)
    T("Admin posts update on complaint (200)", sc == 200, f"sc={sc}")

    sc, body = req("PUT", f"/api/authorities/complaints/{cid}/status",
                   json_data={"status": "In Progress",
                              "reason": "Maintenance team assigned. Repair expected within 2 days."},
                   token=S["tok_admin"])
    pause(CD_WRITE)
    T("Status update Raised->In Progress (200)", sc == 200, f"sc={sc}")

    pause(2, "allow notification propagation")
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Owner notifications endpoint returns 200", sc == 200, f"sc={sc}")
    if sc == 200:
        notifs = body.get("notifications", []) if isinstance(body, dict) else []
        owner_has = any(str(n.get("complaint_id")) == str(cid) for n in notifs)
        T("Owner receives notification for complaint update",
          owner_has, f"total_notifs={len(notifs)}, cid={cid}")
    else:
        SKIP("Owner notification check", f"sc={sc}")

    sc, body = req("PUT", f"/api/authorities/complaints/{cid}/status",
                   json_data={"status": "Resolved",
                              "reason": "Projector has been repaired and tested."},
                   token=S["tok_admin"])
    pause(CD_WRITE)
    T("Status update In Progress->Resolved (200)", sc == 200, f"sc={sc}")

    sc, body = req("GET", f"/api/complaints/{cid}", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Complaint status shows Resolved",
      isinstance(body, dict) and body.get("status") == "Resolved",
      f"status={body.get('status') if isinstance(body, dict) else body!r}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 41 — NOTIFICATION VISIBILITY — ONLY OWNER NOTIFIED  [10 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("NOTIFICATION VISIBILITY — ONLY OWNER NOTIFIED  [10 TCs]")

if not S.get("upd_cid"):
    for _ in range(10): SKIP("Visibility test", "no update-test complaint ID")
else:
    cid = S["upd_cid"]

    log("  [info] Admin posts second update for visibility testing")
    sc, _ = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                params={"title": "Visibility Test Update",
                        "content": "This update is specifically for testing notification visibility."},
                token=S["tok_admin"])
    pause(CD_WRITE)
    T("Second update posted for visibility test (200)", sc == 200, f"sc={sc}")

    pause(2, "allow notification propagation")

    # Owner should have notification
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Owner notifications returns 200", sc == 200, f"sc={sc}")
    owner_notifs = body.get("notifications", []) if (sc == 200 and isinstance(body, dict)) else []
    owner_has = any(str(n.get("complaint_id")) == str(cid) for n in owner_notifs)
    T("Owner has notification for complaint (cid match)",
      owner_has, f"total={len(owner_notifs)}, cid={cid}")

    # Observer should NOT have this notification
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_obs"])
    pause(CD_READ)
    T("Observer notifications returns 200", sc == 200, f"sc={sc}")
    obs_notifs = body.get("notifications", []) if (sc == 200 and isinstance(body, dict)) else []
    obs_has = any(str(n.get("complaint_id")) == str(cid) for n in obs_notifs)
    T("Observer does NOT receive notification for another's complaint",
      not obs_has, f"obs_notif_count={len(obs_notifs)}, has_cid={obs_has}")

    sc, body = req("GET", f"/api/complaints/{cid}", token=S["tok_s_obs"])
    pause(CD_READ)
    T("Observer can view public complaint (200)", sc == 200, f"sc={sc}")

    log("  [info] Men's Hostel Warden tries to update HOD-assigned complaint")
    sc, _ = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                params={"title": "Unauthorised warden update",
                        "content": "Warden should not be able to update HOD complaint."},
                token=S["tok_warden_m"])
    pause(CD_WRITE)
    T("Warden cannot update complaint assigned to HOD (403/404)",
      sc in (403, 404), f"sc={sc}")

    log("  [info] Student tries to post authority update")
    sc, _ = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                params={"title": "Student fake update",
                        "content": "Students should not post authority updates."},
                token=S["tok_s_obs"])
    pause(CD_WRITE)
    T("Student cannot post authority update (401/403)", sc in (401, 403), f"sc={sc}")

    if owner_notifs:
        notif_id = owner_notifs[0].get("id")
        if notif_id:
            sc, _ = req("PUT", f"/api/students/notifications/{notif_id}/read",
                        token=S["tok_s_upd"])
            pause(CD_WRITE)
            T("Owner can mark notification as read (200)", sc == 200, f"sc={sc}")
        else:
            SKIP("Mark notification read", "no notification id in response")
    else:
        SKIP("Mark notification read", "no notifications found")

    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Notification list still returns 200 after marking read", sc == 200, f"sc={sc}")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 42 — AUTHORITY INBOX VERIFICATION  [10 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("AUTHORITY INBOX VERIFICATION — COMPLAINTS REACH CORRECT AUTHORITY  [10 TCs]")

def check_inbox(auth_key: str, expected_cat_id: int, label: str):
    tok = S.get(f"tok_{auth_key}")
    if not tok:
        SKIP(f"{label} inbox check", "no token")
        SKIP(f"{label} has expected category", "no token")
        return
    sc, body = req("GET", "/api/authorities/my-complaints",
                   params={"skip": 0, "limit": 50}, token=tok)
    pause(CD_READ)
    T(f"{label} complaints list returns 200", sc == 200, f"sc={sc}")
    if sc == 200 and isinstance(body, dict):
        complaints = body.get("complaints", [])
        cat_ids = [c.get("category_id") for c in complaints if isinstance(c, dict)]
        has_expected = expected_cat_id in cat_ids
        T(f"{label} inbox contains category_id={expected_cat_id} complaints",
          has_expected,
          f"found categories={sorted(set(cat_ids))}, expected={expected_cat_id}")
    else:
        SKIP(f"{label} has expected category", f"list sc={sc}")

check_inbox("warden_m", 1, "Men's Hostel Warden")
check_inbox("warden_w", 2, "Women's Hostel Warden")
check_inbox("officer",  3, "Admin Officer")
check_inbox("hod_cse",  4, "HOD CSE")
check_inbox("dc",       5, "Disciplinary Committee")


# ════════════════════════════════════════════════════════════════════════════
#  SECTION 43 — NOTICE / BROADCAST FEATURE  [~28 TCs]
# ════════════════════════════════════════════════════════════════════════════
section("NOTICE / BROADCAST FEATURE  [~28 TCs]")

NOTICE_BASE = "/api/authorities/notices"
NOTICE_FEED = "/api/students/notices"

# N1: Men's Hostel Warden creates notice (Male + Hostel)
log("  [N1] Men's Hostel Warden creates notice (Male + Hostel)")
sc, body = req("POST", NOTICE_BASE,
               json_data={
                   "title": "Water supply maintenance this Sunday",
                   "content": "Hot water supply in Block A will be off from 9 AM to 5 PM this Sunday for pipe maintenance. Please store water in advance.",
                   "category": "Maintenance",
                   "priority": "High",
                   "target_gender": ["Male"],
                   "target_stay_types": ["Hostel"],
               },
               token=S["tok_warden_m"])
pause(CD_WRITE)
S["notice_id_mh"] = body.get("id") if isinstance(body, dict) else None
T("N1: Men's Hostel Warden notice created (200/201)", sc in (200, 201), f"sc={sc}")
T("N1: Notice ID returned", bool(S.get("notice_id_mh")), f"id={S.get('notice_id_mh')}")
T("N1: Scope locked to Male+Hostel",
  isinstance(body, dict) and body.get("target_gender") == ["Male"] and body.get("target_stay_types") == ["Hostel"],
  f"got gender={body.get('target_gender') if isinstance(body, dict) else '?'}")

# N2: Men's Hostel Warden cannot target Female students
log("  [N2] Men's Hostel Warden tries to target Female (403)")
sc, body = req("POST", NOTICE_BASE,
               json_data={"title": "Blocked notice",
                          "content": "Men's warden must not target female students.",
                          "category": "General", "priority": "Low",
                          "target_gender": ["Female"]},
               token=S["tok_warden_m"])
pause(CD_WRITE)
T("N2: Men's Warden blocked from targeting Female (403)", sc == 403, f"sc={sc}")

# N3: Men's Hostel Warden cannot target Day Scholars
log("  [N3] Men's Hostel Warden tries to target Day Scholars (403)")
sc, body = req("POST", NOTICE_BASE,
               json_data={"title": "Blocked notice",
                          "content": "Men's warden cannot target day scholars.",
                          "category": "General", "priority": "Low",
                          "target_stay_types": ["Day Scholar"]},
               token=S["tok_warden_m"])
pause(CD_WRITE)
T("N3: Men's Warden blocked from targeting Day Scholars (403)", sc == 403, f"sc={sc}")

# N4: Women's Hostel Warden creates notice (auto Female + Hostel)
log("  [N4] Women's Hostel Warden creates notice (Female + Hostel)")
sc, body = req("POST", NOTICE_BASE,
               json_data={"title": "Laundry room schedule update",
                          "content": "The laundry room in Block B will now operate on a new time slot: 6 AM to 8 PM daily.",
                          "category": "Announcement", "priority": "Medium"},
               token=S["tok_warden_w"])
pause(CD_WRITE)
S["notice_id_wh"] = body.get("id") if isinstance(body, dict) else None
T("N4: Women's Hostel Warden notice created (200/201)", sc in (200, 201), f"sc={sc}")
T("N4: Scope auto-locked to Female+Hostel",
  isinstance(body, dict) and body.get("target_gender") == ["Female"] and body.get("target_stay_types") == ["Hostel"],
  f"got gender={body.get('target_gender') if isinstance(body, dict) else '?'}")

# N5: Admin campus-wide notice (no restrictions)
log("  [N5] Admin creates campus-wide notice")
sc, body = req("POST", NOTICE_BASE,
               json_data={"title": "Annual sports day registration open",
                          "content": "Registration for the annual inter-department sports day is open. All students can register through the sports committee before March 1st.",
                          "category": "Event", "priority": "Low"},
               token=S["tok_admin"])
pause(CD_WRITE)
S["notice_id_admin"] = body.get("id") if isinstance(body, dict) else None
T("N5: Admin campus-wide notice created (200/201)", sc in (200, 201), f"sc={sc}")

# N6: HOD CSE creates notice (auto-locked to CSE dept)
log("  [N6] HOD CSE creates notice (CSE dept only)")
sc, body = req("POST", NOTICE_BASE,
               json_data={"title": "CS301 lab assignment deadline extended",
                          "content": "The deadline for CS301 Data Structures lab assignment has been extended by one week. New deadline: March 10th.",
                          "category": "Announcement", "priority": "Medium"},
               token=S["tok_hod_cse"])
pause(CD_WRITE)
S["notice_id_hod"] = body.get("id") if isinstance(body, dict) else None
T("N6: HOD CSE notice created (200/201)", sc in (200, 201), f"sc={sc}")
T("N6: Scope auto-locked to CSE dept",
  isinstance(body, dict) and body.get("target_departments") == ["CSE"],
  f"got depts={body.get('target_departments') if isinstance(body, dict) else '?'}")

pause(CD_READ)

# N7: Male hostel student can see Men's Hostel Warden notice
log("  [N7] Male hostel student fetches notice feed")
sc, body = req("GET", NOTICE_FEED, token=S["tok_s_mh"])
pause(CD_READ)
T("N7: Male hostel student notice feed returns 200", sc == 200, f"sc={sc}")
if sc == 200 and isinstance(body, dict):
    notice_ids = [n.get("id") for n in body.get("notices", [])]
    has_mh = S.get("notice_id_mh") in notice_ids
    T("N7: Male hostel student sees Men's Hostel Warden notice",
      has_mh,
      f"notice_id_mh={S.get('notice_id_mh')}, ids_in_feed={notice_ids[:5]}")
else:
    SKIP("N7: MH notice visibility check", f"feed sc={sc}")

# N8: Female hostel student CANNOT see Men's Hostel notice
log("  [N8] Female hostel student fetches feed — should NOT see MH notice")
sc, body = req("GET", NOTICE_FEED, token=S["tok_s_wh"])
pause(CD_READ)
T("N8: Female hostel student feed returns 200", sc == 200, f"sc={sc}")
if sc == 200 and isinstance(body, dict) and S.get("notice_id_mh"):
    notice_ids = [n.get("id") for n in body.get("notices", [])]
    not_visible = S["notice_id_mh"] not in notice_ids
    T("N8: Female hostel student does NOT see Men's Hostel notice",
      not_visible, f"notice_id_mh={S['notice_id_mh']}, ids={notice_ids[:5]}")
else:
    SKIP("N8: MH notice gender exclusion check", "no notice id or feed failed")

# N9: Day Scholar CANNOT see Men's Hostel notice
log("  [N9] Day Scholar fetches feed — should NOT see MH notice")
sc, body = req("GET", NOTICE_FEED, token=S["tok_s_gen"])
pause(CD_READ)
T("N9: Day Scholar notice feed returns 200", sc == 200, f"sc={sc}")
if sc == 200 and isinstance(body, dict) and S.get("notice_id_mh"):
    notice_ids = [n.get("id") for n in body.get("notices", [])]
    not_visible = S["notice_id_mh"] not in notice_ids
    T("N9: Day Scholar does NOT see Men's Hostel notice",
      not_visible, f"notice_id_mh={S['notice_id_mh']}, ids={notice_ids[:5]}")
else:
    SKIP("N9: MH notice day-scholar exclusion", "no notice id or feed failed")

# N10: Admin notice visible to ALL student types
log("  [N10] All student types see admin campus-wide notice")
if S.get("notice_id_admin"):
    for label, tok_key in [("Male Hostel", "tok_s_mh"), ("Female Hostel", "tok_s_wh"),
                           ("Day Scholar", "tok_s_gen"), ("CSE Hostel", "tok_s_cse")]:
        sc, body = req("GET", NOTICE_FEED, token=S[tok_key])
        pause(CD_READ)
        if sc == 200 and isinstance(body, dict):
            ids = [n.get("id") for n in body.get("notices", [])]
            T(f"N10: {label} student sees admin notice",
              S["notice_id_admin"] in ids,
              f"admin_id={S['notice_id_admin']}, ids={ids[:5]}")
        else:
            SKIP(f"N10: {label} admin notice visibility", f"sc={sc}")
else:
    for _ in range(4): SKIP("N10: Admin notice visibility", "no admin notice id")

# N11: CSE student sees HOD CSE notice; ECE student does NOT
log("  [N11] HOD CSE notice: CSE sees it, ECE does not")
if S.get("notice_id_hod"):
    sc, body = req("GET", NOTICE_FEED, token=S["tok_s_cse"])
    pause(CD_READ)
    if sc == 200 and isinstance(body, dict):
        ids = [n.get("id") for n in body.get("notices", [])]
        T("N11: CSE student sees HOD CSE notice",
          S["notice_id_hod"] in ids,
          f"hod_id={S['notice_id_hod']}, ids={ids[:5]}")
    else:
        SKIP("N11: CSE student HOD notice visibility", f"sc={sc}")

    sc, body = req("GET", NOTICE_FEED, token=S["tok_s_ece"])
    pause(CD_READ)
    if sc == 200 and isinstance(body, dict):
        ids = [n.get("id") for n in body.get("notices", [])]
        T("N11: ECE student does NOT see HOD CSE notice",
          S["notice_id_hod"] not in ids,
          f"hod_id={S['notice_id_hod']}, ids={ids[:5]}")
    else:
        SKIP("N11: ECE exclusion from HOD CSE notice", f"sc={sc}")
else:
    SKIP("N11: HOD CSE notice dept filtering", "no hod notice id")
    SKIP("N11: ECE exclusion from HOD CSE notice", "no hod notice id")

# N12: Authority can list their own notices
log("  [N12] Men's Hostel Warden lists own notices")
sc, body = req("GET", "/api/authorities/my-notices", token=S["tok_warden_m"])
pause(CD_READ)
T("N12: GET /my-notices returns 200", sc == 200, f"sc={sc}")
if sc == 200 and isinstance(body, dict) and S.get("notice_id_mh"):
    ids = [n.get("id") for n in body.get("notices", [])]
    T("N12: Own notice appears in my-notices list",
      S["notice_id_mh"] in ids,
      f"notice_id_mh={S['notice_id_mh']}, ids={ids}")
else:
    SKIP("N12: Own notice in my-notices", "list failed or no notice id")

# N13: Authority can deactivate their notice
log("  [N13] Men's Hostel Warden deactivates their notice")
if S.get("notice_id_mh"):
    sc, body = req("DELETE", f"{NOTICE_BASE}/{S['notice_id_mh']}", token=S["tok_warden_m"])
    pause(CD_WRITE)
    T("N13: Deactivate own notice returns 200", sc == 200, f"sc={sc}")

    sc2, body2 = req("GET", NOTICE_FEED, token=S["tok_s_mh"])
    pause(CD_READ)
    if sc2 == 200 and isinstance(body2, dict):
        ids = [n.get("id") for n in body2.get("notices", [])]
        T("N13: Deactivated notice no longer in student feed",
          S["notice_id_mh"] not in ids,
          f"notice_id_mh={S['notice_id_mh']}, ids={ids[:5]}")
    else:
        SKIP("N13: Post-deactivate feed check", f"feed sc={sc2}")
else:
    SKIP("N13: Notice deactivation", "no notice id")
    SKIP("N13: Post-deactivate visibility check", "no notice id")

# N14: Another authority cannot deactivate someone else's notice
log("  [N14] Women's Hostel Warden tries to deactivate HOD notice (403/404)")
if S.get("notice_id_hod"):
    sc, body = req("DELETE", f"{NOTICE_BASE}/{S['notice_id_hod']}", token=S["tok_warden_w"])
    pause(CD_WRITE)
    T("N14: Cannot deactivate another authority's notice (403/404)",
      sc in (403, 404), f"sc={sc}")
else:
    SKIP("N14: Cross-authority deactivation blocked", "no hod notice id")

# N15: Student cannot POST a notice
log("  [N15] Student tries to POST a notice (should be 401/403)")
sc, body = req("POST", NOTICE_BASE,
               json_data={"title": "Student fake notice",
                          "content": "Students should not be allowed to create notices.",
                          "category": "General", "priority": "Low"},
               token=S["tok_s_obs"])
pause(CD_WRITE)
T("N15: Student cannot create notice (401/403)", sc in (401, 403), f"sc={sc}")

# N16: Admin can deactivate any notice
log("  [N16] Admin deactivates Women's Hostel Warden notice")
if S.get("notice_id_wh"):
    sc, body = req("DELETE", f"{NOTICE_BASE}/{S['notice_id_wh']}", token=S["tok_admin"])
    pause(CD_WRITE)
    T("N16: Admin deactivates another authority's notice (200)", sc == 200, f"sc={sc}")
else:
    SKIP("N16: Admin deactivate any notice", "no WH notice id")

# N17: Women's Hostel Warden cannot target Male students
log("  [N17] Women's Hostel Warden tries to target Male students (403)")
sc, body = req("POST", NOTICE_BASE,
               json_data={"title": "Blocked notice",
                          "content": "Women's warden must not target male students.",
                          "category": "General", "priority": "Low",
                          "target_gender": ["Male"]},
               token=S["tok_warden_w"])
pause(CD_WRITE)
T("N17: Women's Warden blocked from targeting Male (403)", sc == 403, f"sc={sc}")

# N18: Student notice feed without auth returns 401
log("  [N18] Student notice feed without auth")
sc, body = req("GET", NOTICE_FEED)
pause(CD_READ)
T("N18: Notice feed without auth -> 401", sc == 401, f"sc={sc}")

# N19: Admin's campus notice not deactivated — Day Scholar can still see it
log("  [N19] Admin campus-wide notice (not yet deactivated) — Day Scholar sees it")
if S.get("notice_id_admin"):
    sc, body = req("GET", NOTICE_FEED, token=S["tok_s_gen"])
    pause(CD_READ)
    if sc == 200 and isinstance(body, dict):
        ids = [n.get("id") for n in body.get("notices", [])]
        T("N19: Day Scholar still sees active admin notice",
          S["notice_id_admin"] in ids,
          f"admin_id={S['notice_id_admin']}, ids={ids[:5]}")
    else:
        SKIP("N19: Day Scholar admin notice visibility", f"sc={sc}")
else:
    SKIP("N19: Admin notice visibility", "no admin notice id")


# ════════════════════════════════════════════════════════════════════════════
#  FINAL SUMMARY
# ════════════════════════════════════════════════════════════════════════════

total   = passed + failed + skipped
pct     = (passed / max(1, passed + failed)) * 100
verdict = "PASS" if pct >= PASS_THRESHOLD else "NEEDS WORK"

log(f"\n{'='*72}")
log(f"  FINAL RESULTS — {_now()}")
log(f"{'='*72}")
log(f"  Total Tests : {total}")
log(f"  Passed      : {passed}")
log(f"  Failed      : {failed}")
log(f"  Skipped     : {skipped}")
log(f"  Pass Rate   : {pct:.1f}%  [{verdict}]  (threshold={PASS_THRESHOLD}%)")
log(f"{'='*72}")

if failures:
    log(f"\n  FAILED TESTS ({len(failures)}):")
    for f_item in failures:
        log(f"    {f_item}")

log(f"\n  Run suffix    : {RUN_TS}")
log(f"  Comp students : {S['s1_roll']}, {S['s2_roll']}, {S['s3_roll']}, {S['s4_roll']}")
log(f"  LLM students  : {S['mh_roll']}, {S['wh_roll']}, {S['gen_roll']}, "
    f"{S['cse_roll']}, {S['ece_roll']}, {S['dc_roll']}")
log(f"  Comp cids     : s1={S['cid_s1']}, s2={S['cid_s2']}, "
    f"dept={S['cid_s1_dept']}, gen={S['cid_s1_gen']}, s3={S['cid_s3']}")
log(f"  LLM cids      : mh={S.get('mh_cid')}, wh={S.get('wh_cid')}, "
    f"gen={S.get('gen_cid')}, dc={S.get('dc_cid')}, upd={S.get('upd_cid')}")
log(f"  Full log      : {os.path.abspath(LOG_FILE)}")
log(f"  Credentials   : {os.path.abspath(CRED_FILE)}")

_log_fh.close()

if pct < PASS_THRESHOLD:
    sys.exit(1)
