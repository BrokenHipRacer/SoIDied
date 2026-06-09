from datetime import datetime, timedelta, timezone

import pytest

from api import app, db
from src.models.user import User
from src.tools.check_in_scheduler import (
    DEFAULT_POLL_SECONDS,
    compute_missed_count,
    evaluate_actual_user_check_in,
    poll_interval_seconds,
)


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


def test_evaluate_returns_none_without_deadline(client, main_user):
    main_user.next_check_in_deadline = None
    db.session.commit()

    assert evaluate_actual_user_check_in() is None
    db.session.refresh(main_user)
    assert main_user.missed_check_in_count == 0


def test_evaluate_returns_none_without_actual_user(client):
    assert evaluate_actual_user_check_in() is None


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
