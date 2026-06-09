from src.tools.scheduler_leader import (
    release_scheduler_leadership,
    try_acquire_scheduler_leadership,
)


def test_scheduler_leader_acquire_release_reacquire(tmp_path):
    lock_file = tmp_path / 'leader.lock'

    assert try_acquire_scheduler_leadership(lock_file) is True
    assert lock_file.is_file()

    release_scheduler_leadership()
    assert not lock_file.is_file()

    assert try_acquire_scheduler_leadership(lock_file) is True
    release_scheduler_leadership()


def test_scheduler_leader_same_process_is_reentrant(tmp_path):
    lock_file = tmp_path / 'leader.lock'

    assert try_acquire_scheduler_leadership(lock_file) is True
    assert try_acquire_scheduler_leadership(lock_file) is True

    release_scheduler_leadership()
