from datetime import datetime, timedelta, timezone

import pytest

from api import app, db
import src.tools.check_in_scheduler as check_in_scheduler_module
from src.models.user import User
from src.tools.check_in import compute_check_in_status
from src.tools.check_in_scheduler import (
    DEFAULT_POLL_SECONDS,
    compute_missed_count,
    evaluate_actual_user_check_in,
    poll_interval_seconds,
    start_check_in_scheduler,
    stop_check_in_scheduler,
)
from src.tools.scheduler_leader import release_scheduler_leadership


@pytest.fixture(autouse=True)
def _reset_scheduler_state():
    stop_check_in_scheduler()
    check_in_scheduler_module._atexit_registered = False
    check_in_scheduler_module._scheduler = None
    release_scheduler_leadership()
    yield
    stop_check_in_scheduler()
    check_in_scheduler_module._atexit_registered = False
    check_in_scheduler_module._scheduler = None
    release_scheduler_leadership()


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def main_user(client):
    user = User(is_actual_user=True)
    db.session.add(user)
    db.session.commit()
    return user


def _period() -> timedelta:
    return timedelta(days=7)


def test_compute_missed_count_before_deadline():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    deadline = now + timedelta(days=3)
    assert compute_missed_count(deadline, now, _period()) == 0


def test_compute_missed_count_just_past_deadline():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    deadline = now - timedelta(hours=1)
    assert compute_missed_count(deadline, now, _period()) == 1


def test_compute_missed_count_multiple_periods_past_deadline():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    deadline = now - timedelta(days=15)
    assert compute_missed_count(deadline, now, _period()) == 3


def test_compute_missed_count_no_deadline():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert compute_missed_count(None, now, _period()) == 0


def test_compute_missed_count_treats_naive_as_utc():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    naive_deadline = (now - timedelta(hours=1)).replace(tzinfo=None)
    assert compute_missed_count(naive_deadline, now, _period()) == 1


def test_compute_missed_count_non_positive_period():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    deadline = now - timedelta(days=10)
    assert compute_missed_count(deadline, now, timedelta(0)) == 0


def test_compute_missed_count_exactly_at_deadline():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    deadline = now
    assert compute_missed_count(deadline, now, _period()) == 0


def test_evaluate_raises_missed_count_when_overdue(client, main_user):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=10)
    main_user.next_check_in_deadline = now - timedelta(days=3)
    db.session.commit()

    result = evaluate_actual_user_check_in()

    assert result == 1
    db.session.refresh(main_user)
    assert main_user.missed_check_in_count == 1


def test_evaluate_leaves_count_zero_before_deadline(client, main_user):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=1)
    main_user.next_check_in_deadline = now + timedelta(days=6)
    db.session.commit()

    result = evaluate_actual_user_check_in()

    assert result == 0
    db.session.refresh(main_user)
    assert main_user.missed_check_in_count == 0


def test_evaluate_is_idempotent(client, main_user):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=10)
    main_user.next_check_in_deadline = now - timedelta(days=3)
    db.session.commit()

    first = evaluate_actual_user_check_in()
    second = evaluate_actual_user_check_in()

    assert first == second == 1
    db.session.refresh(main_user)
    assert main_user.missed_check_in_count == 1


def test_evaluate_never_decreases_existing_count(client, main_user):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=1)
    main_user.next_check_in_deadline = now + timedelta(days=6)
    main_user.missed_check_in_count = 5
    db.session.commit()

    result = evaluate_actual_user_check_in()

    assert result == 5
    db.session.refresh(main_user)
    assert main_user.missed_check_in_count == 5


def test_evaluate_backfills_deadline_from_last_check_in(client, main_user):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=1)
    main_user.next_check_in_deadline = None
    db.session.commit()

    evaluate_actual_user_check_in()

    db.session.refresh(main_user)
    assert main_user.next_check_in_deadline is not None
    assert main_user.next_check_in_deadline > main_user.last_check_in


def test_evaluate_returns_none_without_deadline(client, main_user):
    main_user.next_check_in_deadline = None
    db.session.commit()

    assert evaluate_actual_user_check_in() is None
    db.session.refresh(main_user)
    assert main_user.missed_check_in_count == 0


def test_evaluate_returns_none_without_actual_user(client):
    assert evaluate_actual_user_check_in() is None


def test_evaluate_does_not_commit_when_nothing_changes(client, main_user, monkeypatch):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=1)
    main_user.next_check_in_deadline = now + timedelta(days=6)
    main_user.missed_check_in_count = 0
    db.session.commit()

    commits = []
    monkeypatch.setattr(
        'src.tools.check_in_scheduler.db.session.commit',
        lambda: commits.append(True),
    )

    assert evaluate_actual_user_check_in() == 0
    assert commits == []


def test_evaluate_backfill_only_commits_deadline_without_count_change(client, main_user, monkeypatch):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=1)
    main_user.next_check_in_deadline = None
    main_user.missed_check_in_count = 0
    db.session.commit()

    commits = []
    monkeypatch.setattr(
        'src.tools.check_in_scheduler.db.session.commit',
        lambda: commits.append(True),
    )

    assert evaluate_actual_user_check_in() == 0
    assert commits == [True]
    assert main_user.next_check_in_deadline is not None


def test_tracker_stays_alert_when_missed_count_below_miss_count(client, main_user):
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=10)
    main_user.next_check_in_deadline = now - timedelta(hours=1)
    main_user.missed_check_in_count = 0
    db.session.commit()

    assert evaluate_actual_user_check_in() == 1
    db.session.refresh(main_user)
    assert compute_check_in_status(main_user) == 'ALERT'


def test_tracker_advances_status_to_dead(client, main_user):
    """End-to-end: expired deadline is ALERT until tracker reaches miss_count (default 2)."""
    now = datetime.now(timezone.utc)
    main_user.last_check_in = now - timedelta(days=15)
    main_user.next_check_in_deadline = now - timedelta(days=8)
    main_user.missed_check_in_count = 0
    db.session.commit()

    assert compute_check_in_status(main_user) == 'ALERT'

    assert evaluate_actual_user_check_in() >= 2

    db.session.refresh(main_user)
    assert compute_check_in_status(main_user) == 'DEAD'


def test_poll_interval_uses_default_when_missing():
    class _Settings:
        def get(self, key, default=None):
            return {}

    assert poll_interval_seconds(_Settings()) == DEFAULT_POLL_SECONDS


def test_poll_interval_reads_config():
    class _Settings:
        def get(self, key, default=None):
            return {'check_in_poll_seconds': 30}

    assert poll_interval_seconds(_Settings()) == 30


def test_poll_interval_rejects_non_positive():
    class _Settings:
        def get(self, key, default=None):
            return {'check_in_poll_seconds': 0}

    assert poll_interval_seconds(_Settings()) == DEFAULT_POLL_SECONDS


def test_poll_interval_rejects_invalid_string():
    class _Settings:
        def get(self, key, default=None):
            return {'check_in_poll_seconds': 'not-a-number'}

    assert poll_interval_seconds(_Settings()) == DEFAULT_POLL_SECONDS


def test_poll_interval_rejects_negative():
    class _Settings:
        def get(self, key, default=None):
            return {'check_in_poll_seconds': -5}

    assert poll_interval_seconds(_Settings()) == DEFAULT_POLL_SECONDS


def test_start_skipped_in_reloader_parent(monkeypatch, client):
    monkeypatch.setenv('WERKZEUG_RUN_MAIN', 'false')

    result = start_check_in_scheduler(app)

    assert result is None


def test_start_acquires_leader_lock_and_runs(client, tmp_path, monkeypatch):
    monkeypatch.delenv('WERKZEUG_RUN_MAIN', raising=False)
    lock_file = tmp_path / 'scheduler.lock'

    class _Settings:
        def get(self, key, default=None):
            if key == 'defences':
                return {
                    'check_in_poll_seconds': 3600,
                    'check_in_scheduler_lock_file': str(lock_file),
                }
            return default

    monkeypatch.setattr(
        'src.tools.check_in_scheduler.Settings',
        lambda: _Settings(),
    )
    monkeypatch.setattr(
        'src.tools.check_in_scheduler.scheduler_lock_path',
        lambda _settings: lock_file,
    )
    registrations = []
    monkeypatch.setattr(
        'src.tools.check_in_scheduler.atexit.register',
        lambda fn: registrations.append(fn),
    )

    scheduler = start_check_in_scheduler(app)
    assert scheduler is not None
    assert scheduler.running
    assert lock_file.is_file()
    assert len(registrations) == 1
    assert check_in_scheduler_module._atexit_registered is True

    start_check_in_scheduler(app)
    assert len(registrations) == 1

    stop_check_in_scheduler()
    assert not lock_file.is_file()


def test_start_skipped_when_leader_lock_held(client, tmp_path, monkeypatch):
    import os

    monkeypatch.delenv('WERKZEUG_RUN_MAIN', raising=False)
    lock_file = tmp_path / 'scheduler.lock'
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    # Simulate another live process holding the lock (without this module's _lock_fd set).
    lock_file.write_text(str(os.getpid()), encoding='utf-8')

    monkeypatch.setattr(
        'src.tools.check_in_scheduler.scheduler_lock_path',
        lambda _settings: lock_file,
    )

    assert start_check_in_scheduler(app) is None


def test_start_releases_lock_when_scheduler_start_fails(client, tmp_path, monkeypatch):
    monkeypatch.delenv('WERKZEUG_RUN_MAIN', raising=False)
    lock_file = tmp_path / 'scheduler.lock'

    monkeypatch.setattr(
        'src.tools.check_in_scheduler.scheduler_lock_path',
        lambda _settings: lock_file,
    )

    class _BrokenScheduler:
        def __init__(self, **kwargs):
            pass

        def add_job(self, *args, **kwargs):
            pass

        def start(self):
            raise RuntimeError('scheduler boom')

    monkeypatch.setattr(
        'src.tools.check_in_scheduler.BackgroundScheduler',
        _BrokenScheduler,
    )

    assert start_check_in_scheduler(app) is None
    assert not lock_file.is_file()
    assert check_in_scheduler_module._scheduler is None


def test_stop_when_not_running_is_safe():
    stop_check_in_scheduler()
    assert check_in_scheduler_module._scheduler is None


def test_stop_releases_orphan_leader_lock(tmp_path):
    lock_file = tmp_path / 'orphan.lock'
    from src.tools.scheduler_leader import try_acquire_scheduler_leadership

    assert try_acquire_scheduler_leadership(lock_file) is True
    stop_check_in_scheduler()
    assert not lock_file.is_file()


def test_poll_job_removes_session_even_when_evaluate_raises(client, monkeypatch):
    removes = []
    monkeypatch.setattr(
        'src.tools.check_in_scheduler.evaluate_actual_user_check_in',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError('tick failed')),
    )
    monkeypatch.setattr(
        'src.tools.check_in_scheduler.db.session.remove',
        lambda: removes.append(True),
    )

    check_in_scheduler_module._poll_job(app)

    assert removes  # at least once (Flask app context teardown may also remove)


def test_poll_job_runs_evaluate_inside_app_context(client, main_user):
    from flask import has_app_context

    seen = []

    def _record_evaluate():
        seen.append(has_app_context())
        return 0

    from src.tools import check_in_scheduler as sched

    original = sched.evaluate_actual_user_check_in
    sched.evaluate_actual_user_check_in = lambda: _record_evaluate()
    try:
        sched._poll_job(app)
    finally:
        sched.evaluate_actual_user_check_in = original

    assert seen == [True]
