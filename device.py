import ctypes
import time
from ctypes import wintypes

from guard import choose_main_window, is_main_wechat_window
from sticker import Panel

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetCursorPos.argtypes = [ctypes.c_void_p]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.mouse_event.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_size_t,
]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.ClientToScreen.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumChildWindows.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p]
user32.EnumChildWindows.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND


def process_name(pid):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return buffer.value.rsplit("\\", 1)[-1]
    finally:
        kernel32.CloseHandle(handle)


def window_pid(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


GW_OWNER = 4


def _window_record(hwnd):
    pid = window_pid(hwnd)
    return hwnd, pid, process_name(pid), window_title(hwnd)


def _owner_chain(hwnd):
    chain = []
    seen = set()
    current = hwnd
    while current and current not in seen:
        seen.add(current)
        chain.append(_window_record(current))
        owner = user32.GetWindow(current, GW_OWNER)
        parent = user32.GetParent(current)
        nxt = owner or parent
        if not nxt or nxt == current:
            break
        current = nxt
    return chain


def _main_windows():
    found = []

    def collect(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            record = _window_record(hwnd)
            if is_main_wechat_window(record[2], record[3]):
                found.append(record)
        return True

    user32.EnumWindows(WNDENUMPROC(collect), 0)
    return found


def foreground_wechat():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    main = choose_main_window(_owner_chain(hwnd), _main_windows())
    if main is None:
        return None
    return main, window_pid(main)


def cursor_pos():
    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return int(point.x), int(point.y)


def move_click(point):
    user32.SetCursorPos(int(point[0]), int(point[1]))
    time.sleep(0.02)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def _client_box(hwnd):
    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    origin = POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    return (int(origin.x), int(origin.y)), width, height


def capture_panel(main_hwnd):
    x, y = cursor_pos()
    hwnd = user32.WindowFromPoint(POINT(x, y))
    if not hwnd or window_pid(hwnd) != window_pid(main_hwnd):
        return None
    panel = hwnd
    while True:
        parent = user32.GetParent(panel)
        if not parent or parent == main_hwnd:
            break
        panel = parent
    if panel == main_hwnd:
        return None
    box = _client_box(panel)
    if box is None:
        return None
    origin, width, height = box
    offset = (x - origin[0], y - origin[1])
    if width <= 0 or height <= 0:
        return None
    if not (0 <= offset[0] < width and 0 <= offset[1] < height):
        return None
    return Panel(width, height, offset, origin)


def _visible_windows(pid, main_hwnd):
    found = []

    def collect(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and window_pid(hwnd) == pid and hwnd != main_hwnd:
            found.append(hwnd)
        return True

    callback = WNDENUMPROC(collect)
    user32.EnumWindows(callback, 0)
    user32.EnumChildWindows(main_hwnd, callback, 0)
    unique = []
    seen = set()
    for hwnd in found:
        if hwnd not in seen:
            seen.add(hwnd)
            unique.append(hwnd)
    return unique


def wait_for_panel(pid, main_hwnd, width, height, last_origin, timeout=1.0):
    deadline = time.time() + timeout
    while True:
        matches = []
        for hwnd in _visible_windows(pid, main_hwnd):
            box = _client_box(hwnd)
            if box is None:
                continue
            origin, found_width, found_height = box
            if abs(found_width - width) <= 4 and abs(found_height - height) <= 4:
                matches.append(Panel(found_width, found_height, (0, 0), origin))
        if matches:
            return min(
                matches,
                key=lambda panel: (panel.origin[0] - last_origin[0]) ** 2
                + (panel.origin[1] - last_origin[1]) ** 2,
            )
        if time.time() >= deadline:
            return None
        time.sleep(0.05)
