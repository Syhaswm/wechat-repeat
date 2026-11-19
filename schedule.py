import math
from datetime import datetime, timedelta


def next_clock_time(now, clock_time):
    hour, minute = (int(part) for part in clock_time.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now > target:
        target += timedelta(days=1)
    return target


def format_delay_status(remaining_seconds):
    total = max(0, math.ceil(float(remaining_seconds) - 1e-9))
    minutes, seconds = divmod(total, 60)
    return f"等待中，还剩 {minutes} 分 {seconds:02d} 秒"


def format_clock_status(now, target):
    day = "今天" if target.date() == now.date() else "明天"
    return f"等待中，{day} {target:%H:%M} 开始"


def run_wait(target, now_fn, sleep_fn, is_cancelled, on_status, start_send):
    while True:
        if is_cancelled():
            return "cancelled"
        now = now_fn()
        if now >= target:
            start_send()
            return "fired"
        on_status((target - now).total_seconds())
        sleep_fn(0.2)
