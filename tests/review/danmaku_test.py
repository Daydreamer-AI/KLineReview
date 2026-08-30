# -*- coding: utf-8 -*-
"""验证 confirm_ui 各控件能正常构造（headless，不进入事件循环）。"""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

import danmaku_widget as dw
from confirm_ui import ConfirmWindow, build_sample_items


def main():
    app = QApplication(sys.argv)

    # 1. 构造主确认窗口
    win = ConfirmWindow()
    win.resize(1400, 800)
    assert win.widget is not None
    assert win.history is not None
    assert win.checklist is not None
    assert win.log is not None
    print("[OK] ConfirmWindow 构造成功")

    # 2. 模拟一次完整业务流程（不进入 exec_，用 timer 驱动）
    items = build_sample_items()
    win.widget.set_data(items)
    assert len(win.widget._items) == len(items)
    print(f"[OK] set_data({len(items)} 条)")

    # 启动定时器模拟滚动若干帧
    win.widget._timer.start()
    QTimer.singleShot(300, lambda: None)
    QTimer.singleShot(350, win.widget._timer.stop)
    QTimer.singleShot(400, lambda: _after_tick(win, app))
    # 短事件循环
    QTimer.singleShot(500, app.quit)
    app.exec_()

    # 3. 验证各交互槽函数无异常
    win._change_stop_mode()
    win._change_hide_mode()
    win._change_fixed(0)
    win._change_fixed(-1)
    win._change_opacity(60)
    win._change_speed(2.0)
    win._apply_rect()
    win._full_rect()
    win._toggle_main()
    win._toggle_sub()
    win._toggle_pause()
    win._toggle_pause()
    print("[OK] 所有控制面板槽函数调用无异常")

    # 4. 模拟结果回调
    from danmaku_widget import DanmakuItem
    fake = DanmakuItem(text="TEST 测试")
    win._on_result(fake)
    win._on_manual()
    win._on_anim_done()
    assert len(win.history.get_history()) == 1
    print(f"[OK] 结果回调 + 历史记录 (count={win.history.list_widget.count()})")

    # 5. 生成报告不崩溃
    win.checklist._mark_all()
    print("[OK] 确认清单可标记/报告")

    print("\n==== confirm_ui 验证全部通过 ====")
    sys.exit(0)


def _after_tick(win, app):
    # 触发一次筛选（动画+加速+选结果）
    win.widget.on_main_clicked()
    print(f"[OK] on_main_clicked (speed_factor={win.widget._speed_factor})")


if __name__ == "__main__":
    main()
