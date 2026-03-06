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
