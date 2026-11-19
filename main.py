import ctypes
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import win32api
import win32event
import winerror

from config import load_config
from hotkey import HotkeyListener
from ui import App

_MUTEX = None


def enable_dpi():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def acquire_single_instance():
    global _MUTEX
    _MUTEX = win32event.CreateMutex(None, False, "Local\\WeChatRepeatSend")
    return win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main():
    enable_dpi()
    if not acquire_single_instance():
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("微信连发", "微信连发已经在运行")
        root.destroy()
        return
    config_path = app_dir() / "config.json"
    config = load_config(config_path)
    root = tk.Tk()
    app = App(root, config_path, config)
    listener = HotkeyListener(app.hotkey_name, app.on_hotkey, app.on_escape)
    try:
        listener.start()
    except Exception:
        app.report("快捷键注册失败")
    root.mainloop()


if __name__ == "__main__":
    main()
