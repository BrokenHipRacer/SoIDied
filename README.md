# SoIDied – Digital Dead Man's Switch

A post-mortem digital notification system that monitors user check-ins and automatically sends pre-configured information to contacts when the user dies or misses scheduled check-ins.

If feeling generous, consider donating to support development: [Buy me a coffee](https://buymeacoffee.com/brokenhipracer)


## ⚠️ Important Warning

This system handles sensitive post-mortem notifications and data deletion. **Use with extreme caution** – misconfiguration could result in unintended data loss or premature notifications.

## Features

- **Configuration-Driven**: Entirely controlled via YAML configuration – no hardcoded values
- **Check-in Monitoring**: Tracks user check-ins with configurable intervals and thresholds
- **Multi-Provider Email**: Support for Amazon SES, SendGrid, Mailgun, and Gmail
- **Dark Mode Operation**: Suppresses API responses, rotates endpoints, and writes startup files for stealth operation
- **Death Sequence Actions**:
  - Email notifications with custom content
  - Social media posts (planned)
  - Discord notifications (planned)
  - Custom script execution (planned)
  - Data deletion with safeguards
- **Defense Mechanisms**:
  - Panic mode with rate limiting (permanent/lockdown/alert/ignore modes)
  - Canary messages for system health
  - Crash and burn self-destruction
  - Multiple safety thresholds

## Quick Start

### Prerequisites
- Python 3.8+
- Windows/Linux/macOS

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SoIDied
   ```

2. **Set up a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux/macOS
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the system**
   Edit `config.yaml` with your settings:
   ```yaml
   app:
     name: SoIDied
     description: Your description here
     version: 0.0.1

   email:
     provider: AmazonSES  # Choose: AmazonSES, SendGrid, Mailgun, Google email
     alert_email: your-email@example.com

   # ... configure other settings
   ```

5. **Initialize database**
   ```bash
   python create_db.py
   ```

6. **Run the application**
   ```bash
   # Start main system
   python main.py

   # Or run API server
   python api.py
   ```

## Configuration

The system is entirely configuration-driven. See `config.yaml` for all available options:

- **`app`**: Basic project metadata
- **`settings`**: Service configuration
  - `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - `debug`: Extra logging and testing features (use with caution)
  - `dark_mode`: Suppresses API responses, changes endpoints (use with caution)
- **`email`**: Email provider configuration
- **`actions`**: Death sequence behaviors
- **`defences`**: Safety mechanisms and thresholds

### Key Configuration Sections

```yaml
settings:
  log_level: INFO        # DEBUG, INFO, WARNING, ERROR, CRITICAL
  debug: false           # Extra logging and testing features
  dark_mode: true        # Suppresses API responses, rotates endpoints

defences:
  check_in_interval: d        # d=days, W=weeks, M=months, h=hours, m=minutes
  check_in_window: 7          # Grace period for check-ins
  miss_count: 1               # Missed check-ins before death sequence
  panic_mode: lockdown        # permanent, lockdown, alert, ignore
    # permanent: Complete lockdown, requires restart
    # lockdown: Locks down until API release
    # alert: Sends email alert
    # ignore: Continues normal operation
  crash_and_burn: true        # Self-destruct after death sequence

actions:
  send_email: true
  delete_data: true
  echo_count: 2               # Multiple notifications before deletion
```

## Architecture

```
SoIDied/
├── main.py              # Entry point, loads config
├── api.py               # Flask app orchestration
├── config.yaml          # Configuration file
├── create_db.py         # Database initialization
├── requirements.txt     # Python dependencies
├── AGENTS.md           # AI development guide
├── README.md           # This file
├── src/
│   ├── api/            # REST API endpoints
│   │   ├── check_in.py # Check-in management
│   │   ├── email.py    # Email configuration
│   │   ├── discord.py  # Discord integration
│   │   ├── facebook.py # Facebook integration
│   │   ├── file.py     # File management
│   │   └── unlock.py   # System unlock
│   ├── models/         # Database models
│   │   ├── user.py
│   │   ├── email_message.py
│   │   ├── file.py
│   │   └── social_message.py
│   ├── db/             # Database utilities
│   └── tools/          # Core features
│       └── settings.py # Configuration management
├── test/               # Test suite
└── database.db         # SQLite database
```

## API Endpoints

The system provides RESTful endpoints for:

- User management
- Check-in registration
- Status monitoring
- Configuration updates

Run `python api.py` to start the development server on `localhost:5000`.

## Development

### For AI Agents
See [`AGENTS.md`](AGENTS.md) for detailed development guidelines, code patterns, and integration points.

### Code Conventions
- **Configuration-driven**: Never hardcode values – use the Settings class
- **Safe defaults**: Graceful degradation for missing config keys
- **Database context**: Always use `app.app_context()` for database operations

### Testing
```bash
# Create tests directory structure mirroring src/
# Run tests (when implemented)
pytest tests/
```

## Security Considerations

- **Data Deletion**: `actions.delete_data` triggers permanent data loss
- **Custom Scripts**: `actions.custom_script` executes arbitrary code - sanitize inputs
- **API Keys**: Store email provider credentials securely (environment variables recommended)
- **Panic Mode**: Multiple failed attempts can trigger lockdown or death sequence

## Contributing

1. Read [`AGENTS.md`](AGENTS.md) for development patterns
2. Follow configuration-driven principles
3. Add tests for new features
4. Update documentation

## License

See [LICENSE](LICENSE) file.

## Status

**Early Development** – File structure established, core components pending implementation:

- [x] Project structure with modular directories (`src/api/`, `src/models/`, `src/db/`, `src/tools/`)
- [x] Settings management class (`src/tools/settings.py`)
- [x] Basic Flask app setup (`api.py`)
- [x] Configuration system (`config.yaml`)
- [x] Virtual environment setup
- [ ] API endpoint implementations (`src/api/*.py`)
- [ ] Database model definitions (`src/models/*.py`)
- [ ] Check-in scheduler integration
- [ ] Email provider abstractions
- [ ] Panic mode defense system
- [ ] Death sequence actions
- [ ] Comprehensive testing

## Disclaimer

This software handles sensitive post-mortem scenarios. The authors are not responsible for any data loss, premature notifications, or other unintended consequences resulting from misconfiguration or misuse.
