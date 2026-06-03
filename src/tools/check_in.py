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


def record_successful_check_in(user: User) -> datetime:
    """Actual user: persist last check-in and clear missed check-in count."""
    now = datetime.now(timezone.utc)
    user.last_check_in = now
    user.missed_check_in_count = 0
    return now


def record_compromised_check_in(user: User) -> datetime:
    """Non-actual user: register timestamp only; missed count is not cleared."""
    now = datetime.now(timezone.utc)
    user.last_check_in = now
    return now


def compute_check_in_status(user: User, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    defences = _defences(settings)
    miss_count = defences.get('miss_count', 1)

    if user.missed_check_in_count >= miss_count:
        return 'DEAD'

    if user.last_check_in is None:
        return 'ALERT'

    now = datetime.now(timezone.utc)
    deadline = compute_next_check_in_deadline(user.last_check_in, settings)
    if now > deadline:
        return 'ALERT'

    return 'OK'
