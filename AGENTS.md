# AGENTS.md - AI Development Guide for SoIDied

## Project Overview

**SoIDied** is a post-mortem digital notification system ("Digital Dead Man's Switch"). It monitors user check-ins and automatically sends pre-configured information to contacts when the user dies or misses scheduled check-ins. The project is entirely **configuration-driven** via YAML.

### Core Architecture
- **Entry Point**: `main.py` loads config via `Settings` class and initializes the system
- **Configuration Management**: `src/tools/settings.py` provides `Settings` class for YAML config access
- **REST API**: `src/api/` module with endpoint implementations; `api.py` provides Flask-RESTful endpoints with SQLAlchemy ORM (SQLite backend)
- **Data Layer**: `src/models/` for database models; `src/db/` for database utilities; `create_db.py` initializes schema
- **Tooling**: `src/tools/` module for feature implementations (scheduler, email, defense, actions)

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
```bash
python create_db.py  # Initializes SQLite schema with User model
```

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
from api import app, db, User
with app.app_context():
    user = User.query.filter_by(username='name').first()  # Always use app context
```

### TODO Tracking
- `main.py:13`: "EXPAND settings" - Add additional settings initialization
- `main.py:14`: "GOAL : RUNNING DARK" (aspirational state name, likely security hardening)
- `main.py:24`: `print_hi()` is placeholder - will be removed in production
- **File Structure TODOs:**
  - Implement API endpoints in `src/api/` (check_in.py, email.py, discord.py, facebook.py, file.py, unlock.py)
  - Implement database models in `src/models/` (user.py, email_message.py, file.py, social_message.py)
  - Implement database utilities in `src/db/`
  - Create test suite structure in `test/` mirroring `src/`
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
- **`src/api/`**: REST API endpoint implementations (check_in.py, email.py, discord.py, etc.)
- **`src/models/`**: Database model definitions (user.py, email_message.py, social_message.py, etc.)
- **`src/db/`**: Database utilities and connection management
- **`src/tools/`**: Feature implementation modules (email, scheduler, defense, actions)
- **`test/`**: Test suite mirroring `src/` structure
- Keep `main.py` and `api.py` minimal - they're just orchestration layers
- Database models: Use SQLAlchemy models in `src/models/` instead of inline in `api.py`

---

## Red Flags & Questions to Ask

- ❓ Where are check-in records stored? (Not in User model currently - needs table design)
- ❓ How is "death" state persisted? (No status column in User model)
- ❓ How are custom scripts executed safely? (Potential security issue - sanitization needed)
- ⚠️ Email credentials: Where are provider API keys stored? (Not visible - likely environment variables, add to `.env` pattern)
- ❓ Need to implement API endpoints in `src/api/` (check_in.py, email.py, discord.py, facebook.py, file.py, unlock.py)
- ❓ Need to implement database models in `src/models/` (user.py, email_message.py, file.py, social_message.py)
- ❓ Need to implement email provider abstraction in `src/tools/email/`
- ❓ Need to implement check-in scheduler using APScheduler (currently installed but unused)
- ❓ Need to implement panic mode defense system in `src/tools/defense.py`

---

## Related Documentation

- **Config Reference**: See `config.yaml` inline comments for all available settings
- **Flask Documentation**: https://flask.palletsprojects.com/ (API framework)
- **SQLAlchemy**: https://docs.sqlalchemy.org/ (ORM for database)
- **APScheduler**: https://apscheduler.readthedocs.io/ (Scheduled task execution)
