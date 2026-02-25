Database setup & migration instructions
=====================================

Purpose
-------
This document explains how to move the CampusVoice project to a new machine and connect it to a new PostgreSQL database. It also explains how to run the included script `scripts/create_and_seed_db.py` to create schemas and seed authority accounts.

Prerequisites
-------------
- Python 3.10+ (match the project's supported version in `runtime.txt` if present).
- PostgreSQL (server installed and running locally or reachable remotely).
- Git (to clone the repository) and access to this project folder.

Recommended local setup (Windows)
---------------------------------
1. Install Python 3.10+ from python.org.
2. Install PostgreSQL (e.g., from https://www.postgresql.org/download/windows/).
3. From an Administrator PowerShell, create a database user and database (example):

```powershell
# Create DB and user (example)
# Adjust names and password to your environment
set PGPASSWORD="your_postgres_superuser_password"
psql -U postgres -c "CREATE USER campus_user WITH PASSWORD 'campus_pass';"
psql -U postgres -c "CREATE DATABASE campusvoice OWNER campus_user;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE campusvoice TO campus_user;"
```

Database connection string
--------------------------
The project reads DB config from `src/config/settings.py` (Pydantic Settings). The simplest way to provide DB credentials is using an environment variable `DATABASE_URL` or a `.env` file in the project root. The expected format for PostgreSQL is:

postgresql+asyncpg://<db_user>:<db_password>@<host>:<port>/<database>

Example:

postgresql+asyncpg://campus_user:campus_pass@localhost:5432/campusvoice

Where to change DB info
-----------------------
- Preferred: create a `.env` file at the repository root with:

```
DATABASE_URL=postgresql+asyncpg://campus_user:campus_pass@localhost:5432/campusvoice
JWT_SECRET_KEY="a-very-long-secret-key-32-chars-min"
GROQ_API_KEY="(optional-if-using-LLM)"
ENVIRONMENT=development
```

- Or export environment variables in your shell before running the app or scripts:

Linux/macOS:
```bash
export DATABASE_URL="postgresql+asyncpg://campus_user:campus_pass@localhost:5432/campusvoice"
export JWT_SECRET_KEY="..."
export ENVIRONMENT=development
```

Windows (PowerShell):
```powershell
$env:DATABASE_URL = "postgresql+asyncpg://campus_user:campus_pass@localhost:5432/campusvoice"
$env:JWT_SECRET_KEY = "..."
$env:ENVIRONMENT = "development"
```

Script: create_and_seed_db.py
-----------------------------
Location: `scripts/create_and_seed_db.py`

What it does:
- Tests DB connectivity (with retries).
- Creates missing tables (idempotent).
- Seeds authority accounts (idempotent).
- Optionally drops tables when `--drop` is used (development only).

How to run
----------
From the project root (where `setup_database.py` and `src/` live):

```bash
# activate your virtualenv first (recommended)
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Install requirements
pip install -r requirements.txt
# Create and seed DB (normal path)
python scripts/create_and_seed_db.py --show

# If you must recreate tables (DANGER: destructive)
python scripts/create_and_seed_db.py --drop --show
```

Notes & troubleshooting
-----------------------
- If the script cannot import project modules, ensure you run it from the project root (the folder that contains `setup_database.py`).
- If `DATABASE_URL` is not set, `src/config/settings.py` may try to read `.env`; create one as described above.
- If you see permission errors when connecting to Postgres, verify the DB user and password and that `pg_hba.conf` allows the connection.
- For remote Postgres, ensure firewall/host allow inbound connections and replace `localhost` with the host/IP.

Security
--------
- Never commit the `.env` file with real credentials to version control.
- Use a strong `JWT_SECRET_KEY` (>= 32 chars) for tokens.

Want me to run the script here?
--------------------------------
I can run `scripts/create_and_seed_db.py` for you in this workspace if you want — just confirm you want me to execute it with the current environment settings (I will not drop tables unless you pass `--drop`).
