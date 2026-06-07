# AGENTS.md - AI Development Guide for SoIDied

## Project Overview

**SoIDied** is a post-mortem digital notification system ("Digital Dead Man's Switch"). It monitors user check-ins and automatically sends pre-configured information to contacts when the user dies or misses scheduled check-ins. The project is entirely **configuration-driven** via YAML.

### Core Architecture
- **Entry Point**: `main.py` loads config via `Settings` class and initializes the system
- **Configuration Management**: `src/tools/settings.py` provides `Settings` class for YAML config access
- **REST API**: `src/api/` module with endpoint implementations; `api.py` provides Flask-RESTful endpoints with SQLAlchemy ORM (SQLite backend)
- **Data Layer**: `src/models/` for database models; `src/db/` for schema utilities; `src/bootstrap.py` initializes schema on app start
- **Tooling**: `src/tools/` module for feature implementations (scheduler, email, defense, actions)

### API intent and endpoint contract

Before changing or adding anything under `src/api/`, routes in `api.py`, or related models and tools, **read [`doc/ENDPOINTS.md`](doc/ENDPOINTS.md)**. That document is the source of truth for:

- Planned and current REST paths, methods, and request/response shapes
- Security behavior (authentication via `id`/`token` or `user`/`token`, panic rules, dark mode semantics)
- Product intent (what each endpoint is for and how it fits the dead-man's-switch flow)

Implementations should align with `doc/ENDPOINTS.md` unless the user explicitly asks to change the contract; if code and the doc diverge, call out the gap and prefer updating implementation toward the documented intent (or update the doc when the contract is intentionally changed).

---

## Configuration-Driven Development Pattern

**Critical Understanding**: This project is almost entirely controlled by `config.yaml`. Do NOT hardcode values.

### Config Structure (Reference `config.yaml`)
The YAML file has distinct sections that directly map to feature implementations:

```yaml
app:                  # Basic metadata (name, description, version)
settings:             # Service configuration (log_level, debug, dark_mode)
  log_level: INFO     # DEBUG, INFO, WARNING, ERROR, CRITICAL
  debug: false        # Extra logging and testing features (use with caution)
  dark_mode: true     # Suppresses API responses, rotates endpoints, writes startup file (use with caution)
email:                # Provider choice (AmazonSES, SendGrid, Mailgun, Gmail)
actions:              # On-death behaviors (send_email, delete_data, social_media, discord, custom_script)
defences:             # Safety mechanisms (panic_mode, canary messages, crash_and_burn)
```

**Pattern**: When adding features, parameters should be read from `config.yaml` via the `Settings` class in `src/tools/settings.py`, not hardcoded. Example:
```python
from src.tools.settings import Settings
settings = Settings()
email_provider = settings['email']['provider']  # Pluggable abstraction for different providers
panic_mode = settings['defences']['panic_mode']  # Can be changed without code modification
```

---

## Key Components & Integration Points

### 0. Settings Management (IMPLEMENTED)
- **Location**: `src/tools/settings.py` - `Settings` class
- **Usage**: Loaded in `main.py` and available throughout the application
- **Features**: Dictionary-style access, nested retrieval, safe defaults, key existence checks
- **Pattern**: All config access should go through Settings instance, never hardcode values

### 1. Check-in Scheduler (APScheduler)
- **Dependency**: `APScheduler==3.10.4` is installed but NOT YET INTEGRATED
- **Config Reference**: `defences.check_in_interval` (d/W/M/h/m), `check_in_window`, `check_in_timeout_count`
- **Pattern**: Build scheduler in `src/tools/` (e.g., `check_in_scheduler.py`) that reads config and triggers death sequence when missed

### 2. Email Provider Abstraction
- **Config**: `email.provider` (AmazonSES, SendGrid, Mailgun, Googlemail)
- **Pattern**: Create provider factory in `src/tools/email/` with base class and implementations per provider
- **Example**: `src/tools/email/base.py` (abstract), `src/tools/email/amazon_ses.py`, etc.

### 3. Panic Mode & Defense System
- **Config**: `defences.panic_mode` (permanent, lockdown, alert, ignore)
  - `permanent`: Locks down system completely, requires service restart to prevent death sequence
  - `lockdown`: Locks down until released via API call
  - `alert`: Sends alert to configured email address
  - `ignore`: Continues normal operation
- **Logic**: Triggered by multiple failed API attempts within `panic_timeframe`
- **Pattern**: Create `src/tools/defense.py` with `PanicModeHandler` that tracks attempts and enforces mode

### 4. Death Sequence Actions
- **Config**: `actions.*` flags (send_email, delete_data, social_media, discord, custom_script)
- **Pattern**: Each action should be a callable in `src/tools/actions/` that can be invoked independently
- **Example**: `src/tools/actions/email_dispatch.py`, `src/tools/actions/data_cleanup.py`

---

## Important Workflows

### Development Environment Setup (Windows)
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Database Setup
Schema is created automatically when the app starts (`python api.py`). `create_db.py` is internal-only.

### Running the Application
```bash
# Ensure venv is activated
python main.py       # Loads config and initializes system
python api.py        # Runs Flask debug server on localhost:5000
```

### Adding Dependencies
- Edit `requirements.txt` and run `pip install -r requirements.txt`
- Current stack: Flask 3.1.3, SQLAlchemy 2.0.46, APScheduler 3.10.4, PyYAML 6.0.3

---

## Code Conventions & Patterns

### Settings Access Pattern (IMPLEMENTED)
```python
# ✅ DO: Use Settings class for config access
from src.tools.settings import Settings
settings = Settings()
email_provider = settings['email']['provider']
check_in_interval = settings['defences']['check_in_interval']

# Safe access with defaults
log_level = settings.get('settings', {}).get('log_level', 'INFO')

# Check key existence
if 'actions' in settings:
    echo_count = settings['actions']['echo_count']
```

### Error Handling: Safe Defaults
- Service must gracefully degrade if missing config keys (e.g., optional email provider)
- Use `settings.get()` with defaults for non-critical features

### Database Access Pattern
```python
from api import app, db
from src.models.user import User

with app.app_context():
    user = User.query.filter_by(is_actual_user=True).first()  # Always use app context
```

### Application bootstrap
- **`bootstrap_app(app)`** in `src/bootstrap.py` runs at the bottom of `api.py` when the module is imported. It creates the schema, ensures one actual user, and writes startup files under `startup/`.
- **Side effect on import:** Any `import api` (REPL, scripts, WSGI, `main.py`) triggers bootstrap unless skipped. This is intentional so production entry points (`gunicorn api:app`) initialize without a separate DB script.
- **Skip bootstrap** when testing or tooling must not touch disk/DB: set `SOIDIED_SKIP_BOOTSTRAP=1` (see `test/conftest.py`) or `app.config['TESTING'] = True`.
- **Do not** document `python create_db.py` for operators. That script is schema-only, requires `SOIDIED_INTERNAL=1`, does not import `api`, and does not create the actual user or startup files — use `python api.py` instead.
- **`create_db.py` vs bootstrap:** Bootstrap owns full startup; `create_db.py` calls `run_standalone_schema_init()` in `src/db/schema.py` for rare internal schema-only use without loading the Flask API or running bootstrap twice.

### TODO Tracking
- `main.py:13`: "EXPAND settings" - Add additional settings initialization
- `main.py:14`: "GOAL : RUNNING DARK" (aspirational state name, likely security hardening)
- `main.py:24`: `print_hi()` is placeholder - will be removed in production
- **File Structure TODOs:**
  - Implement remaining API endpoints in `src/api/` (email.py, discord.py, facebook.py, file.py, unlock.py, dark_mode.py, …)
  - Implement additional database models in `src/models/` (email_message.py, file.py, social_message.py, …)
  - Integrate check-in scheduler (increment `missed_check_in_count`, death sequence)
  - Wire panic mode to `auth_fail_count` and rate limits
- Search codebase for "## TODO" comments to find open work

---

## Edge Cases & Safety Considerations

1. **Dark Mode Operation**: If `settings.dark_mode = true`, API responses are suppressed, endpoints rotate, and startup files are written to disk. **Use with extreme caution** - this makes the system difficult to interact with and debug.
2. **Crash and Burn**: If `defences.crash_and_burn = true`, system should auto-delete after death sequence. **Implement with extreme caution** - add safeguards.
3. **Data Deletion**: `actions.delete_data = true` triggers permanent data loss. Require confirmation or two-phase commit pattern.
4. **Echo Count**: `actions.echo_count` = multiple death notifications before deletion. Respect this for insurance against errors.
5. **Miss Count**: `defences.miss_count` threshold before triggering death. Logic must account for time windows, not just raw count.
6. **Canary Messages**: `defences.canary = true` sends periodic "system alive" pings. Must not trigger death sequence on failure.

---

## File Organization Strategy

When extending the codebase:
- **`src/api/`**: REST API endpoint implementations (check_in.py, email.py, discord.py, etc.) — match behavior and naming to [`doc/ENDPOINTS.md`](doc/ENDPOINTS.md)
- **`src/models/`**: Database model definitions (user.py, email_message.py, social_message.py, etc.)
- **`src/db/`**: Database utilities and connection management
- **`src/tools/`**: Feature implementation modules (email, scheduler, defense, actions)
- **`test/`**: Test suite mirroring `src/` structure
- Keep `main.py` and `api.py` minimal - they're just orchestration layers
- Database models: Use SQLAlchemy models in `src/models/` instead of inline in `api.py`

---

## Red Flags & Questions to Ask

### Implemented (current baseline)
- **Check-in state** on `User`: `last_check_in`, `missed_check_in_count`, `auth_fail_count`; `id` and `access_token` are UUID4 strings (`id` is unique PK).
- **Actual user**: `is_actual_user` (ENDPOINTS “main” user); only one allowed; bootstrap creates one on startup.
- **API (implemented):** `PUT /api/v1/checkin`, `GET /api/v1/checkin/status`, `GET /api/v1/utils/api` (startup file with credentials + routes).
- **Auth:** Shared `id`/`token` JSON body via `src/api/auth.py`; failed auth increments `auth_fail_count` only (not missed check-ins).
- **Startup files:** `startup/actual_user.md`, `startup/api.txt` (gitignored); refreshed on bootstrap.
- **Tests:** `test/test_check_in.py`, `test/test_actual_user.py` (pytest; set `SOIDIED_SKIP_BOOTSTRAP=1` in conftest).

### Still open
- ❓ **`missed_check_in_count` is not incremented by a scheduler yet** — overdue check-ins return `Status: ALERT` via deadline math; `DEAD` needs APScheduler (or similar) to bump the counter per `defences.miss_count`.
- ❓ **Death sequence persistence** — no dedicated death-state column or workflow; derived from counters and status logic only.
- ❓ **Panic mode** — `auth_fail_count` is stored but not wired to `defences.panic_threshold` / lockdown.
- **Dark mode (rotation)** — `settings.dark_mode: true` rotates paths at boot; `PUT /api/v1/darkmode` enables in-memory rotation for this process only. Canonical paths return 404; `startup/api.txt` lists active secret paths. Response masking (404 on all responses) not implemented yet.
- ❓ **Custom scripts** — `actions.custom_script` needs safe execution (sanitization, sandbox).
- ⚠️ **Email provider API keys** — not in repo; use environment variables / `.env` pattern.
- ❓ **Remaining endpoints** — user management, messages, utils (ping, unlock, debug, ducky), dark mode per `doc/ENDPOINTS.md`.
- ❓ **Email provider abstraction** — `src/tools/email/` not built.
- ❓ **Additional models** — `email_message`, `file`, `social_message`, etc.

---

## Related Documentation

- **Endpoint contract & product intent**: [`doc/ENDPOINTS.md`](doc/ENDPOINTS.md) — reference when implementing or changing API behavior
- **Operational runbook**: [`doc/RUNBOOK.md`](doc/RUNBOOK.md) — install, database init, and local run steps
- **Config Reference**: See `config.yaml` inline comments for all available settings
- **Flask Documentation**: https://flask.palletsprojects.com/ (API framework)
- **SQLAlchemy**: https://docs.sqlalchemy.org/ (ORM for database)
- **APScheduler**: https://apscheduler.readthedocs.io/ (Scheduled task execution)

---

## Cursor Cloud specific instructions

### VM prerequisites

Ubuntu/Debian cloud VMs need the `python3.12-venv` system package before `python3 -m venv` works (`sudo apt-get install -y python3.12-venv`). This is a one-time image/snapshot concern, not part of the repo update script.

### Dependency refresh

After the update script runs, activate the venv before Python commands:

```bash
source venv/bin/activate
```

Or call `venv/bin/python` / `venv/bin/pytest` directly without activating.

### Running the API (required for E2E)

Only one process is needed for local development: the Flask API.

```bash
source venv/bin/activate
python api.py
```

Listens on `http://127.0.0.1:5000`. Bootstrap creates `database.db` and writes credentials to `startup/actual_user.md` on first start.

Keep `settings.dark_mode: false` in `config.yaml` for normal local/API testing. When `dark_mode` is `true`, canonical routes return 404 and paths are rotated.

### Tests

```bash
source venv/bin/activate
pytest -v
```

Tests set `SOIDIED_SKIP_BOOTSTRAP=1` via `test/conftest.py` and use an in-memory SQLite DB — no running server or `database.db` required.

### Lint

No linter or formatter is configured in this repo (no ruff/flake8/pyproject CI). Validation is via `pytest -v`.

### Quick smoke test (after starting `api.py`)

1. `curl http://127.0.0.1:5000/` → `Welcome to the SoIDied App!`
2. Read `id` / `token` from `startup/actual_user.md`
3. `PUT /api/v1/checkin` with JSON body `{"id": "...", "token": "..."}` → next check-in deadline
4. `GET /api/v1/checkin/status` with the same body → `{"Status": "OK"}`

See [`doc/RUNBOOK.md`](doc/RUNBOOK.md) for curl examples.
