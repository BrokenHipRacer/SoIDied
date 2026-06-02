# SoIDied Runbook

Operational guide for setting up, initializing, and running SoIDied locally. For architecture and configuration reference, see [README.md](../README.md) and [AGENTS.md](../AGENTS.md).

## Prerequisites

- Python 3.8+ (3.10+ recommended)
- Git (to clone the repository)
- A shell: PowerShell on Windows, or bash on Linux/macOS

All commands below assume your working directory is the project root (the folder that contains `requirements.txt`, `api.py`, and `config.yaml`).

---

## Install requirements

Create an isolated virtual environment and install Python dependencies from `requirements.txt`.

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Verify installation

With the virtual environment still activated:

```bash
pip list
pytest --version
```

You should see project packages such as Flask, SQLAlchemy, APScheduler, PyYAML, and pytest.

### Optional: upgrade pip

```bash
python -m pip install --upgrade pip
```

---

## Database and startup files (automatic)

Do **not** run `create_db.py` manually. It is internal-only and exits with instructions if invoked directly.

Starting the application runs **bootstrap**, which:

1. Creates SQLite tables if missing (`database.db`)
2. Ensures exactly one **actual user** (`is_actual_user=true`) with UUID4 `id` and `token`
3. Writes startup files (gitignored under `startup/`):
   - `startup/actual_user.md` — credentials only
   - `startup/api.txt` — credentials plus documented API routes (served by `GET /api/v1/utils/api`)

Configure paths in `config.yaml`:

```yaml
settings:
  actual_user_credentials_file: startup/actual_user.md
  api_startup_file: startup/api.txt
```

### Schema changes and existing data

`create_all()` does not migrate existing columns. After model changes, back up and remove `database.db`, then start the app again so bootstrap recreates schema and startup files.

---

## Start the application

### 1. Configure (recommended)

Edit `config.yaml` for log level, defences, email provider, and actions.

For **local API testing**, set `settings.dark_mode: false`. When `dark_mode` is `true`, protected routes return 404.

### 2. Start the API server

```bash
python api.py
```

Default URL: [http://127.0.0.1:5000](http://127.0.0.1:5000)

Read credentials from `startup/actual_user.md` or `startup/api.txt`, or call `GET /api/v1/utils/api` with your `id` and `token` (see below).

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health / welcome message |
| `/api/v1/checkin` | PUT | Register a check-in (`id` and `token` in JSON body) |
| `/api/v1/checkin/status` | GET | Check-in status (`id` and `token` in JSON body) |
| `/api/v1/utils/api` | GET | Startup API file (`id` and `token`; actual user only) |

See [`doc/ENDPOINTS.md`](ENDPOINTS.md) for the full API contract, dark mode, and panic behavior.

### Request bodies on GET routes

Some endpoints expect a JSON body on `GET`. Example:

```bash
curl -X PUT http://127.0.0.1:5000/api/v1/checkin ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"<user-uuid>\", \"token\": \"<access-token-uuid>\"}"
```

```bash
curl -X GET http://127.0.0.1:5000/api/v1/checkin/status ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"<user-uuid>\", \"token\": \"<access-token-uuid>\"}"
```

```bash
curl -X GET http://127.0.0.1:5000/api/v1/utils/api ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"<user-uuid>\", \"token\": \"<access-token-uuid>\"}"
```

On Linux/macOS, use `\` for line continuation or send JSON on one line.

### 3. Start the main process (config loader)

```bash
python main.py
```

Imports `api`, so bootstrap still runs. For API testing, `python api.py` is sufficient.

---

## Run tests

```bash
pytest -v
```

Tests set `SOIDIED_SKIP_BOOTSTRAP=1` and use an in-memory database; they do not require `database.db` or startup files.

---

## Typical startup sequence

1. Install requirements (virtualenv + `pip install -r requirements.txt`)
2. Set `settings.dark_mode: false` in `config.yaml` for local dev (optional)
3. Run `python api.py`
4. Open `startup/actual_user.md` or call `GET /api/v1/utils/api`
5. Run `pytest -v` when validating changes

---

## Troubleshooting

| Problem | Likely cause | What to try |
|---------|----------------|-------------|
| `ModuleNotFoundError` | Venv not activated or deps not installed | Activate venv; `pip install -r requirements.txt` |
| `create_db.py is for internal use only` | Ran DB script manually | Use `python api.py` instead |
| All API routes return 404 | `dark_mode: true` in config | Set `dark_mode: false` for local testing |
| `no such table: users` | Old or missing database | Delete `database.db`; restart `python api.py` |
| Check-in returns 401 | Wrong `id`/`token` | Read `startup/actual_user.md` after bootstrap |
| Port 5000 in use | Another process on 5000 | Stop the other process or change port in `api.py` |

---

## Related docs

- [README.md](../README.md) — overview and configuration
- [doc/ENDPOINTS.md](ENDPOINTS.md) — planned and current API behavior
- [AGENTS.md](../AGENTS.md) — development patterns for contributors and agents
