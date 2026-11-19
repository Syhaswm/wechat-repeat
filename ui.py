import threading
import time
from datetime import datetime, timedelta

from pynput.keyboard import Controller, Key

from config import normalize, save_config
from device import capture_panel, cursor_pos, foreground_wechat, move_click, wait_for_panel
from schedule import format_clock_status, format_delay_status, next_clock_time, run_wait
from sender import run_text_loop
from sticker import run_sticker_loop
import clipboard

MODE_LABELS = {"text": "文字", "sticker": "表情包"}
MODE_VALUES = {label: value for value, label in MODE_LABELS.items()}
SCHEDULE_LABELS = {"now": "马上", "clock": "指定钟点", "delay": "等待分钟"}
SCHEDULE_VALUES = {label: value for value, label in SCHEDULE_LABELS.items()}


def help_text(mode, schedule):
    if schedule == "now":
        if mode == "text":
            return "把光标放进微信输入框，内容准备好后按快捷键。再按一次停止。微信需要使用 Enter 发送。"
        return "先打开表情面板，鼠标停在要发送的表情包上，再按快捷键。再按一次停止。发送过程中不要滚动面板或切换分页。"
    if mode == "text":
        return "把光标留在微信输入框。点开始等待，到点只发一轮。等待期间请保持本程序和微信打开。微信需要使用 Enter 发送。"
    return "先打开表情面板，鼠标停在要发送的表情包上，再点开始等待。到点只发一轮。等待期间请保持本程序和微信打开，不要滚动面板或切换分页。"


class App:
    def __init__(self, root, config_path, config):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.config_path = config_path
        self.state = "idle"
        self.phase = "idle"
        self.stop_event = threading.Event()
        self.cancel_event = threading.Event()
        self.worker = None
        self.keyboard = Controller()
        self._loading = False
        self._payload = {}

        root.title("微信连发")
        root.resizable(False, False)

        self.mode = tk.StringVar(value=MODE_LABELS[config.mode])
        self.count = tk.StringVar(value=str(config.count))
        self.interval = tk.StringVar(value=f"{config.interval_seconds:g}")
        self.hotkey = tk.StringVar(value=config.hotkey.upper())
        self.schedule = tk.StringVar(value=SCHEDULE_LABELS[config.schedule])
        self.clock = tk.StringVar(value=config.clock_time)
        self.minutes = tk.StringVar(value=str(config.wait_minutes))
        self.status = tk.StringVar(value="空闲")
        self.help = tk.StringVar()

        frame = ttk.Frame(root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        self._row(frame, 0, "发送方式", ttk.Combobox(frame, textvariable=self.mode, values=list(MODE_VALUES), state="readonly", width=18))
        self._row(frame, 1, "次数", ttk.Spinbox(frame, textvariable=self.count, from_=1, to=500, width=18))
        self._row(frame, 2, "间隔（秒）", ttk.Spinbox(frame, textvariable=self.interval, from_=0.3, to=60, increment=0.1, width=18))
        self._row(frame, 3, "快捷键", ttk.Combobox(frame, textvariable=self.hotkey, values=[f"F{n}" for n in range(6, 13)], state="readonly", width=18))
        self._row(frame, 4, "启动方式", ttk.Combobox(frame, textvariable=self.schedule, values=list(SCHEDULE_VALUES), state="readonly", width=18))
        self.clock_input = ttk.Entry(frame, textvariable=self.clock, width=20)
        self._row(frame, 5, "钟点", self.clock_input)
        self.minutes_input = ttk.Spinbox(frame, textvariable=self.minutes, from_=1, to=1440, width=18)
        self._row(frame, 6, "等待分钟", self.minutes_input)

        self.inputs = [child for child in frame.winfo_children() if isinstance(child, (ttk.Combobox, ttk.Spinbox, ttk.Entry))]
        self.button = ttk.Button(frame, command=self._on_button)
        self.button.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Label(frame, textvariable=self.status).grid(row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(frame, textvariable=self.help, wraplength=360).grid(row=9, column=0, columnspan=2, sticky="w", pady=(6, 0))

        for variable in (self.mode, self.count, self.interval, self.hotkey, self.schedule, self.clock, self.minutes):
            variable.trace_add("write", lambda *_args: self._on_edit())
        self._refresh_form()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _row(self, frame, row, label, widget):
        self.ttk.Label(frame, text=label, width=12).grid(row=row, column=0, sticky="w", pady=3)
        widget.grid(row=row, column=1, sticky="ew", pady=3)

    def _on_edit(self):
        if self._loading or self.state != "idle":
            return
        self._refresh_form()
        save_config(self.config_path, self.current_config())

    def current_config(self):
        return normalize(
            {
                "mode": MODE_VALUES.get(self.mode.get(), "text"),
                "count": self.count.get(),
                "interval_seconds": self.interval.get(),
                "hotkey": self.hotkey.get(),
                "schedule": SCHEDULE_VALUES.get(self.schedule.get(), "now"),
                "clock_time": self.clock.get(),
                "wait_minutes": self.minutes.get(),
            }
        )

    def _refresh_form(self):
        config = self.current_config()
        schedule = config.schedule
        self.clock_input.state(["!disabled"] if schedule == "clock" and self.state == "idle" else ["disabled"])
        self.minutes_input.state(["!disabled"] if schedule == "delay" and self.state == "idle" else ["disabled"])
        if schedule == "now" and self.state == "idle":
            self.button.grid_remove()
        else:
            self.button.grid()
            if self.state == "sending":
                self.button.configure(text="停止")
            elif self.state == "waiting":
                self.button.configure(text="取消等待")
            else:
                self.button.configure(text="开始等待")
        self.help.set(help_text(config.mode, schedule))

    def _set_locked(self, locked):
        for child in self.inputs:
            if locked:
                child.state(["disabled"])
            elif isinstance(child, self.ttk.Combobox):
                child.state(["!disabled", "readonly"])
            else:
                child.state(["!disabled"])
        if not locked:
            self._refresh_form()

    def report(self, text):
        self.root.after(0, lambda: self.status.set(text))

    def hotkey_name(self):
        return self.current_config().hotkey

    def on_hotkey(self):
        self.root.after(0, self._handle_hotkey)

    def on_escape(self):
        self.root.after(0, self._handle_escape)

    def _handle_hotkey(self):
        if self.phase == "sending":
            self.stop_event.set()
        elif self.phase == "waiting":
            self.cancel_event.set()
        elif self.phase == "idle" and self.current_config().schedule == "now":
            self._begin_now()

    def _handle_escape(self):
        if self.phase == "sending":
            self.stop_event.set()
        elif self.phase == "waiting":
            self.cancel_event.set()

    def _on_button(self):
        if self.phase == "sending":
            self.stop_event.set()
        elif self.phase == "waiting":
            self.cancel_event.set()
        elif self.phase == "idle":
            self._begin_wait()

    def _begin_now(self):
        config = self.current_config()
        save_config(self.config_path, config)
        self._start_worker(self._send_now, config, None, None)

    def _begin_wait(self):
        config = self.current_config()
        save_config(self.config_path, config)
        prepared = None
        restore_point = None
        if config.mode == "sticker":
            current = foreground_wechat()
            if current is None:
                self.status.set("前台不是微信，未发送")
                return
            hwnd, _pid = current
            prepared = capture_panel(hwnd)
            if prepared is None:
                self.status.set("请把鼠标放在已打开的表情面板上")
                return
            restore_point = cursor_pos()
        now = datetime.now()
        if config.schedule == "clock":
            target = next_clock_time(now, config.clock_time)
            self.status.set(format_clock_status(now, target))
            show_delay = False
        else:
            target = now + timedelta(minutes=config.wait_minutes)
            self.status.set(format_delay_status(config.wait_minutes * 60))
            show_delay = True
        self._start_worker(self._wait_then_send, config, prepared, restore_point, target, show_delay)

    def _start_worker(self, target, *args):
        if self.worker and self.worker.is_alive():
            return
        self.stop_event.clear()
        self.cancel_event.clear()
        self.phase = "waiting" if target is self._wait_then_send else "sending"
        self.state = self.phase
        self._set_locked(True)
        self._refresh_form()
        self.worker = threading.Thread(target=target, args=args, daemon=True)
        self.worker.start()

    def _wait_then_send(self, config, prepared, restore_point, target, show_delay):
        def on_status(remaining):
            if show_delay:
                self.report(format_delay_status(remaining))

        result = run_wait(
            target,
            datetime.now,
            time.sleep,
            self.cancel_event.is_set,
            on_status,
            lambda: None,
        )
        if result == "cancelled":
            self.report("已取消等待")
            self._become_idle()
            return
        self.phase = "sending"
        self.root.after(0, lambda: self._mark_sending())
        self._send(config, prepared, restore_point)
        self._become_idle()

    def _send_now(self, config, prepared, restore_point):
        self._send(config, prepared, restore_point)
        self._become_idle()

    def _mark_sending(self):
        self.state = "sending"
        self._refresh_form()

    def _send(self, config, prepared, restore_point):
        if config.mode == "sticker":
            self._send_sticker(config, prepared, restore_point)
        else:
            self._send_text(config)

    def _send_text(self, config):
        self._payload = {}

        def copy_input():
            before = clipboard.sequence()
            self._chord("a")
            time.sleep(0.05)
            self._chord("c")
            deadline = time.time() + 0.3
            while time.time() < deadline:
                if clipboard.sequence() != before:
                    snap = clipboard.snapshot()
                    if not snap.items:
                        return False
                    self._payload["snap"] = snap
                    return True
                time.sleep(0.02)
            return False

        def put_payload():
            clipboard.restore(self._payload["snap"])

        run_text_loop(
            config.count,
            config.interval_seconds,
            is_wechat=lambda: foreground_wechat() is not None,
            snapshot=clipboard.snapshot,
            restore=clipboard.restore,
            copy_input=copy_input,
            put_payload=put_payload,
            paste_enter=self._paste_enter,
            sleep=self._sleep,
            stop_requested=self.stop_event.is_set,
            report=self.report,
        )

    def _send_sticker(self, config, prepared, restore_point):
        session = {"main": None, "pid": None}

        def is_wechat():
            current = foreground_wechat()
            if current is None:
                return False
            session["main"], session["pid"] = current
            return True

        def capture():
            if session["main"] is None:
                return None
            return capture_panel(session["main"])

        def open_panel():
            self._press_alt_e()

        def wait_panel(width, height, origin):
            if session["pid"] is None or session["main"] is None:
                return None
            return wait_for_panel(session["pid"], session["main"], width, height, origin)

        run_sticker_loop(
            config.count,
            config.interval_seconds,
            is_wechat=is_wechat,
            capture_panel=capture,
            open_panel=open_panel,
            wait_panel=wait_panel,
            move_click=move_click,
            mouse_pos=cursor_pos,
            restore_mouse=lambda point: move_cursor(point),
            sleep=self._sleep,
            stop_requested=self.stop_event.is_set,
            report=self.report,
            prepared=prepared,
            restore_point=restore_point,
        )

    def _sleep(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            if self.stop_event.is_set():
                return
            time.sleep(min(0.05, end - time.time()))

    def _chord(self, character):
        self.keyboard.press(Key.ctrl)
        try:
            self.keyboard.press(character)
            self.keyboard.release(character)
        finally:
            self.keyboard.release(Key.ctrl)

    def _press_alt_e(self):
        self.keyboard.press(Key.alt)
        try:
            self.keyboard.press("e")
            self.keyboard.release("e")
        finally:
            self.keyboard.release(Key.alt)
        time.sleep(0.05)

    def _paste_enter(self):
        self._chord("v")
        time.sleep(0.05)
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)

    def _become_idle(self):
        def update():
            self.phase = "idle"
            self.state = "idle"
            self._set_locked(False)
            self._refresh_form()

        self.root.after(0, update)

    def close(self):
        self.stop_event.set()
        self.cancel_event.set()
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=2)
        save_config(self.config_path, self.current_config())
        self.root.destroy()


def move_cursor(point):
    import ctypes

    ctypes.windll.user32.SetCursorPos(int(point[0]), int(point[1]))
