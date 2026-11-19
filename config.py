import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

HOTKEYS = tuple(f"f{number}" for number in range(6, 13))
CLOCK_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@dataclass
class Config:
    mode: str = "text"
    count: int = 5
    interval_seconds: float = 2.0
    hotkey: str = "f8"
    schedule: str = "now"
    clock_time: str = "09:00"
    wait_minutes: int = 1


def clamp_count(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 5
    return min(500, max(1, number))


def clamp_interval(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 2.0
    if number < 0.3:
        number = 0.3
    elif number > 60:
        number = 60.0
    number = math.floor(number * 10 + 0.5) / 10
    if number < 0.3:
        number = 0.3
    if number > 60:
        number = 60.0
    return float(number)


def clamp_hotkey(value):
    text = str(value).strip().lower()
    return text if text in HOTKEYS else "f8"


def clamp_mode(value):
    return value if value in ("text", "sticker") else "text"


def clamp_schedule(value):
    return value if value in ("now", "clock", "delay") else "now"


def clamp_clock(value):
    text = str(value).strip()
    return text if CLOCK_RE.fullmatch(text) else "09:00"


def clamp_wait_minutes(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 1
    return min(1440, max(1, number))


def normalize(data=None):
    data = data or {}
    return Config(
        mode=clamp_mode(data.get("mode", "text")),
        count=clamp_count(data.get("count", 5)),
        interval_seconds=clamp_interval(data.get("interval_seconds", 2.0)),
        hotkey=clamp_hotkey(data.get("hotkey", "f8")),
        schedule=clamp_schedule(data.get("schedule", "now")),
        clock_time=clamp_clock(data.get("clock_time", "09:00")),
        wait_minutes=clamp_wait_minutes(data.get("wait_minutes", 1)),
    )


def load_config(path):
    file = Path(path)
    if not file.exists():
        config = normalize({})
        save_config(file, config)
        return config
    raw = json.loads(file.read_text(encoding="utf-8"))
    config = normalize(raw)
    save_config(file, config)
    return config


def save_config(path, config):
    file = Path(path)
    payload = asdict(config)
    file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
