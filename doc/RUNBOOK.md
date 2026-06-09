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

Starting the application with `run.sh` and Flask **bootstrap**:

1. `run.sh` ensures the local master-key file exists, then exports it as `SOIDIED_MASTER_KEY`
2. Bootstrap creates SQLite tables if missing (`database.db`)
3. Bootstrap ensures exactly one **actual user** (`is_actual_user=true`) with UUID4 `id` and `token`
4. Bootstrap writes startup files (gitignored under `startup/`):
   - `startup/actual_user.md` — credentials only
   - `startup/api.txt` — credentials plus documented API routes (served by `GET /api/v1/utils/api`)
   - `startup/.soidied_master_key` — local master encryption key created by `run.sh`
5. Bootstrap starts the background **check-in tracker** (APScheduler). It polls every `defences.check_in_poll_seconds` (default 60s) and advances the actual user's `missed_check_in_count` once `next_check_in_deadline` passes, so `GET /api/v1/checkin/status` can reach `DEAD` without a manual check. A successful check-in re-freezes the deadline and resets the count; the tracker never lowers it. The tracker is skipped under tests (`SOIDIED_SKIP_BOOTSTRAP=1`).

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

On Linux/macOS, prefer `run.sh` so the app starts with a persistent local master key:

```bash
./run.sh
```

If `startup/.soidied_master_key` does not exist, the script creates it with a strong random value and file mode `600`. On later starts, it reuses that file and exports it as `SOIDIED_MASTER_KEY` before running `api.py`.

You can override paths or Python executable when needed:

```bash
SOIDIED_MASTER_KEY_FILE=/secure/path/soidied.key SOIDIED_PYTHON=python ./run.sh
```

If `SOIDIED_MASTER_KEY` is already set and the key file is missing or empty, `run.sh` writes the current environment value to the key file, then uses the file as the source of truth.

Direct startup still works, but it will not create/export the master key:

```bash
python api.py
```

Default URL: [http://127.0.0.1:5000](http://127.0.0.1:5000) (or `https://localhost:5000` when `tls.enabled: true` — see [Serving over HTTPS (TLS)](#serving-over-https-tls)).

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

### Serving over HTTPS (TLS)

By default the server runs plain HTTP. To encrypt the wire (so a sniffer such as Wireshark cannot read the `id`/`token` payload), enable TLS in `config.yaml`:

```yaml
tls:
  enabled: true
  host: 127.0.0.1
  port: 5000
  cert_file: certs/cert.pem
  key_file: certs/key.pem
  common_name: localhost
  auto_generate: true
  valid_days: 825
  hsts: true
```

With `auto_generate: true`, starting the app (`python api.py`) generates a self-signed certificate at `cert_file`/`key_file` on first run and prints its **SHA-256 fingerprint**. Pin that fingerprint in your client (curl/DuckyScript/Postman) to defeat man-in-the-middle attacks — a self-signed cert is not trusted by a public CA, so verification relies on the pin, not the CA chain.

The `certs/` directory and `*.pem`/`*.key` files are gitignored; never commit them.

Calling endpoints once TLS is on (verify against the generated cert with `--cacert certs/cert.pem`; same routes as the HTTP examples above, just `https://`):

```bash
# Register a check-in:
curl --cacert certs/cert.pem -X PUT https://localhost:5000/api/v1/checkin ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"<user-uuid>\", \"token\": \"<access-token-uuid>\"}"

# Check-in status:
curl --cacert certs/cert.pem -X GET https://localhost:5000/api/v1/checkin/status ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"<user-uuid>\", \"token\": \"<access-token-uuid>\"}"

# Startup API file (actual user only):
curl --cacert certs/cert.pem -X GET https://localhost:5000/api/v1/utils/api ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"<user-uuid>\", \"token\": \"<access-token-uuid>\"}"

# Health check:
curl --cacert certs/cert.pem https://localhost:5000/

# For a quick local test you can skip verification with -k (NOT for production):
curl -k -X GET https://localhost:5000/api/v1/checkin/status ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"<user-uuid>\", \"token\": \"<access-token-uuid>\"}"
```

Notes:
- `port: 443` typically requires elevated privileges; the default `5000` does not.
- HTTPS responses include a `Strict-Transport-Security` header when `hsts: true`.
- For a public deployment behind a reverse proxy (nginx/Caddy) terminating TLS instead, leave `tls.enabled: false` and let the proxy handle certificates.
- To regenerate the cert, delete the files in `certs/` and restart the app.

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
3. Run `./run.sh` on Linux/macOS, or `python api.py` if you are not using the local key wrapper
4. Open `startup/actual_user.md` or call `GET /api/v1/utils/api`
5. Run `pytest -v` when validating changes

---

## Local master key and crypto-shredding

`run.sh` manages a reusable local master key at `startup/.soidied_master_key`. The `startup/` directory is gitignored, so the key is not committed with the repository.

This key is used for encrypted-at-rest message attachments. The app can decrypt attachment data while `SOIDIED_MASTER_KEY` is available to the running process. Deleting the key file makes data encrypted with that key practically unrecoverable, even if encrypted files or backups remain.

Important operational notes:

- Back up the key only if you intentionally want encrypted data to survive host loss.
- Protect the key file with filesystem permissions; `run.sh` sets mode `600`.
- Do not copy the key into docs, logs, commits, issue comments, or chat.
- Deleting the key is destructive for any data encrypted with it. Treat key deletion as crypto-shredding.
- If the key file exists, it wins over a different `SOIDIED_MASTER_KEY` value in the environment. Remove or replace the file intentionally if you need to rotate keys.

---

## Troubleshooting

| Problem | Likely cause | What to try |
|---------|----------------|-------------|
| `ModuleNotFoundError` | Venv not activated or deps not installed | Activate venv; `pip install -r requirements.txt` |
| `./run.sh: Permission denied` | Script is not executable on your checkout | Run `chmod +x run.sh`, then `./run.sh` |
| `SOIDIED_MASTER_KEY is empty` | Key file exists but is empty and no key could be loaded | Delete `startup/.soidied_master_key` and rerun `./run.sh`, or set `SOIDIED_MASTER_KEY` first |
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
