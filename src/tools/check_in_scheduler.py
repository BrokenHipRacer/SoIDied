"""Background time tracker for check-in timers.

A ``BackgroundScheduler`` (APScheduler) polls on a fixed interval and recomputes the
actual user's ``missed_check_in_count`` from the frozen ``next_check_in_deadline``
(``last_check_in`` + the configured check-in period). The poll is **never-decreasing**:
it only ever raises the count (``max`` of the current and computed values), so a poll
can never walk it back if config or the clock changes. A successful check-in is the
sole path that resets ``last_check_in``, re-freezes the deadline, and clears the count
to 0 — which the next tick then honours.

Legacy rows with ``last_check_in`` but no persisted deadline are backfilled via
``effective_deadline`` on the first evaluation tick.

Only one process runs the tracker at a time: multi-worker deployments acquire an
exclusive lock (``defences.check_in_scheduler_lock_file``) before starting APScheduler.
"""

from __future__ import annotations

import atexit
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from src.db.extensions import db
from src.tools.actual_user import get_actual_user
from src.tools.check_in import check_in_period, effective_deadline
from src.tools.scheduler_leader import (
    release_scheduler_leadership,
    scheduler_lock_path,
    try_acquire_scheduler_leadership,
)
from src.tools.settings import Settings

DEFAULT_POLL_SECONDS = 60
JOB_ID = 'check_in_tracker'

_scheduler: BackgroundScheduler | None = None
_atexit_registered = False


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
    """Recompute the actual user's missed count from the effective deadline (never-decreasing).

    Uses ``effective_deadline`` so legacy rows with ``last_check_in`` but no frozen
    deadline are evaluated and backfilled on first tick. The count only ever rises here;
    a successful check-in is the sole reset path. Returns the resulting missed count, or
    ``None`` when there is no actual user or the user has never checked in.
    Must be called inside a Flask application context.
    """
    settings = settings or Settings()
    user = get_actual_user()
    if user is None:
        return None

    deadline = effective_deadline(user, settings)
    if deadline is None:
        return None

    dirty = False
    if user.next_check_in_deadline is None:
        user.next_check_in_deadline = deadline
        dirty = True

    now = datetime.now(timezone.utc)
    computed = compute_missed_count(deadline, now, check_in_period(settings))
    new_count = max(user.missed_check_in_count, computed)
    if new_count != user.missed_check_in_count:
        user.missed_check_in_count = new_count
        dirty = True

    if dirty:
        db.session.commit()
    return new_count


def _poll_job(app) -> None:
    """Scheduler entry point. Failures are logged but never crash the background thread."""
    with app.app_context():
        try:
            evaluate_actual_user_check_in()
        except Exception as exc:  # noqa: BLE001 — a tracker tick must not kill the scheduler
            print(f'[scheduler] check-in evaluation failed: {exc}')
        finally:
            db.session.remove()


def start_check_in_scheduler(app, settings: Settings | None = None) -> BackgroundScheduler | None:
    """Start the background tracker (idempotent). Returns the running scheduler.

    Skipped under the Werkzeug reloader's parent process so debug runs do not start two
    schedulers. In multi-worker deployments, only the process that acquires the leader
    lock starts the tracker.
    """
    global _scheduler, _atexit_registered

    if os.environ.get('WERKZEUG_RUN_MAIN') == 'false':
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    settings = settings or Settings()
    lock_path = scheduler_lock_path(settings)
    if not try_acquire_scheduler_leadership(lock_path):
        print(
            f'[scheduler] check-in tracker not started — another worker holds '
            f'{lock_path}'
        )
        return None

    poll_seconds = poll_interval_seconds(settings)
    scheduler = BackgroundScheduler(daemon=True, timezone='UTC')
    scheduler.add_job(
        _poll_job,
        'interval',
        seconds=poll_seconds,
        args=[app],
        id=JOB_ID,
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    _scheduler = scheduler
    if not _atexit_registered:
        atexit.register(stop_check_in_scheduler)
        _atexit_registered = True
    print(f'[scheduler] check-in tracker started (poll every {poll_seconds}s, lock {lock_path})')
    return scheduler


def stop_check_in_scheduler() -> None:
    """Stop the tracker if running and release the leader lock."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    release_scheduler_leadership()
