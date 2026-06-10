import os

from pathlib import Path

import pytest

import src.tools.scheduler_leader as leader_module
from src.tools.scheduler_leader import (
    DEFAULT_LOCK_FILE,
    release_scheduler_leadership,
    scheduler_lock_path,
    try_acquire_scheduler_leadership,
)


@pytest.fixture(autouse=True)
def _reset_leader_state():
    release_scheduler_leadership()
    leader_module._lock_fd = None
    leader_module._lock_path = None
    yield
    release_scheduler_leadership()
    leader_module._lock_fd = None
    leader_module._lock_path = None


def test_scheduler_leader_acquire_release_reacquire(tmp_path):
    lock_file = tmp_path / 'leader.lock'

    assert try_acquire_scheduler_leadership(lock_file) is True
    assert lock_file.is_file()
    assert lock_file.read_text(encoding='utf-8') == str(os.getpid())

    release_scheduler_leadership()
    assert not lock_file.is_file()

    assert try_acquire_scheduler_leadership(lock_file) is True
    release_scheduler_leadership()


def test_scheduler_leader_same_process_is_reentrant(tmp_path):
    lock_file = tmp_path / 'leader.lock'

    assert try_acquire_scheduler_leadership(lock_file) is True
    assert try_acquire_scheduler_leadership(lock_file) is True

    release_scheduler_leadership()


def test_release_without_acquire_is_noop(tmp_path):
    lock_file = tmp_path / 'leader.lock'

    release_scheduler_leadership()
    assert not lock_file.exists()


def test_stale_lock_removed_when_pid_is_dead(tmp_path):
    lock_file = tmp_path / 'leader.lock'
    lock_file.write_text('999999', encoding='utf-8')

    assert try_acquire_scheduler_leadership(lock_file) is True
    assert lock_file.read_text(encoding='utf-8') == str(os.getpid())

    release_scheduler_leadership()


def test_stale_lock_removed_when_pid_is_invalid(tmp_path):
    lock_file = tmp_path / 'leader.lock'
    lock_file.write_text('not-a-pid', encoding='utf-8')

    assert try_acquire_scheduler_leadership(lock_file) is True

    release_scheduler_leadership()


def test_stale_lock_removed_when_pid_is_zero(tmp_path):
    lock_file = tmp_path / 'leader.lock'
    lock_file.write_text('0', encoding='utf-8')

    assert try_acquire_scheduler_leadership(lock_file) is True

    release_scheduler_leadership()


def test_acquire_blocked_when_live_pid_in_lock_file(tmp_path):
    lock_file = tmp_path / 'leader.lock'
    lock_file.write_text(str(os.getpid()), encoding='utf-8')

    assert try_acquire_scheduler_leadership(lock_file) is False
    assert leader_module._lock_fd is None


def test_acquire_creates_parent_directories(tmp_path):
    lock_file = tmp_path / 'nested' / 'dir' / 'leader.lock'

    assert try_acquire_scheduler_leadership(lock_file) is True
    assert lock_file.is_file()

    release_scheduler_leadership()


def test_scheduler_lock_path_uses_default():
    class _Settings:
        def get(self, key, default=None):
            return {}

    assert scheduler_lock_path(_Settings()) == Path(DEFAULT_LOCK_FILE)


def test_scheduler_lock_path_reads_config():
    class _Settings:
        def get(self, key, default=None):
            return {'check_in_scheduler_lock_file': 'tmp/custom.lock'}

    assert scheduler_lock_path(_Settings()) == Path('tmp/custom.lock')


def test_unix_flock_contention_returns_false(monkeypatch, tmp_path):
    lock_file = tmp_path / 'leader.lock'
    monkeypatch.setattr(leader_module, '_uses_windows_lock', lambda: False)
    monkeypatch.setattr(
        leader_module,
        '_try_unix_exclusive_lock',
        lambda _fd: (_ for _ in ()).throw(BlockingIOError),
    )

    assert try_acquire_scheduler_leadership(lock_file) is False
    assert leader_module._lock_fd is None


def test_unix_release_unlocks_and_removes_lock_file(monkeypatch, tmp_path):
    lock_file = tmp_path / 'leader.lock'
    monkeypatch.setattr(leader_module, '_uses_windows_lock', lambda: False)
    unlocked = []

    def _record_unlock(fd):
        unlocked.append(fd)

    monkeypatch.setattr(leader_module, '_try_unix_exclusive_lock', lambda _fd: None)
    monkeypatch.setattr(leader_module, '_try_unix_unlock', _record_unlock)

    assert try_acquire_scheduler_leadership(lock_file) is True
    held_fd = leader_module._lock_fd
    assert held_fd is not None

    release_scheduler_leadership()

    assert unlocked == [held_fd]
    assert not lock_file.is_file()
    assert leader_module._lock_fd is None
