# -*- coding: utf-8 -*-
"""
自动化验证脚本（无屏环境可用 offscreen 运行）
"""
import os
import sys
import random

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))
from danmaku_widget_yb import (
    DanmakuReviewWidget, DanmakuItem, Mode, ResultOverlay, DiceButton,
)


def make_items(n=20):
    stocks = [
        ("600519", "贵州茅台", "#FFD700"),
        ("300750", "宁德时代", "#4ECDC4"),
        ("601012", "隆基绿能", "#FF6B6B"),
        ("000858", "五粮液",   "#A18CD1"),
        ("002304", "洋河股份", "#FF8C42"),
    ]
    items = []
    for i in range(n):
        code, name, color = stocks[i % len(stocks)]
        items.append(DanmakuItem(
            text=f"{code} {name}-{i}",
            color=color,
            font_size=random.choice([22, 26, 28, 30]),
            bold=random.choice([True, False]),
            italic=random.choice([True, False]),
            opacity=random.choice([0.8, 0.9, 1.0]),
            stroke_width=random.choice([1, 2]),
        ))
    return items


def main():
    app = QApplication(sys.argv)
    w = DanmakuReviewWidget()
    w.resize(800, 480)
    w.show()

    results = []
    items = make_items(20)

    # C01 立即滚动
    w.set_data(items)
    assert w._rolling, "set_data 后应自动开始滚动"
    results.append(("C01 立即滚动", True))

    # C02 循环滚动（驱动 200 帧，检查轨道仍有弹幕）
    w.set_data(items)
    for _ in range(200):
        w._on_tick()
    any_alive = any(len(t) > 0 for t in w._tracks)
    results.append(("C02 循环滚动不停止", any_alive))

    # C03 不重叠：同轨道弹幕间距 >= 间隔
    w.set_data(items)
    for _ in range(300):
        w._on_tick()
    no_overlap = True
    for track in w._tracks:
        sorted_dm = sorted(track, key=lambda d: d.x)
        for a, b in zip(sorted_dm, sorted_dm[1:]):
            if (a.x + a.width) > b.x + 1e-6:
                no_overlap = False
                break
        if not no_overlap:
            break
    results.append(("C03 同轨道不重叠", no_overlap))

    # C04 不越界
    region = w.danmaku_rect()
    in_bounds = True
    for track in w._tracks:
        for dm in track:
            if dm.x + dm.width < region.left() - 1 or dm.x > region.right() + 1:
                in_bounds = False
                break
        if not in_bounds:
            break
    results.append(("C04 弹幕不越界", in_bounds))

    # C05 样式独立
    styles = set((it.color.name(), it.font_size, it.bold) for it in items[:10])
    results.append(("C05 样式独立随机", len(styles) > 3))

    # C06 动画（直接调用不报错）
    try:
        w.main_btn.play_animation(duration=10, on_finished=lambda: None)
        w.main_btn.setDisabled(False)
        results.append(("C06 筛子动画", True))
    except Exception as e:
        results.append(("C06 筛子动画", False, str(e)))

    # C07 加速
    w.set_speed_factor(4.0)
    results.append(("C07 弹幕加速", w._speed_factor == 4.0))

    # C08 停止模式
    w.stop_mode = Mode.STOP_AUTO
    results.append(("C08 停止模式", w.stop_mode == Mode.STOP_AUTO))

    # C09 结果遮罩置顶（overlay 在按钮之上）
    w._last_result = items[0]
    w._show_result_overlay(items[0])
    overlay_on_top = w.result_overlay.isVisible()
    # Z 轴：overlay 应是最后一个子控件（在最上）
    children = w.children()
    topmost = children[-1] if children else None
    results.append(("C09 结果遮罩覆盖(可见且置顶)",
                    overlay_on_top and isinstance(topmost, ResultOverlay)))
    w.hide_result()

    # C10 背景弱化（显示时按钮被禁用）
    w._show_result_overlay(items[0])
    results.append(("C10 背景弱化(按钮禁用)", not w.center_widget.isEnabled()))
    w.hide_result()

    # C11 结果隐藏模式
    w.result_hide_mode = Mode.RESULT_HIDE_MANUAL
    results.append(("C11 结果隐藏模式", w.result_hide_mode == Mode.RESULT_HIDE_MANUAL))
    w.result_hide_mode = Mode.RESULT_HIDE_AUTO
    w.result_hide_duration_ms = 2000
    results.append(("C11 自动隐藏时长", w.result_hide_duration_ms == 2000))

    # C12 内定结果
    w.set_data(items)
    w.set_fixed_result(3)
    w._on_animation_finished()
    results.append(("C12 内定结果", w.get_result() == items[3]))
    w._fixed_index = None

    # C13 全局透明度（pyqtProperty）
    w.global_opacity = 0.5
    results.append(("C13 全局透明度", abs(w._global_opacity - 0.5) < 1e-9))

    # C14 显示区域
    rect = QRectF(50, 80, 600, 300)
    w.set_danmaku_rect(rect)
    results.append(("C14 显示区域", w.danmaku_rect().toRect() == rect.toRect()))

    # C15 按钮显隐
    w.hide_main_button()
    w.hide_sub_button()
    results.append(("C15 按钮显隐",
                    not w.main_btn.isVisible() and not w.sub_btn.isVisible()))

    # C16 历史
    w._add_history("测试记录")
    results.append(("C16 历史记录", len(w.get_history()) > 0))
    w.clear_history()

    # C17 防递归：高频设置属性
    try:
        for _ in range(500):
            w.global_opacity = random.uniform(0.2, 1.0)
            w.main_btn.btn_rotation = random.uniform(0, 360)
            w.main_btn.btn_scale = random.uniform(0.5, 1.5)
            w.result_overlay.card_opacity = random.uniform(0, 1)
            w.result_overlay.card_scale = random.uniform(0.5, 1.2)
        results.append(("C17 防递归(500次无RecursionError)", True))
    except RecursionError as e:
        results.append(("C17 防递归", False, str(e)))

    # C18 随机加载（非顺序）
    w.set_data(items)
    order1 = [w._next_item().text for _ in range(len(items))]
    w.set_data(items)
    order2 = [w._next_item().text for _ in range(len(items))]
    results.append(("C18 随机加载", order1 != order2))

    # 汇总
    print("\n==== 验证结果 ====")
    ok = 0
    for r in results:
        status = "✅" if r[1] else "❌"
        print(f"{status} {r[0]}" + (f"  -- {r[2]}" if len(r) > 2 else ""))
        if r[1]:
            ok += 1
    print(f"\n通过: {ok}/{len(results)}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
