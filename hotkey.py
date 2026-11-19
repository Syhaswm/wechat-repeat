from pynput import keyboard

FUNCTION_KEYS = {f"f{number}": getattr(keyboard.Key, f"f{number}") for number in range(6, 13)}


class HotkeyListener:
    def __init__(self, get_hotkey, on_hotkey, on_escape):
        self.get_hotkey = get_hotkey
        self.on_hotkey = on_hotkey
        self.on_escape = on_escape
        self.listener = None

    def start(self):
        self.listener = keyboard.Listener(on_release=self._on_release)
        self.listener.start()

    def _on_release(self, key):
        wanted = FUNCTION_KEYS.get(self.get_hotkey())
        if wanted is not None and key == wanted:
            self.on_hotkey()
        elif key == keyboard.Key.esc:
            self.on_escape()
