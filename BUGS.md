# BUGS.md
> CampusVoice Backend — Bug & Fix Tracker
> Last updated: 2026-03-06

---

## BUG-001 — Unread Notification Count Endpoints Broken (Admin & Authority)

**Status:** ✅ Fixed

**Affected Endpoints:**
| Side | Endpoint | Method |
|------|----------|--------|
| Admin | `/api/admin/notifications/unread-count` | `GET` |
| Authority | `/api/authorities/notifications` (unread-count call) | `GET` |

### Admin Side — 404 Not Found

- [x] Added `GET /unread-count` route handler in `src/api/routes/admin.py` under `/api/admin/notifications` prefix
- [x] Returns `{"unread_count": N}` for the authenticated admin

### Authority Side — 500 Internal Server Error

- [x] Fixed `str(current_authority.id)` → `str(current_authority)` in all four notification route handlers in `authorities.py` (since `get_current_authority` returns a plain `int`)

---

## BUG-002 — Status History & Timeline Endpoints Reject Authority Tokens (and Complaint Owner)

**Status:** ✅ Fixed

- [x] Changed `get_complaint_with_visibility` dependency → `get_current_user` on both `/{id}/status-history` and `/{id}/timeline` endpoints in `complaints.py`
- [x] Authorities/admins bypass visibility check; students still go through the existing visibility rules
- [x] **Root cause of persistent 403**: Both endpoints used `user.get("sub")` to extract roll_no, but `get_current_user` returns `user_id` (not `sub`). Result: `roll_no = None` → student lookup fails → 403 even for the complaint owner. Fixed to `user.get("user_id")`.

---

## BUG-003 — Frontend Parse Bug: `data?.history` Should Be `data?.status_updates`

**Status:** ✅ Fixed

- [x] `fetchHistory()` in `ComplaintDetails.jsx` now reads `data?.status_updates || data?.history || []`

---

## BUG-004 — Timeline Does Not Distinguish Post Updates from Status Changes

**Status:** ✅ Fixed

- [x] Backend `timeline` endpoint now emits `event: "Authority Update"` for entries where `old_status == new_status` (post-updates) vs `"Status Changed"` for real transitions
- [x] Frontend renders "Authority Update" entries with amber styling and dot colour, distinct from status-change entries

---

## BUG-005 — Student Dispute on Spam Complaint Not Reflected on Admin Side

**Status:** ✅ Fixed

- [x] `ComplaintDetails.jsx` now shows an orange "Student Disputed Spam Classification" banner to authority/admin users when `complaint.has_disputed === true`
- [x] `AuthorityComplaintCard` also shows the dispute banner with `appeal_reason` in the complaint list view
- [x] `AdminComplaintCard.jsx` now shows the dispute banner with `appeal_reason` when `complaint.is_marked_as_spam && complaint.has_disputed` — imported `ShieldAlert`, added orange banner section between the badges and complaint text rows

---

## BUG-006 — Low Confidence Image Verification Result Not Moving Complaint to Spam

**Status:** ✅ Fixed

- [x] Post-verification logic in `complaint_service.py` now checks: if `is_relevant=False` OR `confidence < 0.5`, sets `complaint.is_marked_as_spam=True`, `complaint.status="Spam"`, and populates `spam_reason`
- [x] **Root cause of persisting**: Image verification prompt was explicitly "Be lenient. When in doubt, ACCEPT the image." causing irrelevant images (e.g., a fan for a food complaint) to pass. Prompt rewritten to be strict: image must directly show the subject of the complaint; unrelated campus objects are rejected.

---

## BUG-007 — Authorities Cannot Upload Additional Files / Extra File Size Not Supported

**Status:** ⏭ Deferred — New feature requiring new DB table (`authority_attachments`) and new endpoints

**Description:**
Authority users cannot attach additional supporting files to complaints. The current DB model supports only a single attachment column per complaint. Implementing multi-file support requires a new `authority_attachments` table, new `POST /api/complaints/{id}/authority-attachments` endpoint, and frontend updates. This is a new feature, not a bug fix.

---

## BUG-008 — Physics, Chemistry, Maths, English Shown in Student Registration

**Status:** ✅ Fixed

- [x] `SignupPage.jsx` now filters out ENG/PHY/CHEM/MATH department codes from the student-facing registration dropdown
- [x] Authority-side and backend data are unchanged

---

## BUG-009 — Image Reasoning Section Shows Raw JSON Instead of Human-Readable Text

**Status:** ✅ Fixed

- [x] `ComplaintDetails.jsx` image verification section now JSON-parses `image_verification_message`; displays `parsed.reason` as plain text instead of raw JSON

---

## BUG-010 — Student Roll Number Format Not Validated

**Status:** ✅ Fixed

- [x] `ROLL_NO_PATTERN` in `constants.py` updated to `^\d{11,}$` (numeric only, min 11 digits)
- [x] `SignupPage.jsx` real-time validation updated to match with a clear error message

---

## BUG-011 — Admin Has No Announcement/Notice Feature

**Status:** ⏭ Deferred — New feature, not a bug

---

## BUG-012 — Petition List Returns 422 on Admin/Authority Side

**Status:** ✅ Fixed

- [x] `AdminPetitions.jsx` called `GET /api/petitions/?limit=200` which exceeds backend max of 100 → changed to `limit: 100`
- [x] `AuthorityPetitions.jsx` had the same `limit: 200` → changed to `limit: 100`
- [x] Backend `list_petitions` already commits petitions to DB (`await db.commit()` present)
- [x] Authority petition list view (`AuthorityPetitions.jsx`) and admin petition list with approval controls (`AdminPetitions.jsx`) already exist
- [x] Petition-created notification sent to relevant authority via `_notify_authority_for_approval()` in `petitions.py`

---

## BUG-013 — Complaint Submitted Page Always Shows "AI Analysis Pending" (Static Text)

**Status:** ✅ Fixed

- [x] `SubmitComplaint.jsx` now stores the API response in `submitResult` state and displays actual `category`, `priority`, and `assigned_authority` from the submission response on the success screen

---

## BUG-014 — "Restrooms in IT Department" Complaint Incorrectly Assigned to IT HOD

**Status:** ✅ Fixed

- [x] Added `_apply_facility_general_override()` in `llm_service.py` — detects facility/hygiene keywords (restroom, toilet, washroom, cleanliness, dirty, etc.) and overrides category `Department` → `General`
- [x] LLM categorization prompt updated with an explicit critical rule for physical facility complaints
- [x] Override wired into both the LLM pipeline and `complaint_service.py` post-processing

---

## BUG-015 — Jaccard Similarity in Duplicate Detection Causes False Positives on Shared Location Words

**Status:** ⏭ Deferred — Requires major architectural change (sentence embeddings)

---

## BUG-016 — LLM Incorrectly Categorizes Complaints Against Hostel Staff as Disciplinary Committee

**Status:** ✅ Fixed

- [x] Keyword detection added in `complaint_service.py` — detects "warden", "deputy warden", "senior deputy warden" in complaint text before routing
- [x] Matched role triggers bypass routing: Warden → Deputy Warden, Deputy Warden → Senior Deputy Warden, Senior Deputy Warden → Admin

---

## BUG-017 — Common Subject Complaints (Maths/Physics/English/Chemistry) Assigned to Student's Own Department HOD

**Status:** ✅ Fixed

- [x] Subject-keyword-to-department mapping added in `complaint_service.py`
- [x] When category=Department and text contains subject keywords (maths, physics, chemistry, english), `target_department_id` is overridden to the corresponding department before routing

---

## BUG-018 — LLM Initial Priority Assignment Is Biased / Inconsistent

**Status:** ⏭ Deferred — Major architectural change (weighted scoring model)

---

## BUG-019 — Student Notification Unread-Count Endpoint Intermittently Times Out (500 / TimeoutError)

**Status:** ✅ Fixed

- [x] Changed `GET /students/notifications/unread-count` endpoint from `get_current_student` → `get_current_user` dependency — skips the unnecessary DB student lookup on this hot path (JWT decode is enough to identify the student roll_no)
- [x] Notification polling is already at 30s in `NotificationContext.jsx` with Page Visibility API pause; no change needed there
- [x] `DB_POOL_SIZE=20` + `DB_MAX_OVERFLOW=10` = 30 total connections, adequate for current load

**Root Cause:**
`get_current_student` always called `student_repo.get(roll_no)` (opens a DB connection) just to verify existence/active status. For a polled endpoint (every 30s × N students), this created unnecessary DB connection pressure. The JWT already proves the student is valid; the role check in the new handler enforces authorization without a DB call.

---

## BUG-020 — Student Can Only Attach Camera-Captured Images (Cannot Use Existing Files/Gallery)

**Status:** ✅ Fixed (Already correct)

- [x] Verified: `SubmitComplaint.jsx` uses `accept="image/*"` with no `capture` attribute — gallery and file selection are allowed
- [x] Verified: `NewComplaintModal.jsx` also uses `accept="image/*"` with no `capture` attribute
- [x] No changes required — the bug was not reproducible in the current codebase

---

## BUG-021 — Authority Multi-File Attachments: Only Last File Visible to Students

**Status:** ⏭ Deferred — Tied to BUG-007 (new multi-file DB table required)

**Description:**
The current `Complaint` model stores only a single authority attachment (columns: `authority_attachment_data`, `authority_attachment_filename`, etc.). There is no multi-file mechanism. Fixing this requires a new `authority_attachments` table (same scope as BUG-007). Defer together with BUG-007.

---
## BUG-022 — Petition Link Sharing: Creator Gets "Restricted" Error on Own Petition

**Status:** ✅ Fixed

- [x] Root cause: `_petition_to_dict` (petitions.py) did not include `department_id` in the API response. The frontend `checkAccess` function checked `petition.department_id` for Department-scoped petitions — since it was always `undefined`, `sameDept` was always `false` and all non-creator students were blocked.
- [x] Fix: Added `"department_id": petition.department_id` to `_petition_to_dict` return dict so the frontend scope check has the data it needs.
- [x] Creator bypass (`petition.created_by_roll_no === user.roll_no`) already existed and works correctly once the scope check no longer incorrectly blocks them.

---

## BUG-023 — Hosted Deployment: OPTIONS Preflight Blocked by Auth Middleware Causing 401 on Register/Login

**Status:** ✅ Fixed

**Description:**
After deploying both frontend (`https://campus-voice-frontend-k07w.onrender.com`) and backend on Render, students cannot register and authorities/admin cannot login. Both return `401 Unauthorized`. The backend logs show `OPTIONS /students/register HTTP/1.1 401 Unauthorized` — the auth middleware intercepts CORS preflight requests and rejects them before the actual request is made. This never occurred locally because browsers don't send preflight requests to localhost.

Frontend build was failing on Render due to vite not being installed — fixed by using build command: `npm install --include=dev && node ./node_modules/vite/bin/vite.js build`

CORS_ORIGINS=["https://campus-voice-frontend-k07w.onrender.com","http://localhost:5173"]
ENVIRONMENT=production
DEBUG=False
FRONTEND_URL=https://campus-voice-frontend-k07w.onrender.com

**Frontend Build Command (Render):**
```
npm install --include=dev && node ./node_modules/vite/bin/vite.js build
```

---

## BUG-024 — Stale Token on Browser Reopen: API Calls Fire Before Refresh Completes

**Status:** ✅ Fixed

- [x] `_getValidToken()` in `api.js` proactively checks token expiry (with 10s early buffer) before every API call — if expired it calls `_attemptRefresh()` first, then fires the request with the fresh token
- [x] `_refreshPromise` deduplication ensures all concurrent API calls queue behind a single in-flight refresh — no burst of 401s on page load
- [x] Fallback: if access token is missing, refresh is attempted using the stored refresh token before any request fires
- [x] On refresh failure: all tokens cleared and user redirected to /login

**Root Cause:**
On app initialisation, all components mount simultaneously and fire their API calls in parallel. The token refresh interceptor is async but components don't wait for it — they fire with the stale token and fail. The refresh eventually succeeds and retries work, but the initial burst of `401`s causes brief UI errors or empty states.

---

## BUG-025 — PWA: Install Button Non-Functional, Vibration API Not Working, Real-Time Data Requires Manual Refresh

**Status:** ✅ Fixed

- [x] **Install button**: `InstallPrompt.jsx` refactored to single `useEffect` — reads `window._deferredInstallPrompt` (set in `index.jsx` early-capture) on mount; no more dual-listener race condition. After install, marks `cv_install_prompted` in localStorage. Profile page `handleInstall` correctly calls `window._deferredInstallPrompt.prompt()`.
- [x] **Vibration**: Moved entirely into Service Worker `showNotification` call — fires regardless of app foreground/background state. Pattern: `[200,100,200,100,200]` for urgent (high-priority), `[150,50,150]` for normal. React components no longer handle vibration.
- [x] **Real-time data**: `NotificationContext` dispatches `cv:new-notification` custom event whenever unread count increases (polling). Service Worker sends `BroadcastChannel('cv-notifications')` message `{type:'PUSH_RECEIVED'}` when push arrives — open tabs immediately re-fetch counts without waiting for 30s poll. Periodic background sync registered (`cv-refresh-notifications`, 5min interval) as additional fallback.
- [x] **Push re-subscribe on login**: `AuthContext.loginStudent` calls `window._cvSetupPush()` after auth to ensure push subscription is registered for the new session.

---

## BUG-026 — Authority Can See Student Identity in Complaint Timeline

**Status:** ✅ Fixed

- [x] Timeline endpoint already uses `"a student"` label for non-Admin roles (line 1147 complaints.py)
- [x] Authority complaint list already strips student identity for non-spam complaints (authorities.py partial anonymity)
- [x] Notification message template fixed (see BUG-031) — no roll_no exposed to authorities

---

## BUG-027 — Back Navigation from Complaint Detail Loses Filter State

**Status:** ✅ Fixed

- [x] `status` and `priority` filter values now stored in URL params (`?tab=mine&status=Spam&priority=High`)
- [x] `mineFilters` initialised from URL params on mount so back navigation restores the exact filter state
- [x] `updateMineFilter()` helper syncs filter changes to URL with `replace: true` (no extra history entries)
- [x] `clearMineFilters()` helper resets both state and URL params together
- [x] Tab param preserved when switching — `switchTab('mine')` carries forward existing status/priority params

---

## BUG-028 — LLM Authority Misassignment: Cross-Department Routing, Teacher Scolding Miscategorized as Disciplinary

**Status:** ✅ Fixed

**Description:**
Three related LLM routing failures:
1. **Cross-department complaints** — if a CSE student complains about something in the IT department, the complaint is assigned to CSE HOD instead of IT HOD. Cross-department routing is not implemented.
2. **Teacher scolding complaints** — complaints like "my teacher scolded me in front of the class" are being routed to the Disciplinary Committee. This is wrong — teacher behaviour complaints go to that teacher's department HOD, not DC. DC is only for student misconduct (ragging, harassment between students).
3. **General miscategorization** — LLM continues to misassign despite previous fixes, indicating the prompt rules are insufficient.

**Expected Behaviour:**
- Cross-department complaint → assigned to HOD of the department being complained about (not the student's own dept)
- Teacher behaviour complaint → assigned to HOD of the teacher's department
- DC assignment → only for student-on-student misconduct (ragging, physical assault, harassment)
- Public cross-dept complaints → visible in public feed of both the complainant's dept and the target dept

**Fix:**
Add explicit routing rules in `llm_service.py` and `complaint_service.py`:
```python
# Cross-department detection
# LLM must extract: is_cross_department, target_department_name
# Post-processing maps target_department_name → target_department_id → HOD

# DC assignment rule — ONLY for:
DC_KEYWORDS = ["ragging", "bullying", "physical assault", "harassment by student", "threatening by student"]
# Teacher behaviour keywords → route to HOD, never DC
TEACHER_BEHAVIOUR_KEYWORDS = ["teacher scolded", "professor misbehaved", "faculty rude", "lecturer behaviour"]

# Public feed cross-dept visibility:
# complaint.visible_to_departments = [student.dept_id, target_dept_id]
```
Update LLM prompt with explicit rule:
```
CRITICAL: Disciplinary Committee = ONLY student-on-student misconduct.
Teacher/faculty behaviour complaints = always route to that department's HOD.
Never assign teacher behaviour complaints to Disciplinary Committee.
```

---

## BUG-029 — Image Verification Too Strict: Relevant Images Rejected as Spam

**Status:** ✅ Fixed

**Description:**
The image verification prompt is over-strict. A complaint about contaminated water in a water dispenser with a clear image of a dirty glass of water was rejected as irrelevant (low confidence → marked spam). The image directly shows the subject of the complaint — water with visible contamination — which should pass verification. The current prompt requires the image to show the exact location/object mentioned rather than evidence of the described condition.

**Examples of False Rejections:**
- Complaint: "Water in water dispenser is contaminated" + Image: dirty glass of water → rejected ❌ (should pass ✅)
- Complaint: "Food in canteen is stale" + Image: close-up of spoiled food → may be rejected ❌

**Fix:**
Rewrite the image verification prompt to evaluate **evidence of the condition** not just the exact object:
```python
IMAGE_VERIFICATION_PROMPT = """
Evaluate whether this image provides reasonable evidence for the complaint described.

ACCEPT the image if:
- It shows the condition described (dirty water, broken item, spoiled food, damage)
- It shows the result/effect of the problem even if not the exact object
- It is clearly related to the complaint context (campus environment, food, facilities)

REJECT the image only if:
- It is completely unrelated (e.g., a selfie for an infrastructure complaint)
- It is a stock photo or screenshot of an unrelated web image
- It shows something from a completely different context (outdoor nature for indoor complaint)

Be reasonable. A dirty glass of water IS valid evidence for a water contamination complaint.
A photo of broken furniture IS valid for a furniture complaint even if the room isn't visible.

Confidence threshold: only reject if confidence < 0.35 (not 0.5)
"""
```
Also lower the spam threshold from `confidence < 0.5` to `confidence < 0.35` for image rejection.

---

| student department | complaint                                                                            | expected authority     | assigned authoity      | expected category               | assigned category      | rephrased complaint                                                                                                                      | Remarks                                                                                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------ | ---------------------- | ---------------------- | ------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CSE                | Broken tables in ece classrooms                                                      | ECE HOD                | Administrative Officer | department (cross department)   | general                | The tables in the Early Childhood Education (ECE) classrooms<br>are broken.                                                              | the complaint has to be cross department so that both CSE & ECE students can see and assign to ECE HOD                                                          |
| CSE                | In the ece department...the staffs are very strict and they are scolding by sudharsh | ECE HOD                | Super admin            | departmental (cross department) | Disciplinary Committee | The Early Childhood Education department staff are overly strict and often scold students harshly.                                       | ECE department not Early Childhood Education. it is not disciplinary...complaints about staff is department                                                     |
| CSE                | The boys are ragging the girls in front of fc                                        | DISCIPLINARY COMMITTEE | Super admin            | DISCIPLINARY COMMITTEE          | DISCIPLINARY COMMITTEE | Boys are bullying the girls in front of the class. This behavior<br>is unacceptable and should be addressed.                             | super admin isn't in-charge of DC, need separate authority. FC means food court. llm adds non-existing stuff                                                    |
| CSE                | Please increase the marks of our internal exam.                                      | Department HOD         | administrative officer | department                      | general                | We would like to request an increase in the marks for our internal exam. This would make the assessment more manageable and fair for us. | they're asking to increase marks which is not ethical...so it should be spammed....they are not asking to reevaluate they are asking to increase marks for them |
| CSE                | there's bias among staff in ECE deparment labs during lab exams                      | ECE hod                | super admin            | department                      | department             | Bias is observed in the practical exams of the Electrical and<br>Electronics Engineering (EEE) department.                               | implement cross department                                                                                                                                      |

## BUG-030 — LLM Cannot Handle Shortforms, Typos, and Spelling Mistakes in Complaint Text

**Status:** ✅ Fixed

**Description:**
The LLM fails to correctly categorize or route complaints that contain common shortforms (AC, dept, lib, wifi), typos ("toilett", "complaitn"), or informal spellings ("canteen foood is bad"). Students write casually — the system must handle real-world input robustly.

**Fix:**
Add a text normalization preprocessing step before sending to LLM:
```python
import re

SHORTFORM_MAP = {
    "ac": "air conditioner",
    "dept": "department",
    "lib": "library",
    "wifi": "wi-fi internet",
    "lab": "laboratory",
    "hostel": "hostel",
    "cant": "canteen",
    "dc": "disciplinary committee",
    "hod": "head of department",
    "wc": "washroom",
    "warden": "warden",
}

def normalize_complaint_text(text: str) -> str:
    text = text.lower().strip()
    for short, full in SHORTFORM_MAP.items():
        text = re.sub(rf'\b{short}\b', full, text)
    return text
```
Also update LLM system prompt:
```
Input text may contain shortforms, typos, or informal language.
Interpret charitably — "toilett" means toilet, "canteen foood" means canteen food.
Focus on the intent and subject of the complaint, not spelling accuracy.
```

---

## BUG-031 — Student Identity Exposed to Authorities via Notifications, Complaint Cards, and Timeline

**Status:** ✅ Fixed

- [x] `complaint_service.py` notification template: removed `from student {student_roll_no}` — message is now `"New complaint assigned to you: {category} complaint. Issue: {text[:100]}"`
- [x] `complaints.py` spam dispute notification: removed `from student {roll_no}` — now `"Spam dispute received: ..."`
- [x] Authority complaint list already strips identity fields for non-spam complaints (confirmed in authorities.py)
- [x] Timeline already uses `"a student"` label for Authority role (see BUG-026)

---

## BUG-032 — Notice Detail Not Expanded on Touch: Long Text Hidden in Student View

**Status:** ✅ Fixed

- [x] Added `selectedNotice` state to `NoticeFeed.jsx`
- [x] Added `NoticeDetailModal` component: bottom-sheet on mobile, centered dialog on desktop, shows full `whitespace-pre-wrap` content, authority name, expiry, audience, and attachment button
- [x] All notice cards are now `cursor-pointer` with `onClick={() => setSelectedNotice(notice)}`
- [x] "Read more…" link shown when content exceeds 200 characters
- [x] Attachment button inside card uses `e.stopPropagation()` to open attachment without triggering the detail modal
- [x] Modal attachment button closes the detail modal first, then opens the attachment viewer

---

## BUG-033 — Voting System Unreliable: Single Vote Inflates Priority, No Net Score, No Reach Context

**Status:** 🔴 Open

**Description:**
The current voting system allows a single upvote to push a complaint from Low to Medium priority. This is unreliable and easily manipulated. There is no net vote calculation, no reach context (total eligible voters), and no dampening of vote impact relative to audience size.

**Fix:**
Implement a weighted priority score system:

```python
# Priority score calculation
def calculate_priority_score(complaint, department_student_count: int) -> float:
    # Base score from LLM initial assessment
    base_score = LLM_PRIORITY_BASE_SCORES[complaint.llm_priority]
    # {"Low": 10, "Medium": 40, "High": 70, "Critical": 100}

    # Net votes
    net_votes = complaint.upvote_count - complaint.downvote_count

    # Reach = total students who can see this complaint
    reach = department_student_count  # e.g., 180 for dept complaint

    # Vote weight = dampened by reach (more reach = each vote worth less)
    # Max vote contribution capped at 40 points regardless of votes
    vote_contribution = min(40, (net_votes / reach) * 100 * 2.0)

    # Engagement ratio (what % of eligible viewers voted)
    engagement_ratio = (complaint.upvote_count + complaint.downvote_count) / max(reach, 1)

    # Engagement bonus — high engagement = more credible
    engagement_bonus = min(10, engagement_ratio * 20)

    final_score = base_score + vote_contribution + engagement_bonus

    return round(final_score, 2)

# Priority thresholds
def score_to_priority(score: float) -> str:
    if score >= 80:   return "Critical"
    if score >= 55:   return "High"
    if score >= 30:   return "Medium"
    return "Low"
```
For a department of 180 students:
- 1 upvote = `(1/180) × 100 × 2 = 1.1 points` — negligible, correct behaviour
- 20 upvotes = `(20/180) × 100 × 2 = 22.2 points` — meaningful signal
- 50 upvotes = capped at 40 points — prevents runaway inflation

Add `priority_score FLOAT` column to complaints table and recalculate on every vote.

---

## BUG-034 — Push Notifications Not Delivered When App is Closed or Background

**Status:** ✅ Fixed

- [x] **Backend pipeline wired**: `notification_service._send_push_notification` was a no-op stub — now calls `push_service.send_push_to_user` on every `create_notification`. Push sent to all registered devices for the recipient.
- [x] **pywebpush added**: `pywebpush>=2.0.0` in `requirements.txt`.
- [x] **Vibration in SW**: Pattern set in `showNotification` (`[200,100,200,100,200]` for high urgency, `[150,50,150]` normal) — fires even when app is closed/backgrounded.
- [x] **BroadcastChannel**: After showing notification, SW posts `{type:'PUSH_RECEIVED'}` so open tabs refresh counts immediately without waiting for next poll.
- [x] **Push re-subscribe on login**: `AuthContext.loginStudent` calls `window._cvSetupPush()` to subscribe current device immediately after auth.
- [x] **VAPID setup**: Generate keys and add to `.env`: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL=admin@srec.ac.in`. Frontend reads `VITE_VAPID_PUBLIC_KEY`.
- [x] **Stale cleanup**: `push_service` auto-removes 410 Gone subscriptions.

---

## BUG-035 — Petition Share Link: Non-Creator Viewer Cannot Access Petition After Sharing

**Status:** ✅ Fixed

- [x] Same root cause as BUG-022: missing `department_id` in API response blocked all Department-scoped petition viewers.
- [x] Additional fix in `PetitionDetail.jsx` `checkAccess`: added `signed_by_me` bypass — if the student has already signed the petition they definitively had valid access before, so re-opening the shared link always succeeds regardless of scope re-evaluation.

**Description (original):**
When Student B views a petition (shared by Student A) and then copies and opens the link themselves, they get a "no access" error — even though they already successfully viewed it once. The eligibility check is being re-evaluated on each page load from the link, and something in the URL/session context causes it to fail on the second access. This is distinct from BUG-022 (which was about the creator being blocked). This affects any viewer who shares and re-opens the link.

**Root Cause:**
The petition detail route likely checks eligibility using data from the JWT (dept, year) against the petition scope. If the petition is scope-restricted (e.g., batch-specific), the eligibility check may be failing due to:
1. A race condition where JWT data isn't loaded when the eligibility check fires
2. The URL params being lost or misread on direct link open (deep link handling issue in React Router)
3. Session/auth state not restored before the eligibility check runs on cold open

**Fix:**
In the petition detail page — defer the eligibility check until auth state is confirmed loaded:
```javascript
// PetitionDetail.jsx
const { user, isAuthLoaded } = useAuth()

useEffect(() => {
  if (!isAuthLoaded) return  // wait for auth to restore from storage
  fetchPetitionDetail(petitionId)
}, [isAuthLoaded, petitionId])
```
On backend, also allow access if the student has previously signed or viewed the petition:
```python
def can_view_petition(student, petition) -> bool:
    if petition.created_by == student.roll_no:
        return True
    if has_previously_signed(student.roll_no, petition.id):
        return True
    return is_eligible_by_scope(student, petition)
```

---

