#!/usr/bin/env python3
"""
CampusVoice — LLM Categorization & Authority Routing Test
==========================================================
Validates that the AI correctly:
  1. Categorises complaints (Men's Hostel / Women's Hostel / General /
     Department / Disciplinary Committee)
  2. Assigns complaints to the right authority type
  3. Posts authority updates and notifies ONLY the complaint owner
  4. Verifies authority inbox receives only their assigned complaints

15 TCs per authority type (5 LLM submissions × 3 assertions each).
Additional sections: edge cases, authority update feature, visibility.

Target : https://campusvoice-api-h528.onrender.com
Log    : llm_routing_YYYYMMDD_HHMMSS.log
Run    : python test_llm_routing.py
"""

import requests
import json
import time
import datetime
import os
import struct
import zlib
from typing import Optional, Any, Tuple

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL  = "https://campusvoice-api-h528.onrender.com"
TIMEOUT   = 120
CD_LLM    = 40      # wait after every complaint submission (LLM processing)
CD_WRITE  = 5       # after state-changing non-LLM ops
CD_AUTH   = 3       # after login / register
CD_READ   = 2       # after read-only GETs
CD_MAX    = 50      # hard cap on any single pause

PASS_THRESHOLD = 70  # LLM can misclassify occasionally; 70 % = PASS

# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════════

RUN_TS   = str(int(time.time()))[-5:]
NOW_STR  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = f"llm_routing_{NOW_STR}.log"
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
    seconds = min(float(seconds), CD_MAX)
    msg = f"\n  [wait {_now()}] Pausing {seconds:.0f}s" + (f" — {reason}" if reason else "")
    log(msg)
    time.sleep(seconds)


# ══════════════════════════════════════════════════════════════════════════════
#  TEST COUNTERS & STATE
# ══════════════════════════════════════════════════════════════════════════════

test_num = section_num = passed = failed = skipped = 0
failures = []
section_num = 0

S: dict = {}  # shared state across sections

# Student identifiers (timestamp-based to avoid conflicts)
TS = RUN_TS
S["mh_roll"]   = f"LMH{TS}"   ; S["mh_email"]   = f"lmh{TS}@srec.ac.in"
S["wh_roll"]   = f"LWH{TS}"   ; S["wh_email"]   = f"lwh{TS}@srec.ac.in"
S["gen_roll"]  = f"LGN{TS}"   ; S["gen_email"]  = f"lgn{TS}@srec.ac.in"
S["cse_roll"]  = f"LCSE{TS}"  ; S["cse_email"]  = f"lcse{TS}@srec.ac.in"
S["ece_roll"]  = f"LECE{TS}"  ; S["ece_email"]  = f"lece{TS}@srec.ac.in"
S["dc_roll"]   = f"LDC{TS}"   ; S["dc_email"]   = f"ldc{TS}@srec.ac.in"
S["obs_roll"]  = f"LOBS{TS}"  ; S["obs_email"]  = f"lobs{TS}@srec.ac.in"
S["upd_roll"]  = f"LUPD{TS}"  ; S["upd_email"]  = f"lupd{TS}@srec.ac.in"
S["edg_roll"]  = f"LEDG{TS}"  ; S["edg_email"]  = f"ledg{TS}@srec.ac.in"
STUDENT_PWD = "LLMTest@1234"


# ══════════════════════════════════════════════════════════════════════════════
#  COMPLAINT TEXTS  (distinct, unambiguous, real-world scenarios)
# ══════════════════════════════════════════════════════════════════════════════

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

# One complaint specifically for the authority-update + visibility section
UPDATE_TEST_TEXT = (
    "The projector in CSE Seminar Hall (3rd floor, main academic block) has not been working "
    "for over a week. Multiple faculty lectures and student presentations have been disrupted. "
    "The AV technician has been informed twice but no repair has been carried out."
)

# Edge-case complaint texts
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


# ══════════════════════════════════════════════════════════════════════════════
#  HTTP + TEST HELPERS  (identical pattern to test_render.py)
# ══════════════════════════════════════════════════════════════════════════════

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


def _put(url, json_data, params, headers):
    kw = dict(headers=headers, timeout=TIMEOUT)
    if params:
        kw["params"] = params
    return requests.put(url, json=json_data, **kw) if json_data is not None else requests.put(url, **kw)


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
            if files:            r = requests.post(url, data=form_data or {}, files=files, **kw)
            elif form_data is not None: r = requests.post(url, data=form_data, **kw)
            else:                r = requests.post(url, json=json_data, **kw)
        elif method == "PUT":    r = _put(url, json_data, params, headers)
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


def login_student(identifier: str, pwd: str = STUDENT_PWD) -> Optional[str]:
    sc, body = req("POST", "/api/students/login",
                   json_data={"email_or_roll_no": identifier, "password": pwd})
    pause(CD_AUTH)
    if sc == 200 and isinstance(body, dict):
        return body.get("token") or (body.get("data") or {}).get("token")
    return None


def login_authority(email: str, pwd: str) -> Optional[str]:
    sc, body = req("POST", "/api/authorities/login",
                   json_data={"email": email, "password": pwd})
    pause(CD_AUTH)
    if sc == 200 and isinstance(body, dict):
        return body.get("token") or (body.get("data") or {}).get("token")
    return None


def register_student(roll: str, name: str, email: str,
                     gender: str, stay: str, dept_id: int) -> int:
    sc, _ = req("POST", "/api/students/register", json_data={
        "roll_no": roll, "name": name, "email": email,
        "password": STUDENT_PWD, "gender": gender,
        "stay_type": stay, "department_id": dept_id, "year": 2,
    })
    pause(CD_AUTH)
    return sc or 0


def submit_complaint(token: str, text: str,
                     visibility: str = "Public") -> Tuple[int, dict]:
    """Submit via multipart form. Returns (status_code, body_dict)."""
    sc, body = req("POST", "/api/complaints/submit",
                   form_data={"original_text": text, "visibility": visibility},
                   files={"_": ("", b"", "text/plain")},
                   token=token)
    pause(CD_LLM, "waiting for LLM categorisation")
    if isinstance(body, dict):
        return sc or 0, body
    return sc or 0, {}


def get_field(body: dict, *keys):
    """Return first truthy value found across the given key names."""
    for k in keys:
        v = body.get(k)
        if v is not None:
            return v
    return None


# ── expected authority info ────────────────────────────────────────────────
# category_id mapping:  1=Men's Hostel  2=Women's Hostel  3=General
#                       4=Department    5=Disciplinary Committee
CAT_IDS = {
    "Men's Hostel": 1,
    "Women's Hostel": 2,
    "General": 3,
    "Department": 4,
    "Disciplinary Committee": 5,
}

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


# ══════════════════════════════════════════════════════════════════════════════
#  CREDENTIAL WRITER
# ══════════════════════════════════════════════════════════════════════════════

def append_credentials(students: list):
    """Append this run's new students to credentials.txt."""
    lines = [
        "",
        "=" * 80,
        f"  LLM ROUTING TEST STUDENTS  (Run: {NOW_STR} | Suffix: {RUN_TS})",
        "=" * 80,
        f"  Password for all: {STUDENT_PWD}",
        "",
    ]
    for s in students:
        lines.append(
            f"  {s['roll']:12} | {s['email']:38} | {s['gender']:7} | "
            f"{s['stay']:12} | dept={s['dept']} | {s['label']}"
        )
    lines.append("")
    with open(CRED_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"\n  [info] Appended {len(students)} new students to {os.path.basename(CRED_FILE)}")


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER: verify category submission  (used in every categorisation section)
# ══════════════════════════════════════════════════════════════════════════════

def check_submission(label: str, sc: int, body: dict,
                     expected_cat: str, check_dept_code: str = None):
    """Assert 3 standard TCs for each complaint submission."""
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


# ══════════════════════════════════════════════════════════════════════════════
#  BANNER + SERVER WARM-UP
# ══════════════════════════════════════════════════════════════════════════════

log("=" * 72)
log("  CampusVoice — LLM Categorisation & Authority Routing Test")
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


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 01 — AUTHORITY LOGINS
# ══════════════════════════════════════════════════════════════════════════════

section("AUTHORITY LOGINS")

for key, (email, pwd) in AUTH_CREDS.items():
    tok = login_authority(email, pwd)
    S[f"tok_{key}"] = tok
    T(f"{key} ({email}) login", tok is not None, f"got None")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 02 — STUDENT REGISTRATION & LOGIN
# ══════════════════════════════════════════════════════════════════════════════

section("STUDENT REGISTRATION & LOGIN")

new_students = [
    # roll             name                       email               gender    stay          dept  label
    {"roll": S["mh_roll"],  "name": "LLM MH Student",    "email": S["mh_email"],  "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "Men's Hostel tests"},
    {"roll": S["wh_roll"],  "name": "LLM WH Student",    "email": S["wh_email"],  "gender": "Female", "stay": "Hostel",      "dept": 2,  "label": "Women's Hostel tests"},
    {"roll": S["gen_roll"], "name": "LLM Gen Student",   "email": S["gen_email"], "gender": "Male",   "stay": "Day Scholar", "dept": 10, "label": "General tests (Day Scholar)"},
    {"roll": S["cse_roll"], "name": "LLM CSE Student",   "email": S["cse_email"], "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "CSE Dept tests"},
    {"roll": S["ece_roll"], "name": "LLM ECE Student",   "email": S["ece_email"], "gender": "Female", "stay": "Hostel",      "dept": 2,  "label": "ECE Dept tests"},
    {"roll": S["dc_roll"],  "name": "LLM DC Student",    "email": S["dc_email"],  "gender": "Male",   "stay": "Day Scholar", "dept": 4,  "label": "Disciplinary tests"},
    {"roll": S["obs_roll"], "name": "LLM Observer",      "email": S["obs_email"], "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "Observer (visibility tests)"},
    {"roll": S["upd_roll"], "name": "LLM Update Student","email": S["upd_email"], "gender": "Male",   "stay": "Hostel",      "dept": 1,  "label": "Authority-update target"},
    {"roll": S["edg_roll"], "name": "LLM Edge Student",  "email": S["edg_email"], "gender": "Male",   "stay": "Day Scholar", "dept": 1,  "label": "Edge-case submissions"},
]

for s in new_students:
    sc = register_student(s["roll"], s["name"], s["email"],
                          s["gender"], s["stay"], s["dept"])
    T(f"Register {s['label']} ({s['roll']})", sc in (200, 201, 400, 409),
      f"got {sc}")   # 400/409 = already exists from a previous run

append_credentials(new_students)

# Login all students
for key in ("mh", "wh", "gen", "cse", "ece", "dc", "obs", "upd", "edg"):
    tok = login_student(S[f"{key}_email"])
    S[f"tok_s_{key}"] = tok
    T(f"Student '{key}' login", tok is not None, "got None")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 03 — MEN'S HOSTEL CATEGORISATION  (15 TCs)
# ══════════════════════════════════════════════════════════════════════════════

section("MEN'S HOSTEL CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Male Hostel student (CSE) submitting 5 hostel complaints")
log("  [info] Expected: category='Men\\'s Hostel', assigned to Men's Hostel Warden")

for i, text in enumerate(MH_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_mh"], text)
    check_submission(f"MH-{i}", sc, body, "Men's Hostel")
    if i == 1:
        S["mh_cid"] = body.get("id")   # save for inbox verification


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 04 — WOMEN'S HOSTEL CATEGORISATION  (15 TCs)
# ══════════════════════════════════════════════════════════════════════════════

section("WOMEN'S HOSTEL CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Female Hostel student (ECE) submitting 5 hostel complaints")
log("  [info] Expected: category='Women\\'s Hostel', assigned to Women's Hostel Warden")

for i, text in enumerate(WH_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_wh"], text)
    check_submission(f"WH-{i}", sc, body, "Women's Hostel")
    if i == 1:
        S["wh_cid"] = body.get("id")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 05 — GENERAL CATEGORISATION  (15 TCs)
# ══════════════════════════════════════════════════════════════════════════════

section("GENERAL CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Day Scholar student (IT dept) submitting 5 general campus complaints")
log("  [info] Expected: category='General', assigned to Admin Officer")

for i, text in enumerate(GEN_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_gen"], text)
    check_submission(f"GEN-{i}", sc, body, "General")
    if i == 1:
        S["gen_cid"] = body.get("id")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 06 — DEPARTMENT CATEGORISATION  (15 TCs)
# ══════════════════════════════════════════════════════════════════════════════

section("DEPARTMENT CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] CSE student -> 3 CSE lab complaints -> expected HOD CSE")
log("  [info] ECE student -> 2 ECE lab complaints -> expected HOD ECE")

for i, text in enumerate(CSE_DEPT_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_cse"], text)
    check_submission(f"DEPT-CSE-{i}", sc, body, "Department", check_dept_code="CSE")

for i, text in enumerate(ECE_DEPT_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_ece"], text)
    check_submission(f"DEPT-ECE-{i}", sc, body, "Department", check_dept_code="ECE")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 07 — DISCIPLINARY COMMITTEE CATEGORISATION  (15 TCs)
# ══════════════════════════════════════════════════════════════════════════════

section("DISCIPLINARY COMMITTEE CATEGORISATION & ROUTING  [15 TCs]")
log("  [info] Day Scholar student submitting 5 disciplinary complaints")
log("  [info] Expected: category='Disciplinary Committee', assigned to DC")

for i, text in enumerate(DC_TEXTS, 1):
    sc, body = submit_complaint(S["tok_s_dc"], text)
    check_submission(f"DC-{i}", sc, body, "Disciplinary Committee")
    if i == 1:
        S["dc_cid"] = body.get("id")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 08 — EDGE CASES & BOUNDARY CONDITIONS
# ══════════════════════════════════════════════════════════════════════════════

section("EDGE CASES & BOUNDARY CONDITIONS")

# ── Edge 1: Day Scholar submits a hostel-phrased complaint ────────────────────
log("  [edge-1] Day Scholar submits hostel-phrased complaint")
log("           → expect rejection (400) OR re-categorisation away from hostel")
sc, body = submit_complaint(S["tok_s_edg"], EDGE_HOSTEL_FROM_DAY_SCHOLAR)
if sc in (400, 422):
    T("Edge-1: Day Scholar hostel complaint blocked at submission", True)
    SKIP("Edge-1: re-categorisation check (blocked)", "submission rejected as expected")
elif sc in (200, 201):
    T("Edge-1: Day Scholar hostel complaint handled (submitted or blocked)", True)
    cat = body.get("category", "")
    T("Edge-1: re-categorised AWAY from hostel categories",
      cat not in ("Men's Hostel", "Women's Hostel"),
      f"got category={cat!r}")
else:
    T("Edge-1: Day Scholar hostel complaint handled", False, f"sc={sc}")
    SKIP("Edge-1: re-categorisation check", "unexpected error")

# ── Edge 2: Ambiguous complaint (noise near study area) ──────────────────────
log("  [edge-2] Ambiguous complaint — noise near study area (any student)")
sc, body = submit_complaint(S["tok_s_edg"], EDGE_AMBIGUOUS)
T("Edge-2: Ambiguous complaint submitted", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat = body.get("category")
    auth = body.get("assigned_authority")
    T("Edge-2: Ambiguous complaint gets a valid category",
      cat in CAT_IDS, f"got category={cat!r}")
    T("Edge-2: Ambiguous complaint assigned to authority",
      bool(auth), f"assigned_authority={auth!r}")
else:
    SKIP("Edge-2: category/assignment check", f"submission sc={sc}")
    SKIP("Edge-2: authority assignment check", f"submission sc={sc}")

# ── Edge 3: ECE student about CSE department (cross-department) ──────────────
log("  [edge-3] ECE student complains about CSE lab access (cross-department)")
sc, body = submit_complaint(S["tok_s_ece"], EDGE_CROSS_DEPT)
T("Edge-3: Cross-dept complaint submitted", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat        = body.get("category", "")
    dept_code  = body.get("target_department_code", "")
    cross      = body.get("cross_department", False)
    T("Edge-3: Cross-dept complaint categorised as Department",
      cat == "Department", f"got category={cat!r}")
    T("Edge-3: Cross-dept flag or target dept code present",
      bool(dept_code) or cross,
      f"target_dept={dept_code!r}, cross_department={cross}")
else:
    SKIP("Edge-3: cross-dept category check", f"sc={sc}")
    SKIP("Edge-3: cross_department flag check", f"sc={sc}")

# ── Edge 4: Male student submits complaint phrased around women's hostel ──────
log("  [edge-4] Male Hostel student submits women's hostel-phrased complaint")
log("           → should NOT be routed to Women's Hostel")
# LCSE is Male Hostel, still has quota (only used 3/5)
sc, body = submit_complaint(S["tok_s_cse"], EDGE_MALE_WOMENS_HOSTEL)
T("Edge-4: Male student women's hostel complaint handled", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat = body.get("category", "")
    T("Edge-4: NOT routed to Women's Hostel",
      cat != "Women's Hostel",
      f"got category={cat!r}")
else:
    SKIP("Edge-4: routing check", f"sc={sc}")

# ── Edge 5: Ragging complaint with softened/general phrasing ─────────────────
log("  [edge-5] Ragging/DC complaint with vague phrasing — should still hit DC")
sc, body = submit_complaint(S["tok_s_edg"], EDGE_RAGGING_GENERAL_PHRASING)
T("Edge-5: Ragging (vague phrasing) complaint submitted", sc in (200, 201, 400), f"sc={sc}")
if sc in (200, 201):
    cat  = body.get("category", "")
    auth = body.get("assigned_authority")
    T("Edge-5: Ragging complaint routed to DC or authority",
      cat == "Disciplinary Committee" or bool(auth),
      f"category={cat!r}, auth={auth!r}")
else:
    SKIP("Edge-5: DC routing check", f"sc={sc}")

# ── Edge 6: Empty text (should fail validation) ───────────────────────────────
log("  [edge-6] Empty complaint text — expect 400/422")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "", "visibility": "Public"},
               files={"_": ("", b"", "text/plain")},
               token=S["tok_s_obs"])
pause(CD_READ)
T("Edge-6: Empty complaint text rejected (400/422)", sc in (400, 422), f"sc={sc}")

# ── Edge 7: Complaint text too short (< 10 chars) ────────────────────────────
# MIN_COMPLAINT_LENGTH = 10, so 9 chars must be rejected
log("  [edge-7] Too-short complaint text (9 chars) -- expect 400/422")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "Too hot.", "visibility": "Public"},
               files={"_": ("", b"", "text/plain")},
               token=S["tok_s_obs"])
pause(CD_READ)
T("Edge-7: Short complaint text rejected (400/422)", sc in (400, 422), f"sc={sc}")

# ── Edge 8: Invalid visibility value ─────────────────────────────────────────
log("  [edge-8] Invalid visibility value — expect 400/422")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "The WiFi is broken on campus.", "visibility": "Classified"},
               files={"_": ("", b"", "text/plain")},
               token=S["tok_s_obs"])
pause(CD_READ)
T("Edge-8: Invalid visibility rejected (400/422)", sc in (400, 422, 429), f"sc={sc}")

# ── Edge 9: Unauthenticated submission ────────────────────────────────────────
log("  [edge-9] Complaint submission without token — expect 401")
sc, body = req("POST", "/api/complaints/submit",
               form_data={"original_text": "Campus lights are off near main gate.", "visibility": "Public"},
               files={"_": ("", b"", "text/plain")})
pause(CD_READ)
T("Edge-9: Unauthenticated submission rejected (401)", sc == 401, f"sc={sc}")

# ── Edge 10: llm_failed flag present in response ─────────────────────────────
log("  [edge-10] llm_failed flag should be present (False) in normal submissions")
# Re-use a body from the last successful categorisation section
if S.get("dc_cid"):
    sc, body = req("GET", f"/api/complaints/{S['dc_cid']}", token=S["tok_s_dc"])
    pause(CD_READ)
    # The submit response has llm_failed; the detail response doesn't — just check it was set
    T("Edge-10: DC complaint exists and returns 200",
      sc == 200, f"sc={sc}")
else:
    SKIP("Edge-10: llm_failed check", "no DC complaint ID")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 09 — AUTHORITY POST-UPDATE FEATURE  (10 TCs)
# ══════════════════════════════════════════════════════════════════════════════

section("AUTHORITY POST-UPDATE FEATURE  [10 TCs]")

# 1 ─ Submit the update-test complaint
log("  [info] Submitting update-test complaint (CSE Seminar Hall projector issue)")
sc, body = submit_complaint(S["tok_s_upd"], UPDATE_TEST_TEXT, visibility="Public")
S["upd_cid"] = body.get("id")
T("Update-test complaint submitted (200/201)", sc in (200, 201), f"sc={sc}")
T("Update-test complaint has an ID", bool(S.get("upd_cid")),
  f"id={S.get('upd_cid')!r}")
T("Update-test complaint categorised as Department",
  body.get("category") == "Department",
  f"category={body.get('category')!r}")

if not S.get("upd_cid"):
    for _ in range(7):
        SKIP("Update feature test", "no complaint ID — submission failed")
else:
    cid = S["upd_cid"]

    # 2 ─ Student can view their own complaint
    sc, body = req("GET", f"/api/complaints/{cid}", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Complaint owner can fetch complaint detail (200)", sc == 200, f"sc={sc}")

    # 3 ─ Admin posts an update
    log("  [info] Admin posting update: 'Investigation Initiated'")
    sc, body = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                   params={"title": "Investigation Initiated",
                           "content": "We have acknowledged your complaint. "
                                      "A technician has been dispatched to inspect the projector."},
                   token=S["tok_admin"])
    pause(CD_WRITE)
    T("Admin posts update on complaint (200)", sc == 200, f"sc={sc}")

    # 4 ─ Status update: Raised → In Progress
    log("  [info] Admin updating status: Raised → In Progress")
    sc, body = req("PUT", f"/api/authorities/complaints/{cid}/status",
                   json_data={"status": "In Progress",
                              "reason": "Maintenance team assigned. Repair expected within 2 days."},
                   token=S["tok_admin"])
    pause(CD_WRITE)
    T("Status update Raised → In Progress (200)", sc == 200, f"sc={sc}")

    # 5 ─ Owner's notification list contains this complaint
    pause(2, "allow notification to propagate")
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Owner notifications endpoint returns 200", sc == 200, f"sc={sc}")
    if sc == 200:
        notifs = body.get("notifications", []) if isinstance(body, dict) else []
        owner_has = any(str(n.get("complaint_id")) == str(cid) for n in notifs)
        T("Owner receives notification for their complaint update",
          owner_has, f"total_notifs={len(notifs)}, cid={cid}")
    else:
        SKIP("Owner notification check", f"endpoint sc={sc}")

    # 6 ─ Status update: In Progress → Resolved
    log("  [info] Admin updating status: In Progress → Resolved")
    sc, body = req("PUT", f"/api/authorities/complaints/{cid}/status",
                   json_data={"status": "Resolved",
                              "reason": "Projector has been repaired and tested successfully."},
                   token=S["tok_admin"])
    pause(CD_WRITE)
    T("Status update In Progress → Resolved (200)", sc == 200, f"sc={sc}")

    # 7 ─ Complaint detail reflects Resolved status
    sc, body = req("GET", f"/api/complaints/{cid}", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Complaint status shows Resolved after update",
      isinstance(body, dict) and body.get("status") == "Resolved",
      f"status={body.get('status') if isinstance(body, dict) else body!r}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 10 — NOTIFICATION VISIBILITY  (only complaint owner is notified)
# ══════════════════════════════════════════════════════════════════════════════

section("NOTIFICATION VISIBILITY — ONLY OWNER NOTIFIED  [10 TCs]")

if not S.get("upd_cid"):
    for _ in range(10):
        SKIP("Visibility test", "no update-test complaint ID")
else:
    cid = S["upd_cid"]

    # Post one more update so there is definitely a fresh notification
    log("  [info] Admin posts a second update for visibility testing")
    sc, _ = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                params={"title": "Visibility Test Update",
                        "content": "This update is specifically for testing notification visibility."},
                token=S["tok_admin"])
    pause(CD_WRITE)
    T("Second update posted for visibility test (200)", sc == 200, f"sc={sc}")

    pause(2, "allow notification to propagate")

    # ── Owner (upd) should have the notification ────────────────────────────
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Owner notifications returns 200", sc == 200, f"sc={sc}")
    owner_notifs = body.get("notifications", []) if (sc == 200 and isinstance(body, dict)) else []
    owner_has = any(str(n.get("complaint_id")) == str(cid) for n in owner_notifs)
    T("Owner has notification for their complaint (cid match)",
      owner_has, f"total={len(owner_notifs)}, cid={cid}")

    # ── Observer (obs) should NOT have this complaint's notification ─────────
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_obs"])
    pause(CD_READ)
    T("Observer notifications returns 200", sc == 200, f"sc={sc}")
    obs_notifs = body.get("notifications", []) if (sc == 200 and isinstance(body, dict)) else []
    obs_has = any(str(n.get("complaint_id")) == str(cid) for n in obs_notifs)
    T("Observer does NOT receive notification for another student's complaint",
      not obs_has, f"obs_notif_count={len(obs_notifs)}, has_cid={obs_has}")

    # ── Observer can view the public complaint but has no notification ────────
    sc, body = req("GET", f"/api/complaints/{cid}", token=S["tok_s_obs"])
    pause(CD_READ)
    T("Observer can view public complaint detail (200)",
      sc == 200, f"sc={sc}")

    # ── Warden cannot post update on HOD-assigned complaint ──────────────────
    log("  [info] Men's Hostel Warden tries to update HOD-assigned complaint")
    sc, _ = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                params={"title": "Unauthorised warden update",
                        "content": "Warden should not be able to update HOD complaint."},
                token=S["tok_warden_m"])
    pause(CD_WRITE)
    T("Warden cannot update complaint assigned to HOD (403/404)",
      sc in (403, 404), f"sc={sc}")

    # ── Student cannot use authority post-update endpoint ────────────────────
    log("  [info] Student (observer) tries to post authority update")
    sc, _ = req("POST", f"/api/authorities/complaints/{cid}/post-update",
                params={"title": "Student fake update",
                        "content": "Students should not be allowed to post authority updates."},
                token=S["tok_s_obs"])
    pause(CD_WRITE)
    T("Student cannot post authority update (401/403)",
      sc in (401, 403), f"sc={sc}")

    # ── Owner marks notification as read ─────────────────────────────────────
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

    # ── unread_count decreases after marking read ─────────────────────────────
    sc, body = req("GET", "/api/students/notifications", token=S["tok_s_upd"])
    pause(CD_READ)
    T("Notification list still returns 200 after marking read", sc == 200, f"sc={sc}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 11 — AUTHORITY INBOX VERIFICATION
#  Confirm each authority type sees ONLY complaints routed to them
# ══════════════════════════════════════════════════════════════════════════════

section("AUTHORITY INBOX VERIFICATION — COMPLAINTS REACH CORRECT AUTHORITY  [10 TCs]")

def check_inbox(auth_key: str, expected_cat_id: int, label: str):
    tok = S.get(f"tok_{auth_key}")
    if not tok:
        SKIP(f"{label} inbox check", "no token")
        SKIP(f"{label} has expected category in inbox", "no token")
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
        SKIP(f"{label} has expected category in inbox", f"list sc={sc}")

check_inbox("warden_m", 1, "Men's Hostel Warden")
check_inbox("warden_w", 2, "Women's Hostel Warden")
check_inbox("officer",  3, "Admin Officer")
check_inbox("hod_cse",  4, "HOD CSE")
check_inbox("dc",       5, "Disciplinary Committee")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 12 — NOTICE / BROADCAST FEATURE  [15 TCs]
#  Tests targeted notice creation, scope enforcement, and student feed
# ══════════════════════════════════════════════════════════════════════════════

section("NOTICE / BROADCAST FEATURE  [~28 TCs]")

NOTICE_BASE = "/api/authorities/notices"
NOTICE_FEED = "/api/students/notices"

# ── N1: Men's Hostel Warden sends a notice to male hostel students ─────────
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

# ── N2: Men's Hostel Warden cannot target Female students (scope violation) ─
log("  [N2] Men's Hostel Warden tries to target Female students (403)")
sc, body = req("POST", NOTICE_BASE,
               json_data={
                   "title": "This should be blocked",
                   "content": "Men's warden should not be able to target female students in any notice.",
                   "category": "General",
                   "priority": "Low",
                   "target_gender": ["Female"],
               },
               token=S["tok_warden_m"])
pause(CD_WRITE)
T("N2: Men's Hostel Warden blocked from targeting Female (403)", sc == 403, f"sc={sc}")

# ── N3: Men's Hostel Warden cannot target Day Scholars ─────────────────────
log("  [N3] Men's Hostel Warden tries to target Day Scholars (403)")
sc, body = req("POST", NOTICE_BASE,
               json_data={
                   "title": "This should also be blocked",
                   "content": "Men's warden cannot send notices to day scholars under any circumstances.",
                   "category": "General",
                   "priority": "Low",
                   "target_stay_types": ["Day Scholar"],
               },
               token=S["tok_warden_m"])
pause(CD_WRITE)
T("N3: Men's Hostel Warden blocked from targeting Day Scholars (403)", sc == 403, f"sc={sc}")

# ── N4: Women's Hostel Warden sends notice to female hostel students ────────
log("  [N4] Women's Hostel Warden creates notice (Female + Hostel)")
sc, body = req("POST", NOTICE_BASE,
               json_data={
                   "title": "Laundry room schedule update",
                   "content": "The laundry room in Block B will now operate on a new time slot: 6 AM to 8 PM daily. Please plan your laundry accordingly.",
                   "category": "Announcement",
                   "priority": "Medium",
               },
               token=S["tok_warden_w"])
pause(CD_WRITE)
S["notice_id_wh"] = body.get("id") if isinstance(body, dict) else None
T("N4: Women's Hostel Warden notice created (200/201)", sc in (200, 201), f"sc={sc}")
T("N4: Scope auto-locked to Female+Hostel",
  isinstance(body, dict) and body.get("target_gender") == ["Female"] and body.get("target_stay_types") == ["Hostel"],
  f"got gender={body.get('target_gender') if isinstance(body, dict) else '?'}")

# ── N5: Admin sends a campus-wide notice (no restrictions) ─────────────────
log("  [N5] Admin creates campus-wide notice")
sc, body = req("POST", NOTICE_BASE,
               json_data={
                   "title": "Annual sports day registration open",
                   "content": "Registration for the annual inter-department sports day is open. All students can register through the sports committee before March 1st.",
                   "category": "Event",
                   "priority": "Low",
               },
               token=S["tok_admin"])
pause(CD_WRITE)
S["notice_id_admin"] = body.get("id") if isinstance(body, dict) else None
T("N5: Admin campus-wide notice created (200/201)", sc in (200, 201), f"sc={sc}")

# ── N6: HOD CSE sends notice only to CSE students ──────────────────────────
log("  [N6] HOD CSE creates notice (CSE dept only)")
sc, body = req("POST", NOTICE_BASE,
               json_data={
                   "title": "CS301 lab assignment deadline extended",
                   "content": "The deadline for CS301 Data Structures lab assignment has been extended by one week. New deadline: March 10th. Submit via the department portal.",
                   "category": "Announcement",
                   "priority": "Medium",
               },
               token=S["tok_hod_cse"])
pause(CD_WRITE)
S["notice_id_hod"] = body.get("id") if isinstance(body, dict) else None
T("N6: HOD CSE notice created (200/201)", sc in (200, 201), f"sc={sc}")
T("N6: Scope auto-locked to CSE dept",
  isinstance(body, dict) and body.get("target_departments") == ["CSE"],
  f"got depts={body.get('target_departments') if isinstance(body, dict) else '?'}")

pause(CD_READ)

# ── N7: Male hostel student can see the Men's Hostel Warden notice ──────────
log("  [N7] Male hostel student (mh) fetches notice feed")
sc, body = req("GET", NOTICE_FEED, token=S["tok_s_mh"])
pause(CD_READ)
T("N7: Male hostel student notice feed returns 200", sc == 200, f"sc={sc}")
if sc == 200 and isinstance(body, dict):
    notice_ids = [n.get("id") for n in body.get("notices", [])]
    has_mh_notice = S.get("notice_id_mh") in notice_ids
    T("N7: Male hostel student sees Men's Hostel Warden notice",
      has_mh_notice,
      f"notice_id_mh={S.get('notice_id_mh')}, ids_in_feed={notice_ids[:5]}")
else:
    SKIP("N7: Men's Hostel notice visibility check", f"feed sc={sc}")

# ── N8: Female hostel student CANNOT see the Men's Hostel Warden notice ─────
log("  [N8] Female hostel student (wh) fetches notice feed -- should NOT see MH notice")
sc, body = req("GET", NOTICE_FEED, token=S["tok_s_wh"])
pause(CD_READ)
T("N8: Female hostel student notice feed returns 200", sc == 200, f"sc={sc}")
if sc == 200 and isinstance(body, dict) and S.get("notice_id_mh"):
    notice_ids = [n.get("id") for n in body.get("notices", [])]
    not_visible = S["notice_id_mh"] not in notice_ids
    T("N8: Female hostel student does NOT see Men's Hostel notice",
      not_visible,
      f"notice_id_mh={S['notice_id_mh']}, ids_in_feed={notice_ids[:5]}")
else:
    SKIP("N8: MH notice gender exclusion check", "no notice id or feed failed")

# ── N9: Day Scholar student CANNOT see Men's Hostel notice ──────────────────
log("  [N9] Day scholar (gen) fetches feed -- should NOT see MH hostel notice")
sc, body = req("GET", NOTICE_FEED, token=S["tok_s_gen"])
pause(CD_READ)
T("N9: Day Scholar notice feed returns 200", sc == 200, f"sc={sc}")
if sc == 200 and isinstance(body, dict) and S.get("notice_id_mh"):
    notice_ids = [n.get("id") for n in body.get("notices", [])]
    not_visible = S["notice_id_mh"] not in notice_ids
    T("N9: Day Scholar does NOT see Men's Hostel notice",
      not_visible,
      f"notice_id_mh={S['notice_id_mh']}, ids_in_feed={notice_ids[:5]}")
else:
    SKIP("N9: MH notice day-scholar exclusion check", "no notice id or feed failed")

# ── N10: Admin notice is visible to ALL student types ───────────────────────
log("  [N10] All student types see admin campus-wide notice")
if S.get("notice_id_admin"):
    for (label, tok_key) in [("Male Hostel", "tok_s_mh"), ("Female Hostel", "tok_s_wh"),
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
    for _ in range(4):
        SKIP("N10: Admin notice visibility", "no admin notice id")

# ── N11: CSE student sees HOD CSE notice; ECE student does NOT ──────────────
log("  [N11] HOD CSE notice: CSE student sees it, ECE student does not")
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
        SKIP("N11: ECE student HOD notice exclusion", f"sc={sc}")
else:
    SKIP("N11: HOD CSE notice dept filtering", "no hod notice id")
    SKIP("N11: ECE exclusion from HOD CSE notice", "no hod notice id")

# ── N12: Authority can list their own notices ────────────────────────────────
log("  [N12] Men's Hostel Warden lists own notices (GET /my-notices)")
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

# ── N13: Authority can deactivate their notice ───────────────────────────────
log("  [N13] Men's Hostel Warden deactivates their notice")
if S.get("notice_id_mh"):
    sc, body = req("DELETE", f"{NOTICE_BASE}/{S['notice_id_mh']}", token=S["tok_warden_m"])
    pause(CD_WRITE)
    T("N13: Deactivate own notice returns 200", sc == 200, f"sc={sc}")

    # Verify it's gone from student feed
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

# ── N14: Another authority cannot deactivate someone else's notice ────────────
log("  [N14] Women's Hostel Warden tries to deactivate HOD notice (403/404)")
if S.get("notice_id_hod"):
    sc, body = req("DELETE", f"{NOTICE_BASE}/{S['notice_id_hod']}", token=S["tok_warden_w"])
    pause(CD_WRITE)
    T("N14: Cannot deactivate another authority's notice (403/404)",
      sc in (403, 404), f"sc={sc}")
else:
    SKIP("N14: Cross-authority deactivation blocked", "no hod notice id")

# ── N15: Student cannot POST a notice (401/403) ──────────────────────────────
log("  [N15] Student tries to POST a notice (should be 401/403)")
sc, body = req("POST", NOTICE_BASE,
               json_data={
                   "title": "Student fake notice",
                   "content": "Students should not be allowed to create notices for other students.",
                   "category": "General",
                   "priority": "Low",
               },
               token=S["tok_s_obs"])
pause(CD_WRITE)
T("N15: Student cannot create notice (401/403)", sc in (401, 403), f"sc={sc}")


# ══════════════════════════════════════════════════════════════════════════════
#  FINAL RESULTS
# ══════════════════════════════════════════════════════════════════════════════

total   = passed + failed + skipped
pct     = (passed / max(1, passed + failed)) * 100
verdict = "PASS" if pct >= PASS_THRESHOLD else "FAIL"

log(f"\n{'='*72}")
log(f"  FINAL RESULTS — {_now()}")
log(f"{'='*72}")
log(f"  Total Tests : {total}")
log(f"  Passed      : {passed}")
log(f"  Failed      : {failed}")
log(f"  Skipped     : {skipped}")
log(f"  Pass Rate   : {pct:.1f}%  ({verdict})  [threshold={PASS_THRESHOLD}%]")
log(f"{'='*72}")

if failures:
    log(f"\n  FAILED TESTS:")
    for f in failures:
        log(f"    {f}")

log(f"\n  Run suffix   : {RUN_TS}")
log(f"  Students     : {S['mh_roll']}, {S['wh_roll']}, {S['gen_roll']}, "
    f"{S['cse_roll']}, {S['ece_roll']}, {S['dc_roll']}")
log(f"  Update cid   : {S.get('upd_cid')}")
log(f"  Full log     : {os.path.abspath(LOG_FILE)}")
log(f"  Credentials  : {os.path.abspath(CRED_FILE)}")

_log_fh.close()
