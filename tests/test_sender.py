from sender import run_text_loop


def _run(count=3, *, copied=True, wechat=None, stop_after=None):
    pastes = []
    sleeps = []
    restores = []
    reports = []
    sent_state = {"n": 0}

    def is_wechat():
        if wechat is None:
            return True
        return wechat(sent_state["n"])

    def stop_requested():
        return stop_after is not None and sent_state["n"] >= stop_after

    def paste_enter():
        pastes.append(1)
        sent_state["n"] += 1

    run_text_loop(
        count,
        0.3,
        is_wechat=is_wechat,
        snapshot=lambda: "original",
        restore=restores.append,
        copy_input=lambda: copied,
        put_payload=lambda: None,
        paste_enter=paste_enter,
        sleep=sleeps.append,
        stop_requested=stop_requested,
        report=reports.append,
    )
    return pastes, sleeps, restores, reports


def test_empty_copy_sends_nothing_and_restores_clipboard():
    pastes, _sleeps, restores, reports = _run(copied=False)
    assert pastes == []
    assert restores == ["original"]
    assert reports == ["输入框没有可复制的内容"]


def test_three_sends_sleep_only_between_messages():
    pastes, sleeps, restores, reports = _run()
    assert pastes == [1, 1, 1]
    assert sleeps == [0.3, 0.3]
    assert restores == ["original"]
    assert reports[-1] == "已完成 3/3"


def test_stop_before_second_send_sends_once():
    pastes, _sleeps, restores, reports = _run(stop_after=1)
    assert pastes == [1]
    assert restores == ["original"]
    assert "已停止 1/3" in reports


def test_losing_wechat_before_second_send_sends_once():
    pastes, _sleeps, restores, reports = _run(wechat=lambda sent: sent < 1)
    assert pastes == [1]
    assert restores == ["original"]
    assert "发送过程中微信失去焦点，已停止" in reports


def test_not_wechat_at_start_does_not_touch_clipboard():
    pastes, _sleeps, restores, reports = _run(wechat=lambda _sent: False)
    assert pastes == []
    assert restores == []
    assert reports == ["前台不是微信，未发送"]
