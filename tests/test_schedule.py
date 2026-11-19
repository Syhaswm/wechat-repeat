from datetime import datetime

from schedule import format_delay_status, next_clock_time, run_wait


def test_clock_later_today_stays_today():
    now = datetime(2026, 11, 19, 21, 0, 0)
    assert next_clock_time(now, "21:30") == datetime(2026, 11, 19, 21, 30, 0)


def test_clock_at_exact_minute_is_now():
    now = datetime(2026, 11, 19, 21, 30, 0)
    assert next_clock_time(now, "21:30") == now


def test_clock_after_the_minute_moves_to_tomorrow():
    now = datetime(2026, 11, 19, 21, 30, 1)
    assert next_clock_time(now, "21:30") == datetime(2026, 11, 20, 21, 30, 0)


def test_delay_status_uses_minutes_and_seconds():
    assert format_delay_status(12 * 60 + 5) == "等待中，还剩 12 分 05 秒"


def test_cancel_does_not_start_sending():
    started = []

    result = run_wait(
        target=datetime(2026, 11, 19, 21, 30, 0),
        now_fn=lambda: datetime(2026, 11, 19, 21, 0, 0),
        sleep_fn=lambda _seconds: None,
        is_cancelled=lambda: True,
        on_status=lambda _text: None,
        start_send=lambda: started.append(1),
    )

    assert result == "cancelled"
    assert started == []


def test_reaching_the_target_starts_sending_once():
    started = []
    now = datetime(2026, 11, 19, 21, 30, 0)

    result = run_wait(
        target=now,
        now_fn=lambda: now,
        sleep_fn=lambda _seconds: None,
        is_cancelled=lambda: False,
        on_status=lambda _text: None,
        start_send=lambda: started.append(1),
    )

    assert result == "fired"
    assert started == [1]
