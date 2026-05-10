# test/conftest.py

import pytest


@pytest.fixture
def base_good_config():
    return {
        "app": {
            "name": "SoIDied",
            "description": "Digital dead man's switch",
            "version": "0.0.1",
        },
        "settings": {
            "log_level": "INFO",
            "debug": False,
            "dark_mode": False,
        },
        "email": {
            "provider": "AmazonSES",
            "alert_email": "blank@blank.blank",
        },
        "actions": {
            "send_email": True,
            "delete_data": True,
            "social_media": False,
            "discord": False,
            "custom_script": False,
            "echo_count": 2,
        },
        "defences": {
            "crash_and_burn": False,
            "unlock": True,
            "canary": False,
            "miss_count": 1,
            "miss_alert": False,
            "check_in_interval": "d",
            "check_in_window": 7,
            "check_in_timeout_count": 5,
            "check_in_over_attempts": 3,
            "panic_threshold": 3,
            "panic_timeframe": 5,
            "panic_mode": "lockdown",
            "panic_to_sniffing": True,
            "panic_to_death": True,
            "panic_to_death_timeframe": 1200,
        },
    }


@pytest.fixture
def auth_payload():
    return {
        "id": "main",
        "token": "valid-token",
    }


@pytest.fixture
def invalid_auth_payload():
    return {
        "id": "main",
        "token": "invalid-token",
    }
