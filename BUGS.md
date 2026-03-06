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

## BUG-002 — Status History & Timeline Endpoints Reject Authority Tokens

**Status:** ✅ Fixed

- [x] Changed `get_complaint_with_visibility` dependency → `get_current_user` on both `/{id}/status-history` and `/{id}/timeline` endpoints in `complaints.py`
- [x] Authorities/admins bypass visibility check; students still go through the existing visibility rules

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

---

## BUG-006 — Low Confidence Image Verification Result Not Moving Complaint to Spam

**Status:** ✅ Fixed

- [x] Post-verification logic in `complaint_service.py` now checks: if `is_relevant=False` OR `confidence < 0.5`, sets `complaint.is_marked_as_spam=True`, `complaint.status="Spam"`, and populates `spam_reason`

---

## BUG-007 — Authorities Cannot Upload Additional Files / Extra File Size Not Supported

**Status:** ⏭ Deferred — New feature, not a bug

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

## BUG-012 — Petition Creation Silently Fails; Not Visible to Authority or Admin

**Status:** ✅ Fixed

- [x] `list_petitions()` in `petitions.py` now allows Authority role to see unpublished petitions (previously all non-admin roles were filtered to `is_published=True` only)

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
