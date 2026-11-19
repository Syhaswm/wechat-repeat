from config import normalize


def test_count_is_clamped_to_1_and_500():
    assert normalize({"count": 0}).count == 1
    assert normalize({"count": 500}).count == 500
    assert normalize({"count": 501}).count == 500


def test_interval_is_clamped_to_0_3_and_60():
    assert normalize({"interval_seconds": 0.1}).interval_seconds == 0.3
    assert normalize({"interval_seconds": 2}).interval_seconds == 2.0
    assert normalize({"interval_seconds": 61}).interval_seconds == 60.0


def test_unknown_hotkey_becomes_f8_and_case_is_ignored():
    assert normalize({"hotkey": "f1"}).hotkey == "f8"
    assert normalize({"hotkey": "F8"}).hotkey == "f8"


def test_unknown_mode_and_schedule_fall_back():
    assert normalize({"mode": "image"}).mode == "text"
    assert normalize({"schedule": "daily"}).schedule == "now"


def test_clock_and_wait_minutes_are_clamped():
    assert normalize({"clock_time": "25:99"}).clock_time == "09:00"
    assert normalize({"clock_time": "21:30"}).clock_time == "21:30"
    assert normalize({"wait_minutes": 0}).wait_minutes == 1
    assert normalize({"wait_minutes": 1441}).wait_minutes == 1440
