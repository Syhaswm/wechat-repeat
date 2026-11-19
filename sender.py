def _failure_text(exc):
    message = str(exc).strip().splitlines()
    return message[0] if message else exc.__class__.__name__


def run_text_loop(
    count,
    interval,
    *,
    is_wechat,
    snapshot,
    restore,
    copy_input,
    put_payload,
    paste_enter,
    sleep,
    stop_requested,
    report,
):
    if not is_wechat():
        report("前台不是微信，未发送")
        return
    original = None
    try:
        original = snapshot()
        if not copy_input():
            report("输入框没有可复制的内容")
            return
        report(f"正在发送 0/{count}")
        sent = 0
        for index in range(count):
            if stop_requested():
                report(f"已停止 {sent}/{count}")
                return
            if not is_wechat():
                report("发送过程中微信失去焦点，已停止")
                return
            put_payload()
            paste_enter()
            sent += 1
            report(f"正在发送 {sent}/{count}")
            if index < count - 1:
                sleep(interval)
        report(f"已完成 {count}/{count}")
    except Exception as exc:
        report(f"发送失败：{_failure_text(exc)}")
    finally:
        if original is not None:
            restore(original)
