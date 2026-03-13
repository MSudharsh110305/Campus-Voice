#!/usr/bin/env python3
"""
test_focused.py — Targeted regression test for:
  1. Previously failing LLM classification TCs
     (WH-4 rats, DEPT-CSE-1, DEPT-CSE-3, DC-3, Edge-3, Update-test, T380)
  2. Notice / broadcast feature
     (creation, scope enforcement, visibility per student type, deactivation)

Target: https://campusvoice-api-h528.onrender.com
"""

import requests, time, sys
from datetime import datetime
from typing import Tuple

BASE_URL = "http://localhost:8000"
TS       = datetime.now().strftime("%H%M%S")          # 6-digit suffix
LOG_FILE = f"focused_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
CD_LLM   = 15    # seconds after each LLM complaint (local server is faster)
CD_WRITE = 3
CD_READ  = 1

# ── logging ──────────────────────────────────────────────────────────────────
_fh = open(LOG_FILE, "w", encoding="utf-8", buffering=1)

def log(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode())
    _fh.write(msg + "\n")

# ── counters ─────────────────────────────────────────────────────────────────
passed = failed = 0
failures_list = []

def check(label: str, cond: bool, detail: str = ""):
    global passed, failed
    if cond:
        passed += 1
        log(f"  [+] {label}")
    else:
        failed += 1
        failures_list.append(label)
        log(f"  [!] FAIL: {label}")
        if detail:
            log(f"         {detail}")

def pause(secs: int, reason: str = ""):
    ts = datetime.now().strftime("%H:%M:%S")
    label = f" — {reason}" if reason else ""
    log(f"\n  [wait {ts}] Pausing {secs}s{label}")
    time.sleep(secs)

# ── http helper ───────────────────────────────────────────────────────────────
def req(method: str, path: str, token: str = None, **kwargs) -> Tuple[int, dict]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = BASE_URL + path
    try:
        r = getattr(requests, method.lower())(url, headers=headers, timeout=60, **kwargs)
        try:
            body = r.json()
        except Exception:
            body = {"_raw": r.text[:300]}
        return r.status_code, body
    except Exception as e:
        return 0, {"error": str(e)}

def submit_complaint(token: str, text: str, visibility: str = "Public") -> Tuple[int, dict]:
    sc, body = req("POST", "/api/complaints/submit",
                   token=token,
                   data={"original_text": text, "visibility": visibility},
                   files={"_": ("", b"", "text/plain")})
    pause(CD_LLM, "waiting for LLM")
    return sc, (body if isinstance(body, dict) else {})

# ── shared state ──────────────────────────────────────────────────────────────
S = {}   # tokens, IDs


# ═════════════════════════════════════════════════════════════════════════════
#  AUTHORITY LOGINS
# ═════════════════════════════════════════════════════════════════════════════
def authority_logins():
    log("\n" + "=" * 72)
    log("  AUTHORITY LOGINS")
    log("=" * 72)

    creds = [
        ("admin",    "admin@srec.ac.in",          "Admin@123456"),
        ("officer",  "officer@srec.ac.in",         "Officer@1234"),
        ("warden_m", "warden1.mens@srec.ac.in",    "MensW1@1234"),
        ("warden_w", "warden1.womens@srec.ac.in",  "WomensW1@123"),
        ("hod_cse",  "hod.cse@srec.ac.in",         "HodCSE@123"),
        ("hod_ece",  "hod.ece@srec.ac.in",         "HodECE@123"),
        ("dc",       "dc@srec.ac.in",              "Discip@12345"),
    ]
    for key, email, pwd in creds:
        sc, body = req("POST", "/api/authorities/login",
                       json={"email": email, "password": pwd})
        S[f"tok_{key}"] = body.get("token")
        check(f"Login {email}",
              sc == 200 and bool(S[f"tok_{key}"]),
              f"sc={sc}")
        pause(CD_READ)


# ═════════════════════════════════════════════════════════════════════════════
#  STUDENT REGISTRATION & LOGIN
# ═════════════════════════════════════════════════════════════════════════════
def register_students():
    log("\n" + "=" * 72)
    log("  STUDENT REGISTRATION  (3 students, suffix=" + TS + ")")
    log("=" * 72)

    # Student types chosen to cover all test scenarios:
    #   mh_cse  — Male, CSE, Hostel    → DEPT-CSE-1/3, Update-test, N7/N11
    #   wh_ece  — Female, ECE, Hostel  → WH-4, Edge-3, N8
    #   ds_gen  — Male, Day Scholar    → DC-3, N9
    students = [
        ("mh_cse", f"FMC{TS}", "Male CSE Hostel",   f"fmc{TS}@srec.ac.in",  "Male",   "Hostel",      1),
        ("wh_ece", f"FWE{TS}", "Female ECE Hostel", f"fwe{TS}@srec.ac.in",  "Female", "Hostel",      2),
        ("ds_gen", f"FDG{TS}", "Day Scholar Male",  f"fdg{TS}@srec.ac.in",  "Male",   "Day Scholar", 4),
    ]

    pwd = "Focus@1234"

    for key, roll, name, email, gender, stay, dept in students:
        sc, body = req("POST", "/api/students/register", json={
            "roll_no": roll, "name": name, "email": email,
            "password": pwd, "gender": gender,
            "stay_type": stay, "department_id": dept, "year": 2
        })
        check(f"Register {key} ({email})", sc in (200, 201), f"sc={sc}")
        pause(CD_WRITE)

    for key, roll, name, email, gender, stay, dept in students:
        sc, body = req("POST", "/api/students/login",
                       json={"email_or_roll_no": email, "password": pwd})
        S[f"tok_{key}"] = body.get("token")
        check(f"Login {key}", sc == 200 and bool(S[f"tok_{key}"]), f"sc={sc}")
        pause(CD_READ)


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — LLM CLASSIFICATION FIXES
# ═════════════════════════════════════════════════════════════════════════════
def test_llm_fixes():
    log("\n" + "=" * 72)
    log("  SECTION 1: LLM CLASSIFICATION FIXES  (previously failing TCs)")
    log("=" * 72)
    log("  Each complaint waits 40s for Groq LLM on Render.")

    # ── WH-4: Rats sighted in hostel storeroom ───────────────────────────────
    log("\n  [WH-4] Rats complaint — Female ECE Hostel → expected Women's Hostel")
    sc, body = submit_complaint(
        S["tok_wh_ece"],
        "Rats have been sighted repeatedly in the women's hostel storeroom near the kitchen. "
        "This is a major hygiene risk and students are afraid to store food in their rooms."
    )
    check("WH-4: submission accepted (200/201)", sc in (200, 201), f"got {sc}")
    check("WH-4: categorised as Women's Hostel",
          body.get("category") == "Women's Hostel",
          f"got category={body.get('category')!r}")
    check("WH-4: assigned to an authority",
          bool(body.get("assigned_authority")),
          f"assigned_authority={body.get('assigned_authority')!r}")

    # ── DEPT-CSE-1: Computers in CSE Lab 3 ───────────────────────────────────
    log("\n  [DEPT-CSE-1] CSE Lab hardware failure — Male CSE Hostel → expected Department")
    sc, body = submit_complaint(
        S["tok_mh_cse"],
        "Fifteen out of thirty computers in CSE Lab 3 (2nd floor, main block) are non-functional "
        "due to hardware failures. Programming practicals for CS301 are severely disrupted this week."
    )
    check("DEPT-CSE-1: submission accepted (200/201)", sc in (200, 201), f"got {sc}")
    check("DEPT-CSE-1: categorised as Department",
          body.get("category") == "Department",
          f"got category={body.get('category')!r}")

    # ── DEPT-CSE-3: Laser printer in CSE department office ───────────────────
    log("\n  [DEPT-CSE-3] CSE dept office printer — Male CSE Hostel → expected Department")
    sc, body = submit_complaint(
        S["tok_mh_cse"],
        "The laser printer in the CSE department office has been out of order for two weeks. "
        "We are unable to print lab observation books and project reports as mandated by faculty."
    )
    check("DEPT-CSE-3: submission accepted (200/201)", sc in (200, 201), f"got {sc}")
    check("DEPT-CSE-3: categorised as Department",
          body.get("category") == "Department",
          f"got category={body.get('category')!r}")

    # ── DC-3: Violent physical altercation near library ───────────────────────
    log("\n  [DC-3] Physical altercation near library — Day Scholar → expected Disciplinary Committee")
    sc, body = submit_complaint(
        S["tok_ds_gen"],
        "I witnessed a violent physical altercation between two students near the library building "
        "yesterday at 4 PM. This kind of violent behaviour is unacceptable and must be investigated."
    )
    check("DC-3: submission accepted (200/201)", sc in (200, 201), f"got {sc}")
    check("DC-3: categorised as Disciplinary Committee",
          body.get("category") == "Disciplinary Committee",
          f"got category={body.get('category')!r}")

    # ── Edge-3: ECE female cross-dept complaint about CSE lab ─────────────────
    log("\n  [Edge-3] ECE female hostel → CSE lab access issue → expected Department")
    sc, body = submit_complaint(
        S["tok_wh_ece"],
        "As an ECE student working on my final-year project, I need access to the CSE department's "
        "server room and computing cluster. Despite sending requests to the CSE lab in-charge three "
        "times, no access has been granted and my project submission date is approaching."
    )
    check("Edge-3: submission accepted (200/201)", sc in (200, 201), f"got {sc}")
    check("Edge-3: categorised as Department (not Women's Hostel)",
          body.get("category") == "Department",
          f"got category={body.get('category')!r}")

    # ── Update-test: Projector in CSE Seminar Hall ────────────────────────────
    log("\n  [Update-test] CSE Seminar Hall projector — Male CSE Hostel → expected Department")
    sc, body = submit_complaint(
        S["tok_mh_cse"],
        "The projector in CSE Seminar Hall (3rd floor, main academic block) has not been working "
        "for over a week. Multiple faculty lectures and student presentations have been disrupted. "
        "The AV technician has been informed twice but no repair has been carried out."
    )
    check("Update-test: submission accepted (200/201)", sc in (200, 201), f"got {sc}")
    check("Update-test: categorised as Department",
          body.get("category") == "Department",
          f"got category={body.get('category')!r}")
    S["upd_cid"] = body.get("id")

    # ── T380: Men's Hostel Warden cannot update a Dept-assigned complaint ─────
    log("\n  [T380] Men's Hostel Warden tries to update HOD-assigned complaint → 403/404")
    if S.get("upd_cid"):
        pause(CD_WRITE, "brief pause before warden access attempt")
        sc, body = req("PUT", f"/api/authorities/complaints/{S['upd_cid']}/status",
                       token=S["tok_warden_m"],
                       json={"status": "In Progress"})
        check("T380: Warden cannot update HOD complaint (expects 403/404)",
              sc in (403, 404),
              f"got sc={sc}")
    else:
        log("  [T380] Skipped: Update-test complaint has no ID (submission failed or wrong category)")


# ═════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — NOTICE / BROADCAST FEATURE
# ═════════════════════════════════════════════════════════════════════════════
def test_notices():
    log("\n" + "=" * 72)
    log("  SECTION 2: NOTICE / BROADCAST FEATURE")
    log("=" * 72)

    # ── N1: Men's Hostel Warden creates notice ────────────────────────────────
    log("\n  [N1] Men's Hostel Warden creates notice")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_warden_m"],
                   json={
                       "title": f"Water Supply Disruption {TS}",
                       "content": "Water supply will be interrupted Sunday 6-8 AM for tank cleaning.",
                       "category": "Announcement",
                       "priority": "Medium",
                   })
    pause(CD_WRITE)
    check("N1: Men's Hostel Warden notice created (200/201)", sc in (200, 201),
          f"sc={sc} body={str(body)[:120]}")
    check("N1: Notice ID returned", bool(body.get("id")), f"body={str(body)[:100]}")
    S["n1_id"] = body.get("id")
    tg  = body.get("target_gender") or []
    ts_ = body.get("target_stay_types") or []
    check("N1: scope locked to Male",   "Male"   in tg,  f"target_gender={tg}")
    check("N1: scope locked to Hostel", "Hostel" in ts_, f"target_stay_types={ts_}")

    # ── N2: Men's Hostel Warden tries to target Female → 403 ─────────────────
    log("\n  [N2] Men's Hostel Warden targets Female → 403")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_warden_m"],
                   json={
                       "title": "Bad target test",
                       "content": "This scope should be blocked — warden is Men's Hostel only.",
                       "target_gender": ["Female"],
                   })
    pause(CD_WRITE)
    check("N2: Men's Warden blocked from targeting Female (403)", sc == 403,
          f"got sc={sc}")

    # ── N3: Men's Hostel Warden tries to target Day Scholars → 403 ───────────
    log("\n  [N3] Men's Hostel Warden targets Day Scholars → 403")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_warden_m"],
                   json={
                       "title": "Bad stay-type test",
                       "content": "Day scholars are outside hostel warden scope.",
                       "target_stay_types": ["Day Scholar"],
                   })
    pause(CD_WRITE)
    check("N3: Men's Warden blocked from targeting Day Scholars (403)", sc == 403,
          f"got sc={sc}")

    # ── N4: Women's Hostel Warden creates notice ──────────────────────────────
    log("\n  [N4] Women's Hostel Warden creates notice → scope Female+Hostel")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_warden_w"],
                   json={
                       "title": f"Room Inspection Saturday {TS}",
                       "content": "Room inspection scheduled for Saturday 9 AM. Keep rooms tidy.",
                       "category": "Announcement",
                   })
    pause(CD_WRITE)
    check("N4: Women's Hostel Warden notice created (200/201)", sc in (200, 201),
          f"sc={sc}")
    S["n4_id"] = body.get("id")
    tg = body.get("target_gender") or []
    check("N4: scope auto-locked to Female", "Female" in tg, f"target_gender={tg}")

    # ── N5: Admin creates campus-wide notice ──────────────────────────────────
    log("\n  [N5] Admin creates campus-wide notice (no targeting)")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_admin"],
                   json={
                       "title": f"Annual Day Celebration {TS}",
                       "content": "Annual Day will be held on March 15 at the main auditorium. All students invited.",
                       "category": "Event",
                       "priority": "High",
                   })
    pause(CD_WRITE)
    check("N5: Admin campus-wide notice created (200/201)", sc in (200, 201),
          f"sc={sc}")
    S["n5_id"] = body.get("id")

    # ── N6: HOD CSE creates notice → scope CSE dept ───────────────────────────
    log("\n  [N6] HOD CSE creates notice → scope auto-locked to CSE")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_hod_cse"],
                   json={
                       "title": f"CSE Lab 3 Maintenance {TS}",
                       "content": "CSE Lab 3 will be closed Friday afternoon for hardware maintenance.",
                       "category": "Maintenance",
                   })
    pause(CD_WRITE)
    check("N6: HOD CSE notice created (200/201)", sc in (200, 201), f"sc={sc}")
    S["n6_id"] = body.get("id")
    td = body.get("target_departments") or []
    check("N6: scope auto-locked to CSE", "CSE" in td, f"target_departments={td}")

    # ── Fetch feeds for all 3 student types ───────────────────────────────────
    log("\n  [Visibility] Fetching notice feeds for all student types...")
    pause(CD_READ, "allow notice propagation")

    sc_m, body_m = req("GET", "/api/students/notices", token=S["tok_mh_cse"])
    sc_f, body_f = req("GET", "/api/students/notices", token=S["tok_wh_ece"])
    sc_d, body_d = req("GET", "/api/students/notices", token=S["tok_ds_gen"])

    ids_m = [n.get("id") for n in (body_m.get("notices") or [])] if isinstance(body_m, dict) else []
    ids_f = [n.get("id") for n in (body_f.get("notices") or [])] if isinstance(body_f, dict) else []
    ids_d = [n.get("id") for n in (body_d.get("notices") or [])] if isinstance(body_d, dict) else []

    check("N7: Male hostel student feed returns 200", sc_m == 200, f"sc={sc_m}")
    check("N8: Female hostel student feed returns 200", sc_f == 200, f"sc={sc_f}")
    check("N9: Day Scholar feed returns 200", sc_d == 200, f"sc={sc_d}")

    # Men's Hostel notice (N1) visibility
    check("N7: Male hostel student SEES Men's Hostel notice (N1)",
          S.get("n1_id") in ids_m,
          f"n1_id={S.get('n1_id')} male_feed={ids_m}")
    check("N8: Female hostel student does NOT see Men's Hostel notice (N1)",
          S.get("n1_id") not in ids_f,
          f"n1_id={S.get('n1_id')} female_feed={ids_f}")
    check("N9: Day Scholar does NOT see Men's Hostel notice (N1)",
          S.get("n1_id") not in ids_d,
          f"n1_id={S.get('n1_id')} ds_feed={ids_d}")

    # Admin campus-wide notice (N5) — all three should see it
    check("N10a: Male hostel student sees admin campus-wide notice (N5)",
          S.get("n5_id") in ids_m,
          f"n5_id={S.get('n5_id')} male_feed={ids_m}")
    check("N10b: Female hostel student sees admin campus-wide notice (N5)",
          S.get("n5_id") in ids_f,
          f"n5_id={S.get('n5_id')} female_feed={ids_f}")
    check("N10c: Day Scholar sees admin campus-wide notice (N5)",
          S.get("n5_id") in ids_d,
          f"n5_id={S.get('n5_id')} ds_feed={ids_d}")

    # HOD CSE notice (N6) — CSE student sees, ECE student does not
    check("N11a: CSE student SEES HOD CSE notice (N6)",
          S.get("n6_id") in ids_m,
          f"n6_id={S.get('n6_id')} cse_feed={ids_m}")
    check("N11b: ECE student does NOT see HOD CSE notice (N6)",
          S.get("n6_id") not in ids_f,
          f"n6_id={S.get('n6_id')} ece_feed={ids_f}")

    # ── N12: Authority lists own notices ──────────────────────────────────────
    log("\n  [N12] Men's Hostel Warden lists own notices")
    sc, body = req("GET", "/api/authorities/my-notices", token=S["tok_warden_m"])
    check("N12: GET /my-notices returns 200", sc == 200, f"sc={sc}")
    my_ids = [n.get("id") for n in (body.get("notices") or [])] if isinstance(body, dict) else []
    check("N12: Own notice (N1) appears in my-notices",
          S.get("n1_id") in my_ids,
          f"n1_id={S.get('n1_id')} my_ids={my_ids}")

    # ── N13: Warden deactivates own notice ────────────────────────────────────
    log("\n  [N13] Men's Hostel Warden deactivates own notice (N1)")
    if S.get("n1_id"):
        sc, body = req("DELETE", f"/api/authorities/notices/{S['n1_id']}",
                       token=S["tok_warden_m"])
        pause(CD_WRITE)
        check("N13: Deactivate own notice → 200", sc == 200,
              f"sc={sc} body={str(body)[:80]}")
        # Verify gone from student feed
        sc2, body2 = req("GET", "/api/students/notices", token=S["tok_mh_cse"])
        ids_after = [n.get("id") for n in (body2.get("notices") or [])] if isinstance(body2, dict) else []
        check("N13: Deactivated notice no longer in male student feed",
              S.get("n1_id") not in ids_after,
              f"n1_id={S.get('n1_id')} still present: {S.get('n1_id') in ids_after}")
    else:
        log("  [N13] Skipped — N1 ID not available")

    # ── N14: Women's Warden cannot deactivate HOD CSE notice ─────────────────
    log("\n  [N14] Women's Hostel Warden tries to deactivate HOD CSE notice → 403/404")
    if S.get("n6_id"):
        sc, body = req("DELETE", f"/api/authorities/notices/{S['n6_id']}",
                       token=S["tok_warden_w"])
        pause(CD_WRITE)
        check("N14: Cannot deactivate another authority's notice (403/404)",
              sc in (403, 404), f"got sc={sc}")
    else:
        log("  [N14] Skipped — N6 ID not available")

    # ── N15: Student cannot create notice → 401/403 ───────────────────────────
    log("\n  [N15] Student tries to POST a notice → 401/403")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_mh_cse"],
                   json={"title": "Student notice attempt",
                         "content": "Students should not be allowed to create notices."})
    pause(CD_WRITE)
    check("N15: Student cannot create notice (401/403)", sc in (401, 403),
          f"got sc={sc}")

    # ── N16: Admin deactivates Women's Warden notice ──────────────────────────
    log("\n  [N16] Admin deactivates Women's Hostel Warden notice (N4)")
    if S.get("n4_id"):
        sc, body = req("DELETE", f"/api/authorities/notices/{S['n4_id']}",
                       token=S["tok_admin"])
        pause(CD_WRITE)
        check("N16: Admin deactivates another authority's notice → 200",
              sc == 200, f"sc={sc}")
    else:
        log("  [N16] Skipped — N4 ID not available")

    # ── N17: Women's Hostel Warden tries to target Male → 403 ────────────────
    log("\n  [N17] Women's Hostel Warden targets Male → 403")
    sc, body = req("POST", "/api/authorities/notices",
                   token=S["tok_warden_w"],
                   json={
                       "title": "Bad male target test",
                       "content": "Women's warden cannot target male students.",
                       "target_gender": ["Male"],
                   })
    pause(CD_WRITE)
    check("N17: Women's Warden blocked from targeting Male (403)", sc == 403,
          f"got sc={sc}")

    # ── N18: Notice feed without auth → 401 ──────────────────────────────────
    log("\n  [N18] Notice feed without auth → 401")
    sc, _ = req("GET", "/api/students/notices")
    check("N18: Notice feed without auth → 401", sc == 401, f"got sc={sc}")


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    start = datetime.now().strftime("%H:%M:%S")
    log("=" * 72)
    log("  CampusVoice — Focused Regression + Notice Test")
    log(f"  Target : {BASE_URL}")
    log(f"  Log    : {LOG_FILE}")
    log(f"  Suffix : {TS}")
    log(f"  Started: {start}")
    log("=" * 72)

    # Server wake-up
    log("\n[WAKE-UP] Pinging server...")
    import time as _t
    t0 = _t.time()
    for _ in range(15):
        sc, body = req("GET", "/health")
        if sc == 200:
            log(f"[WAKE-UP] HTTP 200 in {_t.time()-t0:.1f}s")
            break
        _t.sleep(10)
    else:
        log("[WAKE-UP] Server unreachable — aborting")
        sys.exit(1)

    pause(3, "server stabilise")

    authority_logins()
    register_students()
    test_llm_fixes()
    test_notices()

    end = datetime.now().strftime("%H:%M:%S")
    total = passed + failed
    rate  = 100.0 * passed / total if total else 0.0
    status = "[PASS]" if rate >= 80 else "[FAIL]"

    log("\n" + "=" * 72)
    log(f"  FINAL RESULTS  —  {end}")
    log("=" * 72)
    log(f"  Total  : {total}")
    log(f"  Passed : {passed}")
    log(f"  Failed : {failed}")
    log(f"  Rate   : {rate:.1f}%  {status}")
    log("=" * 72)

    if failures_list:
        log("\n  FAILED TESTS:")
        for f_ in failures_list:
            log(f"    • {f_}")

    _fh.close()


if __name__ == "__main__":
    main()
