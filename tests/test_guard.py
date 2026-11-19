from guard import choose_main_window, is_main_wechat_window, is_wechat_process


def test_wechat_process_counts_without_title():
    assert is_wechat_process("Weixin.exe")
    assert is_wechat_process("WeChat.exe")
    assert is_wechat_process("WeChatAppEx.exe")
    assert not is_wechat_process("notepad.exe")
    assert not is_wechat_process("微信连发.exe")


def test_main_window_still_needs_wechat_title():
    assert is_main_wechat_window("Weixin.exe", "微信")
    assert not is_main_wechat_window("Weixin.exe", "")
    assert not is_main_wechat_window("notepad.exe", "微信")


def test_emoji_popup_uses_owning_main_window():
    chain = [
        (10, 100, "Weixin.exe", ""),
        (20, 100, "Weixin.exe", "微信"),
    ]
    assert choose_main_window(chain, [(20, 100, "Weixin.exe", "微信")]) == 20


def test_wechat_helper_process_uses_the_only_main_window():
    chain = [(10, 200, "WeChatAppEx.exe", "")]
    mains = [(20, 100, "Weixin.exe", "微信")]
    assert choose_main_window(chain, mains) == 20


def test_other_apps_are_not_wechat():
    chain = [(10, 300, "chrome.exe", "微信")]
    mains = [(20, 100, "Weixin.exe", "微信")]
    assert choose_main_window(chain, mains) is None
