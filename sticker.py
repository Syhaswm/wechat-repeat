from dataclasses import dataclass


@dataclass
class Panel:
    width: int
    height: int
    offset: tuple
    origin: tuple


def screen_point(origin, offset):
    return (origin[0] + offset[0], origin[1] + offset[1])


def _inside(point, panel):
    x, y = point
    left, top = panel.origin
    return left <= x < left + panel.width and top <= y < top + panel.height


def _failure_text(exc):
    message = str(exc).strip().splitlines()
    return message[0] if message else exc.__class__.__name__


def run_sticker_loop(
    count,
    interval,
    *,
    is_wechat,
    capture_panel,
    open_panel,
    wait_panel,
    move_click,
    mouse_pos,
    restore_mouse,
    sleep,
    stop_requested,
    report,
    prepared=None,
    restore_point=None,
):
    home = mouse_pos() if restore_point is None else restore_point
    try:
        if not is_wechat():
            report("前台不是微信，未发送")
            return
        if prepared is not None:
            located = wait_panel(prepared.width, prepared.height, prepared.origin)
            if located is None:
                report("表情面板没有回到原位，未发送")
                return
            panel = Panel(prepared.width, prepared.height, prepared.offset, located.origin)
        else:
            panel = capture_panel()
            if panel is None:
                report("请把鼠标放在已打开的表情面板上")
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
            current = panel
            if index > 0:
                open_panel()
                current = wait_panel(panel.width, panel.height, panel.origin)
                if current is None:
                    report("表情面板没有回到原位，已停止")
                    return
            point = screen_point(current.origin, panel.offset)
            if not _inside(point, current):
                report("表情面板没有回到原位，已停止")
                return
            move_click(point)
            sent += 1
            panel = Panel(panel.width, panel.height, panel.offset, current.origin)
            report(f"正在发送 {sent}/{count}")
            if index < count - 1:
                sleep(interval)
        report(f"已完成 {count}/{count}")
    except Exception as exc:
        report(f"发送失败：{_failure_text(exc)}")
    finally:
        restore_mouse(home)
