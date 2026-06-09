"""Background time tracker for check-in timers.

A ``BackgroundScheduler`` (APScheduler) polls on a fixed interval and recomputes the
actual user's ``missed_check_in_count`` from elapsed wall-clock time. The count is
*derived* from ``last_check_in`` and the configured check-in period, so the poll is
idempotent: re-running it never double-counts, and a fresh check-in (which resets
``last_check_in`` and the count) is honoured on the next tick.

This closes the gap noted in AGENTS.md: ``compute_check_in_status`` could only return
``ALERT`` from deadline math, but nothing advanced the counter toward ``DEAD``.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from src.db.extensions import db
from src.tools.actual_user import get_actual_user
from src.tools.check_in import check_in_period
from src.tools.settings import Settings

DEFAULT_POLL_SECONDS = 60
JOB_ID = 'check_in_tracker'

_scheduler: BackgroundScheduler | None = None


def poll_interval_seconds(settings: Settings | None = None) -> int:
    """How often the tracker re-evaluates the deadline (config-driven, safe default)."""
    settings = settings or Settings()
    configured = settings.get('defences', {}).get(
        'check_in_poll_seconds',
        DEFAULT_POLL_SECONDS,
    )
    try:
        interval = int(configured)
    except (TypeError, ValueError):
        return DEFAULT_POLL_SECONDS
    return interval if interval > 0 else DEFAULT_POLL_SECONDS


def compute_missed_count(
    deadline: datetime | None,
    now: datetime,
    period: timedelta,
) -> int:
    """Missed check-ins given a frozen ``deadline`` (``last_check_in`` + interval period).

    ``0`` until ``now`` passes the deadline, ``1`` once it does, and one more for every
    additional period that elapses without a check-in. Returns ``0`` when there is no
    deadline (never checked in) or the period is non-positive.
    """
    if deadline is None or period.total_seconds() <= 0:
        return 0
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if now <= deadline:
        return 0
    overdue = (now - deadline).total_seconds()
    return 1 + int(overdue // period.total_seconds())


def evaluate_actual_user_check_in(settings: Settings | None = None) -> int | None:
    """Recompute the actual user's missed count from the frozen deadline (never-decreasing).

    The count only ever rises here: a successful check-in is the sole reset path. Returns
    the resulting missed count, or ``None`` when there is no actual user or the user has
    never checked in (status stays ``ALERT`` rather than advancing to ``DEAD``).
    Must be called inside a Flask application context.
    """
    settings = settings or Settings()
    user = get_actual_user()
    if user is None or user.next_check_in_deadline is None:
        return None

    now = datetime.now(timezone.utc)
    computed = compute_missed_count(
        user.next_check_in_deadline,
        now,
        check_in_period(settings),
    )
    new_count = max(user.missed_check_in_count, computed)
    if new_count != user.missed_check_in_count:
        user.missed_check_in_count = new_count
        db.session.commit()
    return new_count


def _poll_job(app) -> None:
    """Scheduler entry point. Failures are logged but never crash the background thread."""
    with app.app_context():
        try:
            evaluate_actual_user_check_in()
        except Exception as exc:  # noqa: BLE001 — a tracker tick must not kill the scheduler
            print(f'[scheduler] check-in evaluation failed: {exc}')


def start_check_in_scheduler(app, settings: Settings | None = None) -> BackgroundScheduler | None:
    """Start the background tracker (idempotent). Returns the running scheduler.

    Skipped under the Werkzeug reloader's parent process so debug runs do not start two
    schedulers.
    """
    global _scheduler

    if os.environ.get('WERKZEUG_RUN_MAIN') == 'false':
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    settings = settings or Settings()
    scheduler = BackgroundScheduler(daemon=True, timezone='UTC')
    scheduler.add_job(
        _poll_job,
        'interval',
        seconds=poll_interval_seconds(settings),
        args=[app],
        id=JOB_ID,
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_check_in_scheduler() -> None:
    """Stop the tracker if running (used by tests and clean shutdown)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
