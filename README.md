# CampusVoice — Backend

> AI-powered campus complaint management system built for SREC . Students submit complaints that are automatically categorised, rephrased, and routed to the right authority using a Groq-hosted LLM, with full status tracking, escalation, voting, and a notice/broadcast system.

**Frontend** developed by [TharunSaro](https://github.com/TharunSaro) and [SuriyaPrince](https://github.com/SuriyaPrince).

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Database Schema](#database-schema)
4. [Environment Variables](#environment-variables)
5. [Running the Backend](#running-the-backend)
6. [API Reference](#api-reference)
   - [Auth — Students](#auth--students)
   - [Auth — Authorities](#auth--authorities)
   - [Complaints](#complaints)
   - [Authorities (Actions)](#authorities-actions)
   - [Admin](#admin)
   - [Notices & Broadcasts](#notices--broadcasts)
   - [Notifications](#notifications)
7. [LLM Integration](#llm-integration)
8. [Authentication & Authorization](#authentication--authorization)
9. [Complaint Lifecycle](#complaint-lifecycle)
10. [Auto-Escalation](#auto-escalation)
11. [Vote System](#vote-system)
12. [Visibility & Gender Filtering](#visibility--gender-filtering)
13. [Image Handling](#image-handling)
14. [Spam Detection](#spam-detection)
15. [Rate Limiting](#rate-limiting)
16. [Constants & Configuration](#constants--configuration)
17. [Repository Pattern](#repository-pattern)
18. [Running Tests](#running-tests)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async) + Uvicorn |
| Database | PostgreSQL 15+ via `asyncpg` |
| ORM | SQLAlchemy 2.0 (async) |
| AI / LLM | Groq API (`llama-3.1-8b-instant`) with OpenAI fallback |
| Auth | JWT (HS256) via `python-jose` + `passlib[bcrypt]` |
| Validation | Pydantic v2 + pydantic-settings |
| Image Processing | Pillow |
| Migrations | Alembic (SQLAlchemy) |
| Rate Limiting | In-memory token bucket (Redis-ready) |

---

## Project Structure

```
campusvoice/
├── main.py                        # Entry point — starts Uvicorn
├── src/
│   ├── api/
│   │   ├── __init__.py            # FastAPI app factory, middleware registration
│   │   ├── dependencies.py        # Dependency injection (get_db, get_current_user, etc.)
│   │   └── routes/
│   │       ├── __init__.py        # APIRouter with /api prefix, mounts all sub-routers
│   │       ├── students.py        # /api/students — register, login, profile
│   │       ├── complaints.py      # /api/complaints — submit, vote, feed, images
│   │       ├── authorities.py     # /api/authorities — dashboard, actions, stats
│   │       ├── admin.py           # /api/admin — user management, analytics, escalations
│   │       └── notices.py         # /api/notices — broadcast/notice CRUD
│   ├── services/
│   │   ├── auth_service.py        # Token creation, password hashing, login logic
│   │   ├── complaint_service.py   # Core complaint logic — submit, assign, feed, vote
│   │   ├── llm_service.py         # Groq LLM — categorise, rephrase, spam, image verify
│   │   ├── notification_service.py# Create and query per-user notifications
│   │   ├── image_verification.py  # LLM vision check on uploaded images
│   │   └── spam_detection.py      # Keyword + LLM two-layer spam detection
│   ├── repositories/
│   │   ├── base.py                # Generic CRUD (get, create, update, delete, paginate)
│   │   ├── complaint_repo.py      # Complaint-specific queries (feed, vote, escalate)
│   │   ├── student_repo.py        # Student queries (by roll_no, email)
│   │   └── authority_repo.py      # Authority queries (by level, department)
│   ├── schemas/
│   │   ├── student.py             # StudentRegister, StudentLogin, StudentProfile
│   │   ├── complaint.py           # ComplaintCreate, ComplaintResponse, VoteRequest
│   │   ├── authority.py           # AuthorityResponse, DashboardStats
│   │   └── common.py              # PaginatedResponse, Timestamp mixins
│   ├── database/
│   │   ├── models.py              # SQLAlchemy ORM models (all tables)
│   │   └── connection.py          # Async engine, session factory, get_db generator
│   ├── middleware/
│   │   ├── auth.py                # JWT bearer extraction, PUBLIC_ROUTES whitelist
│   │   ├── error_handler.py       # Global 400/422/500 exception handlers
│   │   ├── logging.py             # Structured request/response logging
│   │   └── rate_limit.py          # Per-IP + per-user token bucket
│   ├── utils/
│   │   ├── validators.py          # Email pattern (@srec.ac.in), roll_no, password
│   │   ├── helpers.py             # time_ago(), uuid validation
│   │   ├── jwt_utils.py           # encode_token / decode_token
│   │   ├── file_upload.py         # Multipart file → bytes + MIME validation
│   │   └── logger.py              # Structured JSON logger setup
│   └── config/
│       ├── settings.py            # Pydantic Settings — loads .env
│       └── constants.py           # All fixed constants (see §16)
```

---

## Database Schema

All tables are created via `SQLAlchemy.create_all()` on startup (no separate migration step needed for development). For production, run Alembic migrations.

### `students`

| Column | Type | Notes |
|---|---|---|
| `roll_no` | VARCHAR PK | Format: `23CS001` — regex validated |
| `name` | VARCHAR NOT NULL | Full name |
| `email` | VARCHAR UNIQUE NOT NULL | Must be `@srec.ac.in` |
| `password_hash` | VARCHAR NOT NULL | bcrypt |
| `department_code` | VARCHAR FK → `departments.code` | |
| `year` | INTEGER NOT NULL | CheckConstraint: 1–10 |
| `stay_type` | VARCHAR | `'Hostel'` or `'Day Scholar'` |
| `gender` | VARCHAR | `'Male'` / `'Female'` — drives hostel visibility |
| `is_active` | BOOLEAN DEFAULT TRUE | Admin can deactivate |
| `profile_picture` | BYTEA | Optional, stored as binary |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |

### `authorities`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | VARCHAR NOT NULL | |
| `email` | VARCHAR UNIQUE NOT NULL | `@srec.ac.in` |
| `password_hash` | VARCHAR NOT NULL | bcrypt |
| `authority_type` | VARCHAR | e.g. `'Warden'`, `'HOD'`, `'Admin Officer'` |
| `authority_level` | INTEGER | Admin=100, AdminOfficer=50, SrDeputyWarden=15, DeputyWarden=10, HOD=8, Warden=5 |
| `department_id` | INTEGER FK → `departments.id` | NULL for non-dept authorities |
| `is_active` | BOOLEAN DEFAULT TRUE | |
| `phone` | VARCHAR | Optional |
| `target_gender` | VARCHAR | `'Male'`/`'Female'`/NULL — Warden gender scope |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |

### `departments`

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `name` | VARCHAR UNIQUE NOT NULL | e.g. `'Computer Science and Engineering'` |
| `code` | VARCHAR UNIQUE NOT NULL | e.g. `'CSE'`, `'ECE'`, `'MECH'` |
| `is_active` | BOOLEAN DEFAULT TRUE | |

13 departments pre-seeded: CSE, ECE, EEE, MECH, CIVIL, IT, AIDS, AIML, MCT, VLSI, ACT, AUTO, MBA.

### `complaint_categories`

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `name` | VARCHAR UNIQUE NOT NULL | |
| `description` | TEXT | |
| `is_active` | BOOLEAN DEFAULT TRUE | |

4 categories: `Hostel` (split into Men's/Women's), `General`, `Department`, `Disciplinary Committee`.

### `complaints`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `student_roll_no` | VARCHAR FK → `students.roll_no` | |
| `category_id` | INTEGER FK → `complaint_categories.id` | LLM-assigned |
| `assigned_authority_id` | UUID FK → `authorities.id` | Current handler |
| `original_assigned_authority_id` | UUID FK → `authorities.id` | NULL until escalated — marks escalation |
| `complaint_department_id` | INTEGER FK → `departments.id` | For dept routing |
| `original_text` | TEXT NOT NULL | Raw student input |
| `rephrased_text` | TEXT | LLM-rephrased formal version |
| `status` | VARCHAR DEFAULT `'Raised'` | See §9 |
| `priority` | VARCHAR DEFAULT `'Low'` | `Low`/`Medium`/`High`/`Critical` |
| `visibility` | VARCHAR DEFAULT `'Public'` | `Public`/`Department`/`Private` |
| `upvotes` | INTEGER DEFAULT 0 | |
| `downvotes` | INTEGER DEFAULT 0 | |
| `is_marked_as_spam` | BOOLEAN DEFAULT FALSE | |
| `image_data` | BYTEA | Binary image stored in DB (not filesystem) |
| `image_verification_status` | VARCHAR | `pending`/`verified`/`rejected`/`abusive` |
| `submitted_at` | TIMESTAMPTZ DEFAULT now() | |
| `resolved_at` | TIMESTAMPTZ | Set when status → `Resolved`/`Closed` |
| `llm_category_reasoning` | TEXT | LLM explanation of category choice |
| `llm_suggested_priority` | VARCHAR | LLM priority suggestion |

Computed property (Python `@property`, not a DB column):
- `has_image` → `image_data is not None`

### `status_updates`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `complaint_id` | UUID FK → `complaints.id` ON DELETE CASCADE | |
| `updated_by_authority_id` | UUID FK → `authorities.id` | |
| `old_status` | VARCHAR | |
| `new_status` | VARCHAR | |
| `reason` | TEXT | Optional — required for Spam/Closed transitions |
| `public_message` | TEXT | Optional public update message |
| `title` | VARCHAR | Optional update title |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |

### `votes`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `complaint_id` | UUID FK → `complaints.id` ON DELETE CASCADE | |
| `student_roll_no` | VARCHAR FK → `students.roll_no` | |
| `vote_type` | VARCHAR | `'upvote'` or `'downvote'` |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |
| UNIQUE | `(complaint_id, student_roll_no)` | One vote per student per complaint |

### `notifications`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `recipient_type` | VARCHAR | `'Student'` or `'Authority'` |
| `recipient_id` | VARCHAR | `roll_no` (student) or `authority_id` (UUID) |
| `complaint_id` | UUID FK → `complaints.id` | Optional |
| `notification_type` | VARCHAR | e.g. `complaint_submitted`, `status_updated`, `complaint_spam` |
| `message` | TEXT NOT NULL | |
| `is_read` | BOOLEAN DEFAULT FALSE | |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |

### `notices`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `authority_id` | UUID FK → `authorities.id` | Who posted it |
| `title` | VARCHAR NOT NULL | |
| `content` | TEXT NOT NULL | |
| `target_audience` | VARCHAR | `'All'`/`'Students'`/`'Hostel'`/`'Department'` |
| `target_department_id` | INTEGER FK → `departments.id` | NULL unless dept-specific |
| `target_gender` | VARCHAR | NULL=all, `'Male'`/`'Female'` for hostel notices |
| `is_active` | BOOLEAN DEFAULT TRUE | |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |

---

## Environment Variables

Create a `.env` file in the project root:

```ini
# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/campusvoice

# ── Security ──────────────────────────────────────────────
JWT_SECRET_KEY=your-secret-key-minimum-32-characters-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DAYS=7

# ── LLM ───────────────────────────────────────────────────
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...          # Optional fallback

# ── App ───────────────────────────────────────────────────
ENVIRONMENT=development        # development | staging | production | test
DEBUG=true
HOST=0.0.0.0
PORT=8000

# ── Feature Flags ─────────────────────────────────────────
ENABLE_IMAGE_VERIFICATION=true
ENABLE_SPAM_DETECTION=true
ENABLE_AUTO_ESCALATION=true
ENABLE_WEBSOCKET=false

# ── Rate Limiting ─────────────────────────────────────────
RATE_LIMIT_REQUESTS=100        # requests per window
RATE_LIMIT_WINDOW=60           # seconds

# ── Image ─────────────────────────────────────────────────
MAX_IMAGE_SIZE_MB=5
IMAGE_STORAGE_MODE=database    # currently only 'database' supported
```

---

## Running the Backend

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

```sql
CREATE DATABASE campusvoice;
CREATE USER campusvoice_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE campusvoice TO campusvoice_user;
```

### 3. Start the server

```bash
# Development (auto-reload)
python main.py

# Or directly with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The database schema is created automatically on first startup via `SQLAlchemy.create_all()`.

Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

### 4. Alembic migrations (production)

```bash
alembic init alembic
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

---

## API Reference

All routes are prefixed with `/api`. JWT token must be sent as `Authorization: Bearer <token>` except for public endpoints.

### Public endpoints (no token required)

```
POST  /api/students/register
POST  /api/students/login
POST  /api/authorities/login
GET   /api/complaints/feed           # public complaint feed
GET   /api/complaints/{id}           # single complaint detail
GET   /api/complaints/{id}/image     # complaint image
GET   /api/notices                   # public notice feed
GET   /api/departments               # list departments
GET   /api/categories                # list complaint categories
GET   /api/health                    # health check
```

---

### Auth — Students

#### `POST /api/students/register`
```json
{
  "roll_no": "23CS001",
  "name": "John Doe",
  "email": "23cs001@srec.ac.in",
  "password": "Password@123",
  "department_code": "CSE",
  "year": 2,
  "stay_type": "Hostel",
  "gender": "Male"
}
```
Validations:
- `roll_no` must match `[0-9]{2}[A-Z]{2,4}[0-9]{3}` (e.g. `23CS001`)
- `email` must end with `@srec.ac.in`
- `password` must have ≥8 chars, uppercase, lowercase, digit, special char
- `year` must be 1–10
- `stay_type`: `Hostel` or `Day Scholar`
- `gender`: `Male` or `Female`

Returns: `{ token, student }` on success.

#### `POST /api/students/login`
```json
{ "email": "23cs001@srec.ac.in", "password": "Password@123" }
```
Returns: `{ token, student }`

#### `GET /api/students/profile`
Returns the logged-in student's profile.

#### `PUT /api/students/profile`
Update name, year, stay_type, gender. Profile picture upload via multipart.

---

### Auth — Authorities

#### `POST /api/authorities/login`
```json
{ "email": "warden@srec.ac.in", "password": "Warden@123" }
```
Returns: `{ token, authority }` — `authority` includes `authority_type`, `authority_level`, `department_id`.

---

### Complaints

#### `POST /api/complaints/submit`
Rate limited: 3 requests per 10 minutes per student.

Multipart form:
```
text          string  required   Complaint description (10–5000 chars)
visibility    string  optional   Public | Department | Private (default: Public)
image         file    optional   JPEG/PNG/WebP, max 5 MB
```

Processing pipeline:
1. Spam/abuse keyword check → reject if flagged
2. LLM spam classification (`llm_service.classify_text`)
3. LLM categorisation (`llm_service.categorize_complaint`) → assigns category
4. LLM rephrasing (`llm_service.rephrase_text`) → stores as `rephrased_text`
5. Authority assignment via `DEFAULT_CATEGORY_ROUTING`
6. Image stored as binary in `complaint.image_data` if provided
7. Notification sent to assigned authority

Returns full `ComplaintResponse`.

#### `GET /api/complaints/feed`
Public complaint feed. Query params:
```
page          int     default 0
page_size     int     default 20 (max 100)
category      string  filter by category name
department    string  filter by department code
status        string  filter by status
priority      string  filter by priority
sort          string  score | time | votes (default: score)
```

Visibility rules applied automatically (see §12).

#### `GET /api/complaints/{complaint_id}`
Full complaint detail including `status_updates` list.

#### `GET /api/complaints/my`
Auth required. Returns the logged-in student's complaints.

#### `POST /api/complaints/{id}/vote`
```json
{ "vote_type": "upvote" }    // or "downvote"
```
- Cannot vote on own complaint (403)
- Replaces existing vote if different type
- Vote score recalculated → priority auto-updated

#### `DELETE /api/complaints/{id}/vote`
Remove own vote.

#### `GET /api/complaints/{id}/my-vote`
Returns `{ has_voted, vote_type }`.

#### `GET /api/complaints/{id}/image`
Returns image binary with correct `Content-Type`. Query `?thumbnail=true` for 300×200 thumbnail.

---

### Authorities (Actions)

All require Authority or Admin JWT.

#### `GET /api/authorities/dashboard`
Returns:
```json
{
  "authority": { ...profile... },
  "stats": {
    "total_assigned": 12,
    "in_progress": 4,
    "resolved": 6,
    "raised": 2,
    "spam": 0,
    "closed": 0,
    "escalated": 1
  }
}
```

#### `GET /api/authorities/complaints`
Complaints assigned to the logged-in authority. Query params: `status`, `priority`, `skip`, `limit`.

#### `PUT /api/authorities/complaints/{id}/status`
```json
{
  "status": "In Progress",
  "reason": "Investigation started"
}
```
Valid transitions (see `VALID_STATUS_TRANSITIONS` in constants):
```
Raised       → In Progress, Spam
In Progress  → Resolved, Spam
Resolved     → Closed
```
`reason` required for `Spam` and `Closed` transitions.

#### `POST /api/authorities/complaints/{id}/update`
Post a public status message visible to the student:
```json
{ "title": "Update title", "content": "Detailed message" }
```

#### `POST /api/authorities/complaints/{id}/escalate`
```json
{ "reason": "Needs higher-level approval" }
```
Sets `original_assigned_authority_id = assigned_authority_id`, then assigns to the next authority in the escalation chain.

#### `POST /api/authorities/complaints/{id}/flag-spam`
```json
{ "reason": "Abuse detected" }
```

#### `GET /api/authorities/stats/detailed`
Returns breakdown for executive dashboard:
```json
{
  "by_category": { "Hostel": 5, "General": 3 },
  "by_priority": { "Critical": 1, "High": 2, "Medium": 3, "Low": 7 },
  "by_status": { "Raised": 2, "In Progress": 4, "Resolved": 6 },
  "resolution_rate": 54.5,
  "avg_resolution_hours": 18.3,
  "weekly_trend": [
    { "label": "Week 1", "count": 3 },
    { "label": "Week 2", "count": 5 },
    { "label": "Week 3", "count": 2 },
    { "label": "Week 4", "count": 7 }
  ]
}
```

---

### Admin

All require Admin-level JWT (`authority_level = 100`).

#### `GET /api/admin/overview`
System-wide stats:
```json
{
  "total_complaints": 150,
  "total_students": 320,
  "total_authorities": 14,
  "by_status": { "Raised": 20, "In Progress": 45, ... },
  "by_priority": { "Critical": 5, "High": 18, ... },
  "by_category": { "Hostel": 60, "General": 40, ... },
  "recent_7_days": 23,
  "resolved": 70,
  "resolution_rate": 46.7,
  "critical_count": 5
}
```

#### `GET /api/admin/complaints`
All complaints system-wide. Query params:
```
status, priority, category, search, date_from (YYYY-MM-DD), date_to (YYYY-MM-DD), skip, limit
```

#### `GET /api/admin/students`
All students. `?search=` filters by name, roll_no, email.

#### `PUT /api/admin/students/{roll_no}/deactivate`
Deactivate a student account.

#### `PUT /api/admin/students/{roll_no}/activate`
Reactivate a student account.

#### `GET /api/admin/authorities`
All authorities list.

#### `POST /api/admin/authorities`
Create a new authority account:
```json
{
  "name": "Dr. Smith",
  "email": "smith@srec.ac.in",
  "password": "Authority@123",
  "authority_type": "HOD",
  "authority_level": 8,
  "department_id": 1,
  "target_gender": null
}
```

#### `PUT /api/admin/authorities/{id}`
Update authority details or reset password.

#### `DELETE /api/admin/authorities/{id}`
Deactivate authority (soft delete).

#### `GET /api/admin/escalations`
Three-section escalation view:
```json
{
  "escalated": [...],     // complaints where original_assigned_authority_id IS NOT NULL
  "critical": [...],      // Critical priority, not escalated, not closed
  "overdue": [...]        // open > 7 days, not escalated
}
```

#### `GET /api/admin/analytics`
Time-series analytics for the last N days:
```json
{
  "period_days": 30,
  "total_complaints": 45,
  "resolved_complaints": 21,
  "resolution_rate_percent": 46.7,
  "avg_resolution_time_hours": 19.2,
  "daily_data": [
    { "date": "2025-01-15", "count": 3 },
    ...
  ]
}
```

---

### Notices & Broadcasts

#### `GET /api/notices`
Public notice feed. Filtered by:
- `target_audience` — All students, or Hostel/Department specific
- `target_gender` — Only shows hostel notices for the student's gender
- `target_department_id` — Only shows dept notices for the student's department

Query params: `skip`, `limit`.

#### `POST /api/notices` (Authority only)
```json
{
  "title": "Water Supply Disruption",
  "content": "Water supply will be interrupted on Monday 10am–2pm in Men's Hostel Block A.",
  "target_audience": "Hostel",
  "target_department_id": null,
  "target_gender": "Male"
}
```

#### `GET /api/notices/{id}`
Single notice detail.

#### `PUT /api/notices/{id}` (Authority only)
Update notice. Only the posting authority can edit.

#### `DELETE /api/notices/{id}` (Authority only)
Soft-delete (sets `is_active = false`).

---

### Notifications

#### `GET /api/notifications`
Returns notifications for the logged-in user (student or authority).
Query params: `skip`, `limit`, `unread_only=true`.

Returns:
```json
{
  "notifications": [...],
  "unread_count": 5,
  "total": 23
}
```

#### `PUT /api/notifications/{id}/read`
Mark a notification as read.

#### `PUT /api/notifications/read-all`
Mark all notifications as read.

---

## LLM Integration

### Groq API (Primary)

Model: `llama-3.1-8b-instant`
Endpoint: `https://api.groq.com/openai/v1`

All LLM calls are wrapped in try/except with fallback to keyword-based classification.

### Categorisation (`llm_service.categorize_complaint`)

Prompt sends:
- Complaint text
- Student context (stay_type, department, gender)
- List of available categories with keywords

LLM returns JSON:
```json
{
  "category": "Men's Hostel",
  "reasoning": "Student mentions room heater malfunction in hostel",
  "suggested_priority": "Medium",
  "confidence": 0.92
}
```

Bias prevention: Academic/department complaints from hostel students are NOT auto-routed to hostel — the LLM is explicitly instructed to categorise by *subject matter*, not student residence.

### Rephrasing (`llm_service.rephrase_text`)

Converts informal student language to formal complaint text. Both original and rephrased text are stored. The rephrased version is shown publicly; the original is preserved for auditing.

### Spam / Abuse Detection (`llm_service.classify_text`)

Returns:
```json
{
  "is_spam": false,
  "is_abusive": false,
  "confidence": 0.95,
  "reason": "Legitimate maintenance complaint"
}
```

Two-layer check:
1. Keyword matching against `SPAM_KEYWORDS` list (fast, synchronous)
2. LLM classification (if keyword check passes)

### Image Verification (`image_verification.verify_image`)

Uses LLM vision model to check:
- `is_relevant` — Is the image related to the complaint?
- `is_abusive` — Does the image contain inappropriate content?
- `confidence_score`

Images pending verification have `image_verification_status = 'pending'`.

---

## Authentication & Authorization

### JWT Token

```python
payload = {
    "sub": user_email,
    "role": "student" | "authority",
    "exp": datetime.utcnow() + timedelta(days=7)
}
```

Algorithm: HS256. Secret must be ≥32 characters.

### Middleware Flow

1. `auth.py` middleware extracts `Authorization: Bearer <token>`
2. Checks path against `PUBLIC_ROUTES` (exact match) and `PUBLIC_PREFIXES` (prefix match)
3. If not public: decodes token, injects `request.state.user` and `request.state.role`
4. Routes use `get_current_user` or `get_current_authority` dependencies from `dependencies.py`

### Public Routes Whitelist

```python
PUBLIC_ROUTES = [
    "/api/students/register", "/api/students/login",
    "/api/authorities/login", "/api/health", "/docs", "/redoc", "/openapi.json"
]
PUBLIC_PREFIXES = [
    "/api/complaints/feed", "/api/notices", "/api/departments", "/api/categories"
]
```

### Role Hierarchy

| Role | `authority_level` | Can access |
|---|---|---|
| Admin | 100 | Everything |
| Admin Officer | 50 | All complaints, analytics |
| Senior Deputy Warden | 15 | Hostel escalations |
| Deputy Warden | 10 | Hostel escalations |
| HOD | 8 | Department complaints |
| Warden | 5 | Hostel complaints (gender-scoped) |

---

## Complaint Lifecycle

```
                 ┌──────────┐
   submit ──────►│  Raised  │
                 └────┬─────┘
                      │ authority action
                 ┌────▼──────┐
                 │In Progress│
                 └────┬──────┘
                      │
              ┌───────▼────────┐
              │    Resolved    │
              └───────┬────────┘
                      │ admin/authority
              ┌───────▼────────┐
              │     Closed     │
              └────────────────┘

   Any open status ──► Spam  (authority flags)
```

Valid transitions (`VALID_STATUS_TRANSITIONS` in `constants.py`):
```python
{
    "Raised":      ["In Progress", "Spam"],
    "In Progress": ["Resolved", "Spam"],
    "Resolved":    ["Closed"],
    "Closed":      [],
    "Spam":        [],
}
```

`Spam` and `Closed` transitions require a `reason`.

---

## Auto-Escalation

Threshold: **7 days** (`ESCALATION_THRESHOLD_DAYS = 7`, `AUTO_ESCALATE_HOURS = 168`).

Escalation chain:
```
Warden (level 5)
    └─► Deputy Warden (level 10)
            └─► Senior Deputy Warden (level 15)
                    └─► Admin (level 100)

HOD (level 8)
    └─► Admin Officer (level 50)
            └─► Admin (level 100)
```

When a complaint is manually or automatically escalated:
- `original_assigned_authority_id` is set to the current handler
- `assigned_authority_id` is updated to the next authority in chain
- Notification sent to both the escalating authority and the new handler

---

## Vote System

```
vote_score = (upvotes × 5) + (downvotes × −3)
```

Priority auto-adjustment (applied after each vote):

| Score | Priority |
|---|---|
| ≥ 200 | Critical |
| ≥ 100 | High |
| ≥ 50  | Medium |
| < 50  | Low |

Rules:
- Students cannot vote on their own complaints (403)
- One vote per student per complaint (DB UNIQUE constraint)
- Voting replaces the previous vote type if different
- `DELETE /vote` removes vote entirely

---

## Visibility & Gender Filtering

Three visibility levels:

| Level | Who can see |
|---|---|
| `Public` | All students (with gender/hostel filter applied) |
| `Department` | Students in the same department + authority |
| `Private` | Only the submitting student + assigned authority |

**Hostel gender filter** (applied to public feed):
- `Men's Hostel` complaints are hidden from Female students and Day Scholars
- `Women's Hostel` complaints are hidden from Male students and Day Scholars
- Day Scholars see neither hostel category in the public feed

---

## Image Handling

Images are stored as **binary in PostgreSQL** (`BYTEA` column on `complaints.image_data`). There is no filesystem storage.

Upload flow:
1. `POST /api/complaints/submit` — multipart file received
2. `file_upload.py` validates MIME type (JPEG/PNG/WebP) and size (≤5 MB)
3. Pillow re-encodes to JPEG for consistency
4. Binary stored in `complaint.image_data`
5. `image_verification_status` set to `'pending'`

Retrieval:
- `GET /api/complaints/{id}/image` — streams binary with `Content-Type: image/jpeg`
- `?thumbnail=true` — Pillow resizes to 300×200 before streaming

`has_image` is a Python `@property` computed as `self.image_data is not None`. It is **not a database column** — never try to assign to it directly.

---

## Spam Detection

### Layer 1: Keyword matching
`SPAM_KEYWORDS` list in `constants.py` — checked synchronously before DB write.

### Layer 2: LLM classification
`llm_service.classify_text()` — async call to Groq. Returns confidence score.

If either layer flags the complaint:
- Complaint is still saved (for audit) with `is_marked_as_spam = True`
- Student is notified
- Assigned authority is notified to review

Authorities can also manually flag spam via `PUT /api/authorities/complaints/{id}/flag-spam`.

---

## Rate Limiting

Implemented in `middleware/rate_limit.py` using an in-memory token bucket (Redis-ready).

Current limits:
- Complaint submission: **3 requests per 10 minutes** per student (stricter)
- All other endpoints: **100 requests per 60 seconds** per IP

Rate limit applies only to `POST /api/complaints/submit` at complaint level. Other POST endpoints use the global IP limit.

---

## Constants & Configuration

All fixed values are in `src/config/constants.py`:

```python
AUTHORITY_LEVELS = {
    "Admin": 100,
    "Admin Officer": 50,
    "Senior Deputy Warden": 15,
    "Deputy Warden": 10,
    "HOD": 8,
    "Warden": 5,
}

DEFAULT_CATEGORY_ROUTING = {
    "Hostel":                   "Warden",
    "Men's Hostel":             "Warden",
    "Women's Hostel":           "Warden",
    "General":                  "Admin Officer",
    "Department":               "HOD",
    "Disciplinary Committee":   "Disciplinary Committee",
}

VALID_STATUS_TRANSITIONS = {
    "Raised":      ["In Progress", "Spam"],
    "In Progress": ["Resolved", "Spam"],
    "Resolved":    ["Closed"],
    "Closed":      [],
    "Spam":        [],
}

REASON_REQUIRED_STATUSES = ["Spam", "Closed"]

ESCALATION_THRESHOLD_DAYS = 7
AUTO_ESCALATE_HOURS = 168

EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@srec\.ac\.in$'
ROLL_NO_PATTERN = r'^[0-9]{2}[A-Z]{2,4}[0-9]{3}$'
```

---

## Repository Pattern

Never write raw SQL in services. Use repository methods.

```python
# complaint_repo.py example
class ComplaintRepository(BaseRepository[Complaint]):
    async def get_feed(self, db, skip, limit, filters, student) -> list[Complaint]:
        ...
    async def get_by_authority(self, db, authority_id, status=None) -> list[Complaint]:
        ...
    async def escalate(self, db, complaint_id, new_authority_id) -> Complaint:
        ...
```

`BaseRepository` provides: `get(id)`, `get_all(skip, limit)`, `create(obj)`, `update(id, data)`, `delete(id)`.

**Critical**: Always use `selectinload()` for any ORM relationship accessed in an async context. Missing `selectinload` causes `greenlet_spawn` errors at runtime:

```python
# Correct
stmt = select(Complaint).options(
    selectinload(Complaint.category),
    selectinload(Complaint.status_updates).selectinload(StatusUpdate.updated_by_authority),
    selectinload(Complaint.student),
)
```

**Session isolation**: Import `get_db` from `src/api/dependencies.py` (not from `connection.py`) in all route files. The `dependencies.py` version caches one session per request. Using the raw `connection.get_db` creates a separate session and causes "already attached to session" errors and silent data loss.

---

## Running Tests

```bash
# Integration test script (requires server running on port 8000)
python test_endpoints.py

# Covers: student registration/login, complaint submission, voting,
#         authority login/actions, status updates, escalation,
#         admin endpoints, notifications, notices
```

Start the server first:
```bash
python main.py
```

---

## License

All rights reserved. SREC internal project.
