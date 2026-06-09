from datetime import datetime, timedelta, timezone

from src.models.user import User
from src.tools.settings import Settings

_INTERVAL_TO_TIMEDELTA = {
    'm': lambda window: timedelta(minutes=window),
    'h': lambda window: timedelta(hours=window),
    'd': lambda window: timedelta(days=window),
    'W': lambda window: timedelta(weeks=window),
    'M': lambda window: timedelta(days=30 * window),
}


def _defences(settings: Settings | None = None) -> dict:
    settings = settings or Settings()
    return settings.get('defences', {})


def check_in_period(settings: Settings | None = None) -> timedelta:
    defences = _defences(settings)
    interval = defences.get('check_in_interval', 'd')
    window = defences.get('check_in_window', 7)
    builder = _INTERVAL_TO_TIMEDELTA.get(interval)
    if builder is None:
        builder = _INTERVAL_TO_TIMEDELTA['d']
    return builder(window)


def compute_next_check_in_deadline(
    from_time: datetime,
    settings: Settings | None = None,
) -> datetime:
    if from_time.tzinfo is None:
        from_time = from_time.replace(tzinfo=timezone.utc)
    return from_time + check_in_period(settings)


def format_next_check_in_message(deadline: datetime) -> str:
    return f'Next required Check-In by: {deadline.isoformat()}'


def record_successful_check_in(user: User, settings: Settings | None = None) -> datetime:
    """Actual user: stamp the check-in, freeze the next deadline, clear missed count.

    The deadline is persisted (frozen at check-in time) so it does not drift if config
    changes later. ``missed_check_in_count`` is reset to 0 here — this is the only
    legitimate reset path; the background tracker never lowers the count.
    """
    now = datetime.now(timezone.utc)
    user.last_check_in = now
    user.next_check_in_deadline = compute_next_check_in_deadline(now, settings)
    user.missed_check_in_count = 0
    return now


def record_compromised_check_in(user: User, settings: Settings | None = None) -> datetime:
    """Non-actual user: stamp timestamp and deadline only; missed count is not cleared."""
    now = datetime.now(timezone.utc)
    user.last_check_in = now
    user.next_check_in_deadline = compute_next_check_in_deadline(now, settings)
    return now


def effective_deadline(user: User, settings: Settings | None = None) -> datetime | None:
    """Frozen deadline if present, else derive one from ``last_check_in`` (or ``None``)."""
    if user.next_check_in_deadline is not None:
        deadline = user.next_check_in_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return deadline
    if user.last_check_in is None:
        return None
    return compute_next_check_in_deadline(user.last_check_in, settings)


def compute_check_in_status(user: User, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    defences = _defences(settings)
    miss_count = defences.get('miss_count', 2)

    if user.missed_check_in_count >= miss_count:
        return 'DEAD'

    deadline = effective_deadline(user, settings)
    if deadline is None:
        return 'ALERT'

    now = datetime.now(timezone.utc)
    if now > deadline:
        return 'ALERT'

    return 'OK'
