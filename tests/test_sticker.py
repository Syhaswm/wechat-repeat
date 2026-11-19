from sticker import Panel, run_sticker_loop, screen_point


def _panel(origin=(10, 20)):
    return Panel(width=200, height=180, offset=(15, 25), origin=origin)


def _run(*, capture=None, wechat=None, stop_after=None, found=None, prepared=None):
    clicks = []
    opens = []
    sleeps = []
    restores = []
    reports = []
    sent = {"n": 0}

    def is_wechat():
        if wechat is None:
            return True
        return wechat(sent["n"])

    def open_panel():
        opens.append(1)

    def wait_panel(_width, _height, _origin):
        if found is None:
            return _panel(origin=(30, 40))
        return found()

    def move_click(point):
        clicks.append(point)
        sent["n"] += 1

    run_sticker_loop(
        3,
        0.3,
        is_wechat=is_wechat,
        capture_panel=capture or (lambda: _panel()),
        open_panel=open_panel,
        wait_panel=wait_panel,
        move_click=move_click,
        mouse_pos=lambda: (1, 2),
        restore_mouse=restores.append,
        sleep=sleeps.append,
        stop_requested=lambda: stop_after is not None and sent["n"] >= stop_after,
        report=reports.append,
        prepared=prepared,
    )
    return clicks, opens, sleeps, restores, reports


def test_screen_point_follows_panel_origin():
    assert screen_point((100, 200), (5, 6)) == (105, 206)
    assert screen_point((300, 400), (5, 6)) == (305, 406)


def test_cursor_on_main_window_does_not_click():
    clicks, opens, _sleeps, _restores, reports = _run(capture=lambda: None)
    assert clicks == []
    assert opens == []
    assert reports == ["请把鼠标放在已打开的表情面板上"]


def test_three_stickers_press_alt_e_twice():
    clicks, opens, sleeps, restores, reports = _run()
    assert len(clicks) == 3
    assert clicks[0] == (25, 45)
    assert opens == [1, 1]
    assert sleeps == [0.3, 0.3]
    assert restores == [(1, 2)]
    assert reports[-1] == "已完成 3/3"


def test_stop_or_problems_before_second_click_do_not_click_again():
    for kwargs in (
        {"stop_after": 1},
        {"wechat": lambda sent: sent < 1},
        {"found": lambda: None},
    ):
        clicks, _emoji, _sleeps, _restores, _reports = _run(**kwargs)
        assert len(clicks) == 1


def test_prepared_panel_missing_at_fire_time_sends_nothing():
    clicks, _emoji, _sleeps, _restores, reports = _run(prepared=_panel(), found=lambda: None)
    assert clicks == []
    assert reports == ["表情面板没有回到原位，未发送"]
