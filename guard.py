WECHAT_PROCESSES = {"wechat.exe", "weixin.exe", "wechatappex.exe"}
MAIN_PROCESSES = {"wechat.exe", "weixin.exe"}


def is_wechat_process(process_name):
    return str(process_name).lower() in WECHAT_PROCESSES


def is_main_wechat_window(process_name, title):
    name = str(process_name).lower()
    return name in MAIN_PROCESSES and "微信" in str(title)


def choose_main_window(chain, main_windows):
    if not chain or not is_wechat_process(chain[0][2]):
        return None
    for hwnd, _pid, process, title in chain:
        if is_main_wechat_window(process, title):
            return hwnd
    foreground_pid = chain[0][1]
    same_process = [item for item in main_windows if item[1] == foreground_pid]
    if len(same_process) == 1:
        return same_process[0][0]
    if len(main_windows) == 1:
        return main_windows[0][0]
    return None
