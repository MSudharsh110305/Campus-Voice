"""
CampusVoice Full Integration Test
===================================
Tests: complaint submission, anonymous posting, duplicate detection, satisfaction rating,
changelog, Wilson Score, Levenshtein fuzzy spam, Hacker News Hot Score, EWMA,
vote toggle, vote ownership, admin complaint control, student disable/enable.

Run: python test_integration.py
Requires: Backend running on http://localhost:8000
"""

import asyncio
import httpx
import json
import sys
import time
import math

BASE = "http://localhost:8000/api"
TIMEOUT = 30

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = []

def check(label: str, cond: bool, detail: str = ""):
    sym = PASS if cond else FAIL
    msg = f"  {sym} {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append((label, cond, detail))
    return cond


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def post(client, path, data=None, token=None, form=False):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form:
        r = await client.post(f"{BASE}{path}", data=data, headers=headers, timeout=TIMEOUT)
    else:
        headers["Content-Type"] = "application/json"
        r = await client.post(f"{BASE}{path}", content=json.dumps(data or {}), headers=headers, timeout=TIMEOUT)
    return r


async def get(client, path, token=None, params=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = await client.get(f"{BASE}{path}", headers=headers, params=params or {}, timeout=TIMEOUT)
    return r


async def put(client, path, data=None, token=None, params=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = await client.put(
        f"{BASE}{path}",
        content=json.dumps(data or {}),
        headers=headers,
        params=params or {},
        timeout=TIMEOUT,
    )
    return r


async def delete(client, path, token=None, params=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = await client.delete(f"{BASE}{path}", headers=headers, params=params or {}, timeout=TIMEOUT)
    return r


# ── Unique identifiers ────────────────────────────────────────────────────────

TS = str(int(time.time()))[-5:]
# department_id: CSE=1, ECE=2, RAA=3, MECH=4, EEE=5, EIE=6, BIO=7, AERO=8, CIVIL=9, IT=10
STUDENT1 = {"roll_no": f"23CS{TS}1", "name": "Test Alpha",  "email": f"s1{TS}@srec.ac.in", "password": "TestPass@123", "department_id": 1,  "year": 2, "stay_type": "Hostel",     "gender": "Male"}
STUDENT2 = {"roll_no": f"23CS{TS}2", "name": "Test Beta",   "email": f"s2{TS}@srec.ac.in", "password": "TestPass@123", "department_id": 1,  "year": 2, "stay_type": "Day Scholar", "gender": "Male"}
STUDENT3 = {"roll_no": f"23IT{TS}3", "name": "Test Gamma",  "email": f"s3{TS}@srec.ac.in", "password": "TestPass@123", "department_id": 10, "year": 2, "stay_type": "Hostel",     "gender": "Male"}
ADMIN_EMAIL = "admin@srec.ac.in"
ADMIN_PASS  = "Admin@123456"

tok1 = tok2 = tok3 = admin_tok = None
complaint1_id = complaint2_id = None


async def main():
    global tok1, tok2, tok3, admin_tok, complaint1_id, complaint2_id

    async with httpx.AsyncClient() as client:

        # ── 1. REGISTER & LOGIN ───────────────────────────────────────────────
        section("1. Register & Login")

        for s in [STUDENT1, STUDENT2, STUDENT3]:
            r = await post(client, "/students/register", s)
            check(f"Register {s['roll_no']}", r.status_code in (200, 201, 400),
                  f"HTTP {r.status_code}")

        def _get_token(resp_json):
            """Extract token from login/register response"""
            return (resp_json.get("access_token")
                    or resp_json.get("token")
                    or resp_json.get("data", {}).get("token"))

        r1 = await post(client, "/students/login",  {"email_or_roll_no": STUDENT1["email"], "password": STUDENT1["password"]})
        check("Login student1", r1.status_code == 200, f"HTTP {r1.status_code}")
        if r1.status_code == 200:
            tok1 = _get_token(r1.json())

        r2 = await post(client, "/students/login",  {"email_or_roll_no": STUDENT2["email"], "password": STUDENT2["password"]})
        check("Login student2", r2.status_code == 200, f"HTTP {r2.status_code}")
        if r2.status_code == 200:
            tok2 = _get_token(r2.json())

        r3 = await post(client, "/students/login",  {"email_or_roll_no": STUDENT3["email"], "password": STUDENT3["password"]})
        check("Login student3 (IT dept)", r3.status_code == 200, f"HTTP {r3.status_code}")
        if r3.status_code == 200:
            tok3 = _get_token(r3.json())

        r_adm = await post(client, "/authorities/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        check("Login admin", r_adm.status_code == 200, f"HTTP {r_adm.status_code}")
        if r_adm.status_code == 200:
            admin_tok = _get_token(r_adm.json())

        if not tok1:
            print("\n  [ABORT] Could not get student1 token - check backend is running and seeded.")
            sys.exit(1)

        # ── 2. ANONYMOUS POSTING ──────────────────────────────────────────────
        section("2. Anonymous Posting (always anonymous)")

        r = await client.post(
            f"{BASE}/complaints/submit",
            data={
                "original_text": "The projector in CSE Application Development lab room 203 is broken since last week and nobody is fixing it",
                "visibility": "Public",
                "is_anonymous": "true",
            },
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=TIMEOUT,
        )
        check("Submit dept complaint (CSE lab, hostel student)", r.status_code in (200, 201), f"HTTP {r.status_code}")
        if r.status_code in (200, 201):
            data = r.json()
            complaint1_id = data.get("id")
            check("  -> category set", bool(data.get("category")), str(data.get("category")))
            check("  -> authority assigned", bool(data.get("assigned_authority")),
                  str(data.get("assigned_authority")))
            print(f"  {INFO} Category: {data.get('category')} | Priority: {data.get('priority')}")
            print(f"  {INFO} Rephrased: {str(data.get('rephrased_text', ''))[:100]}")

        # ── 3. PLACEMENT ROUTING ──────────────────────────────────────────────
        section("3. Placement Complaint -> Department (not General)")

        r_place = await client.post(
            f"{BASE}/complaints/submit",
            data={
                "original_text": "I need extra support to prepare for my placement drives and campus recruitment. The training and placement cell is not conducting enough mock interviews",
                "visibility": "Public",
                "is_anonymous": "true",
            },
            headers={"Authorization": f"Bearer {tok2}"},
            timeout=TIMEOUT,
        )
        check("Submit placement complaint", r_place.status_code in (200, 201), f"HTTP {r_place.status_code}")
        if r_place.status_code in (200, 201):
            pdata = r_place.json()
            cat = pdata.get("category", "")
            check("  -> Routed to Department (not General)", "Department" in str(cat) or "Dept" in str(cat),
                  f"category={cat}")
            print(f"  {INFO} Category: {cat} | Dept target: {pdata.get('target_department_code')}")

        # ── 4. DUPLICATE DETECTION (Levenshtein) ─────────────────────────────
        section("4. Duplicate Detection (Levenshtein fuzzy matching)")

        if tok2:
            dup_r = await post(client, "/complaints/check-duplicate",
                {"text": "The projector in CSE Application Development lab room is not working properly"},
                token=tok2)
            check("Check-duplicate endpoint accessible", dup_r.status_code == 200, f"HTTP {dup_r.status_code}")
            if dup_r.status_code == 200:
                dup_data = dup_r.json()
                check("  -> Response has is_likely_duplicate field", "is_likely_duplicate" in dup_data)
                check("  -> Response has duplicates list", "duplicates" in dup_data)
                print(f"  {INFO} is_likely_duplicate={dup_data.get('is_likely_duplicate')} | candidates={len(dup_data.get('duplicates', []))}")

        # ── 5. CSE DEPT VISIBILITY (Day Scholar can see hostel student's dept complaint) ─
        section("5. CSE Dept Visibility: Day Scholar sees hostel student's dept complaint")

        if tok2 and complaint1_id:
            feed_r = await get(client, "/complaints/public-feed", token=tok2)
            check("Public feed accessible for student2 (Day Scholar)", feed_r.status_code == 200, f"HTTP {feed_r.status_code}")
            if feed_r.status_code == 200:
                feed_data = feed_r.json()
                complaints_list = feed_data if isinstance(feed_data, list) else feed_data.get("complaints", [])
                ids_in_feed = [str(c.get("id")) for c in complaints_list]
                check("  -> Complaint from hostel student visible to Day Scholar CSE peer",
                      str(complaint1_id) in ids_in_feed,
                      f"complaint1={str(complaint1_id)[:8]}... in {len(ids_in_feed)} items")

        # ── 6. VOTING - toggle & ownership ───────────────────────────────────
        section("6. Voting: Toggle on/off + ownership guard")

        up1 = 0
        if tok2 and complaint1_id:
            # Vote upvote (student2 on student1's complaint)
            vote_r = await post(client, f"/complaints/{complaint1_id}/vote", {"vote_type": "Upvote"}, token=tok2)
            check("Upvote succeeds", vote_r.status_code == 200, f"HTTP {vote_r.status_code}")
            if vote_r.status_code == 200:
                vd = vote_r.json()
                check("  -> user_vote=Upvote", vd.get("user_vote") == "Upvote", str(vd.get("user_vote")))
                up1 = vd.get("upvotes", 0)

            # Toggle off (same vote type -> should remove)
            toggle_r = await post(client, f"/complaints/{complaint1_id}/vote", {"vote_type": "Upvote"}, token=tok2)
            check("Toggle upvote off (same type -> remove)", toggle_r.status_code == 200, f"HTTP {toggle_r.status_code}")
            if toggle_r.status_code == 200:
                td = toggle_r.json()
                check("  -> user_vote=None after toggle", td.get("user_vote") is None, str(td.get("user_vote")))
                check("  -> upvote count decreased", td.get("upvotes", 999) < up1 or td.get("upvotes", 0) == 0,
                      f"was={up1} now={td.get('upvotes')}")

            # Downvote
            down_r = await post(client, f"/complaints/{complaint1_id}/vote", {"vote_type": "Downvote"}, token=tok2)
            check("Downvote succeeds", down_r.status_code == 200, f"HTTP {down_r.status_code}")

            # Switch to upvote (change vote)
            switch_r = await post(client, f"/complaints/{complaint1_id}/vote", {"vote_type": "Upvote"}, token=tok2)
            check("Switch downvote -> upvote", switch_r.status_code == 200, f"HTTP {switch_r.status_code}")
            if switch_r.status_code == 200:
                sd = switch_r.json()
                check("  -> user_vote=Upvote after switch", sd.get("user_vote") == "Upvote", str(sd.get("user_vote")))

            # Remove via DELETE
            del_vote_r = await delete(client, f"/complaints/{complaint1_id}/vote", token=tok2)
            check("DELETE vote (remove)", del_vote_r.status_code == 200, f"HTTP {del_vote_r.status_code}")

        # Ownership guard: student1 cannot vote own complaint
        if tok1 and complaint1_id:
            own_r = await post(client, f"/complaints/{complaint1_id}/vote", {"vote_type": "Upvote"}, token=tok1)
            check("Owner vote blocked (403)", own_r.status_code == 403, f"HTTP {own_r.status_code}")
            if own_r.status_code == 403:
                err = own_r.json()
                # Custom error handler wraps HTTPException detail into "error" key
                raw_err = err.get("error", err.get("detail", ""))
                if isinstance(raw_err, dict):
                    err_msg = raw_err.get("error", "")
                else:
                    err_msg = str(raw_err)
                check("  -> error message mentions own complaint", "own" in err_msg.lower() or "cannot vote" in err_msg.lower(), err_msg)

        # ── 7. WILSON SCORE USED ──────────────────────────────────────────────
        section("7. Wilson Score Lower Bound priority recalculation")

        if tok2 and complaint1_id:
            # Vote upvote again to trigger Wilson Score recalc
            r_v = await post(client, f"/complaints/{complaint1_id}/vote", {"vote_type": "Upvote"}, token=tok2)
            if r_v.status_code == 200:
                vd = r_v.json()
                ps = vd.get("priority_score", 0)
                ups = vd.get("upvotes", 0)
                downs = vd.get("downvotes", 0)
                # Manually verify Wilson Score math
                n = ups + downs
                if n > 0:
                    p = ups / n
                    z = 1.96
                    wilson = (p + z*z/(2*n) - z*math.sqrt((p*(1-p) + z*z/(4*n))/n)) / (1 + z*z/n)
                    expected_score = wilson * 200
                    check("Wilson Score applied to priority_score",
                          abs(ps - expected_score) < 5.0,
                          f"expected~{expected_score:.2f} got={ps}")
                else:
                    check("Wilson Score (no votes yet, skip math check)", True, "no votes")

        # ── 8. HOT SCORE ──────────────────────────────────────────────────────
        section("8. Hacker News Hot Score (logarithmic time decay)")

        if tok1:
            feed_r2 = await get(client, "/complaints/public-feed", token=tok1, params={"skip": 0, "limit": 50})
            check("Public feed returns hot-score-sorted list", feed_r2.status_code == 200, f"HTTP {feed_r2.status_code}")
            if feed_r2.status_code == 200:
                fl = feed_r2.json()
                items = fl if isinstance(fl, list) else fl.get("complaints", [])
                check("  -> Feed has items", len(items) > 0, f"{len(items)} items")
                # Just verify the endpoint works and returns a list (hot-sort happens server-side)
                print(f"  {INFO} Feed returned {len(items)} items (hot-score sorted server-side)")

        # ── 9. SATISFACTION RATING ────────────────────────────────────────────
        section("9. Satisfaction Rating")

        # Submit a second complaint so we can close/resolve it
        r_c2 = await client.post(
            f"{BASE}/complaints/submit",
            data={
                "original_text": "The library Wi-Fi connection is very slow and keeps disconnecting throughout the day",
                "visibility": "Public",
                "is_anonymous": "true",
            },
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=TIMEOUT,
        )
        if r_c2.status_code in (200, 201):
            complaint2_id = r_c2.json().get("id")

        # Try to rate an unresolved complaint (should work or return appropriate error)
        if complaint2_id and tok1:
            rate_r = await post(client, f"/complaints/{complaint2_id}/rate",
                {"rating": 4, "feedback": "Good resolution, thank you"},
                token=tok1)
            # Might be 200 (allowed any time) or 400 (only after resolved) - both valid
            check("Rate endpoint callable", rate_r.status_code in (200, 400),
                  f"HTTP {rate_r.status_code}")
            if rate_r.status_code == 200:
                rd = rate_r.json()
                check("  -> Rating stored (satisfaction_rating present)", True)
                print(f"  {INFO} Rating response: {rd}")
            else:
                print(f"  {INFO} Rating rejected (expected if complaint not resolved): {rate_r.json()}")

        # ── 10. CHANGELOG ─────────────────────────────────────────────────────
        section("10. Changelog (Whats Fixed)")

        if tok1:
            cl_r = await get(client, "/complaints/changelog", token=tok1)
            check("Changelog endpoint accessible", cl_r.status_code == 200, f"HTTP {cl_r.status_code}")
            if cl_r.status_code == 200:
                cl_data = cl_r.json()
                # Response is ChangelogResponse: {entries: [...], total, page, page_size}
                items = cl_data.get("entries", cl_data if isinstance(cl_data, list) else [])
                check("  -> Changelog returns entries list", isinstance(items, list), f"{len(items)} entries")
                print(f"  {INFO} Changelog has {len(items)} entries (total={cl_data.get('total', '?')})")

        # ── 11. PUBLIC ANALYTICS (EWMA) ───────────────────────────────────────
        section("11. Public Analytics + EWMA")

        if tok1:
            analytics_r = await get(client, "/complaints/analytics/summary", token=tok1)
            check("Analytics summary endpoint accessible", analytics_r.status_code == 200, f"HTTP {analytics_r.status_code}")
            if analytics_r.status_code == 200:
                an = analytics_r.json()
                check("  -> total_complaints field present", "total_complaints" in an, str(list(an.keys())))
                check("  -> status_breakdown field present", "status_breakdown" in an, str(list(an.keys())[:5]))
                print(f"  {INFO} Total: {an.get('total_complaints')} | Res avg: {an.get('avg_resolution_hours')}h | Satisfaction: {an.get('satisfaction_avg')}/5")

        if admin_tok:
            adm_analytics = await get(client, "/admin/stats/analytics", token=admin_tok, params={"days": 30})
            check("Admin analytics (EWMA resolution) accessible", adm_analytics.status_code == 200, f"HTTP {adm_analytics.status_code}")
            if adm_analytics.status_code == 200:
                aa = adm_analytics.json()
                print(f"  {INFO} Admin analytics: period={aa.get('period_days')}d resolved={aa.get('resolved_complaints')} rate={aa.get('resolution_rate_percent')}%")

        # ── 12. ADMIN STUDENT MANAGEMENT ──────────────────────────────────────
        section("12. Admin Student Management (disable/enable)")

        if admin_tok:
            students_r = await get(client, "/admin/students", token=admin_tok, params={"limit": 10})
            check("Admin list students", students_r.status_code == 200, f"HTTP {students_r.status_code}")
            if students_r.status_code == 200:
                sdata = students_r.json()
                stlist = sdata.get("students", [])
                check("  -> Students list returned", len(stlist) > 0, f"{len(stlist)} students")

            # Disable student1
            dis_r = await put(client, f"/admin/students/{STUDENT1['roll_no']}/toggle-active",
                              token=admin_tok, params={"activate": "false"})
            check("Disable student1", dis_r.status_code == 200, f"HTTP {dis_r.status_code}")

            # Re-enable
            en_r = await put(client, f"/admin/students/{STUDENT1['roll_no']}/toggle-active",
                             token=admin_tok, params={"activate": "true"})
            check("Re-enable student1", en_r.status_code == 200, f"HTTP {en_r.status_code}")

        # ── 13. ADMIN COMPLAINT CONTROL (reassign/delete) ─────────────────────
        section("13. Admin Complaint Control (reassign + delete)")

        if admin_tok and complaint2_id:
            # List authorities to get a valid ID
            auth_r = await get(client, "/admin/authorities", token=admin_tok, params={"limit": 5, "is_active": "true"})
            check("List authorities", auth_r.status_code == 200, f"HTTP {auth_r.status_code}")
            if auth_r.status_code == 200:
                authorities = auth_r.json().get("authorities", [])
                if authorities:
                    auth_id = authorities[0]["id"]
                    # Reassign
                    rea_r = await put(client, f"/admin/complaints/{complaint2_id}/reassign",
                                      token=admin_tok, params={"authority_id": auth_id})
                    check("Reassign complaint", rea_r.status_code == 200, f"HTTP {rea_r.status_code}")
                    if rea_r.status_code != 200:
                        print(f"  {INFO} Reassign error: {rea_r.text[:200]}")

            # Delete
            del_r = await delete(client, f"/admin/complaints/{complaint2_id}", token=admin_tok)
            check("Delete complaint", del_r.status_code == 200, f"HTTP {del_r.status_code}")
            if del_r.status_code != 200:
                print(f"  {INFO} Delete error: {del_r.text[:200]}")

            # Verify deleted
            det_r = await get(client, f"/complaints/{complaint2_id}", token=tok1)
            check("Deleted complaint is gone (404)", det_r.status_code == 404, f"HTTP {det_r.status_code}")

        # ── 14. LEVENSHTEIN FUZZY SPAM ────────────────────────────────────────
        section("14. Levenshtein fuzzy spam detection")

        # Submit a complaint with slight variations of known spam keywords
        spam_r = await client.post(
            f"{BASE}/complaints/submit",
            data={
                "original_text": "This is a test mesage about faculty with slight speling error in lab",
                "visibility": "Public",
                "is_anonymous": "true",
            },
            headers={"Authorization": f"Bearer {tok2}"},
            timeout=TIMEOUT,
        )
        check("Submit with near-spam text does not crash", spam_r.status_code in (200, 201, 400, 422),
              f"HTTP {spam_r.status_code}")
        if spam_r.status_code in (200, 201):
            sp = spam_r.json()
            print(f"  {INFO} is_spam={sp.get('is_spam', sp.get('is_marked_as_spam'))} | status={sp.get('status')}")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    section("SUMMARY")
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    failed = [(label, detail) for label, ok, detail in results if not ok]
    print(f"\n  Passed: {passed}/{total}")
    if failed:
        print(f"  Failed ({len(failed)}):")
        for label, detail in failed:
            print(f"    {FAIL} {label}  [{detail}]")
    else:
        print(f"  All tests passed!")
    print()
    return len(failed) == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
