# -*- coding: utf-8 -*-
"""
弹幕抽奖控件 (DanmakuReviewWidget)
====================================
基于 Model/View 架构的弹幕滚动 + 抽奖控件。

架构原则：
- View 内不做任何数据获取，数据由外部通过 set_data() 传入
- 内部只负责渲染与动画
- 所有 pyqtProperty 使用私有属性存值，setter 内绝不写 self.xxx = value（防递归）

依赖：PyQt5
运行：python danmaku_widget.py   （需要 GUI 环境；无屏可用 QT_QPA_PLATFORM=offscreen）
"""
import sys
import random
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QHBoxLayout, QFrame, QApplication,
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup, QPointF, QRect, QRectF,
    QObject, pyqtProperty, pyqtSignal, QElapsedTimer, QSize, QEasingCurve
)
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen, QBrush, QPainterPath, QIcon,
)

from ..qfluentwidgets.components.widgets.button import TransparentPushButton, TransparentToolButton


# ----------------------------------------------------------------------
# 数据模型（Model）
# ----------------------------------------------------------------------
class DanmakuItem(QObject):
    """
    单条弹幕数据模型。
    所有样式属性均可外部指定，未指定取默认值。
    最终透明度 = global_opacity(控件级) * opacity(单条)
    """

    def __init__(self, text="", color=None, font_family=None, font_size=None,
                 bold=False, italic=False, opacity=1.0, stroke_color=None,
                 stroke_width=0, parent=None):
        super().__init__(parent)
        self.text = text
        self.color = QColor(color) if color else QColor("#FFFFFF")
        self.font_family = font_family or "Microsoft YaHei"
        self.font_size = font_size if font_size else 18
        self.bold = bold
        self.italic = italic
        self.opacity = opacity
        self.stroke_color = QColor(stroke_color) if stroke_color else None
        self.stroke_width = stroke_width

    def build_font(self):
        f = QFont(self.font_family, self.font_size)
        f.setBold(self.bold)
        f.setItalic(self.italic)
        return f

    def text_width(self):
        fm = QFontMetrics(self.build_font())
        return fm.horizontalAdvance(self.text)

    def effective_opacity(self, global_opacity):
        return self.opacity * global_opacity


# ----------------------------------------------------------------------
# 单条弹幕运行时状态（轨道内使用）
# ----------------------------------------------------------------------
class _LiveDanmaku:
    """轨道内正在滚动的一条弹幕，含当前 x 坐标"""

    def __init__(self, item, x=0.0):
        self.item = item
        self.x = x
        self.width = item.text_width()


# ----------------------------------------------------------------------
# 中心主按钮（带动画）
# ----------------------------------------------------------------------
class DiceButton(TransparentToolButton):
    """图标按钮，点击时播放骰子摇动动画（旋转 + 缩放 + 位置抖动）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rotation = 0.0
        self._scale = 1.0
        self._offset_x = 0.0  # X 轴偏移
        self._offset_y = 0.0  # Y 轴偏移
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(400, 400)
        # icon 缩小，给缩放和抖动留出余量
        self.setIconSize(QSize(200, 200))

    def _get_rotation(self):
        return self._rotation

    def _set_rotation(self, v):
        self._rotation = v
        self.update()

    def _get_scale(self):
        return self._scale

    def _set_scale(self, v):
        self._scale = v
        self.update()

    # 偏移量的 getter/setter
    def _get_offset_x(self):
        return self._offset_x

    def _set_offset_x(self, v):
        self._offset_x = v
        self.update()

    def _get_offset_y(self):
        return self._offset_y

    def _set_offset_y(self, v):
        self._offset_y = v
        self.update()

    btn_rotation = pyqtProperty(float, _get_rotation, _set_rotation)
    btn_scale = pyqtProperty(float, _get_scale, _set_scale)
    # 注册为 Qt 属性，供动画引擎驱动
    btn_offset_x = pyqtProperty(float, _get_offset_x, _set_offset_x)
    btn_offset_y = pyqtProperty(float, _get_offset_y, _set_offset_y)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        # p.setBrush(QBrush(QColor("BDBDBD")))
        # p.drawRect(self.rect())
        
        p.save()
        p.translate(self.width() / 2, self.height() / 2)
        p.translate(self._offset_x, self._offset_y)
        p.rotate(self._rotation)
        p.scale(self._scale, self._scale)
        
        icon = self.icon()
        size = self.iconSize()
        if not icon.isNull():
            rect = QRect(-size.width() // 2, -size.height() // 2, 
                         size.width(), size.height())
            icon.paint(p, rect)
        else:
            p.setPen(QPen(QColor("#FFD700")))
            p.setFont(QFont("Arial", 32, QFont.Bold))
            p.drawText(QRect(-30, -30, 60, 60), Qt.AlignCenter, "\uD83C\uDFB2")
        
        p.restore()

    def play_animation(self, duration=1200, on_finished=None):
        self.anim_group = QParallelAnimationGroup(self)

        # ===== 旋转：4圈快速旋转，逐渐减速 =====
        rot = QPropertyAnimation(self, b"btn_rotation")
        rot.setDuration(duration)
        rot.setStartValue(0)
        rot.setEndValue(1440)  # 4圈 = 1440°
        rot.setEasingCurve(QEasingCurve.OutQuart)  # 快起慢停
        self.anim_group.addAnimation(rot)

        # ===== 缩放：剧烈弹跳 =====
        scl = QPropertyAnimation(self, b"btn_scale")
        scl.setDuration(duration)
        scl.setKeyValueAt(0.0, 1.0)
        scl.setKeyValueAt(0.12, 1.55)   # 猛放大
        scl.setKeyValueAt(0.28, 0.55)   # 猛缩小（"砸向桌面"）
        scl.setKeyValueAt(0.42, 1.40)   # 弹起
        scl.setKeyValueAt(0.56, 0.65)   # 再落下
        scl.setKeyValueAt(0.70, 1.20)   # 小幅弹起
        scl.setKeyValueAt(0.85, 0.90)   # 微缩
        scl.setKeyValueAt(1.0, 1.0)     # 归位
        scl.setEasingCurve(QEasingCurve.OutBounce)  # 落地弹跳感
        self.anim_group.addAnimation(scl)

        # ===== X 轴随机抖动 =====
        off_x = QPropertyAnimation(self, b"btn_offset_x")
        off_x.setDuration(duration)
        off_x.setKeyValueAt(0.00, 0)
        off_x.setKeyValueAt(0.10, random.uniform(-18, 18))
        off_x.setKeyValueAt(0.20, random.uniform(-15, 15))
        off_x.setKeyValueAt(0.30, random.uniform(-12, 12))
        off_x.setKeyValueAt(0.42, random.uniform(-10, 10))
        off_x.setKeyValueAt(0.55, random.uniform(-6, 6))
        off_x.setKeyValueAt(0.68, random.uniform(-4, 4))
        off_x.setKeyValueAt(0.80, random.uniform(-2, 2))
        off_x.setKeyValueAt(0.90, random.uniform(-1, 1))
        off_x.setKeyValueAt(1.0, 0)
        off_x.setEasingCurve(QEasingCurve.OutQuad)  # 抖动逐渐衰减
        self.anim_group.addAnimation(off_x)

        # ===== Y 轴随机抖动 =====
        off_y = QPropertyAnimation(self, b"btn_offset_y")
        off_y.setDuration(duration)
        off_y.setKeyValueAt(0.00, 0)
        off_y.setKeyValueAt(0.10, random.uniform(-18, 18))
        off_y.setKeyValueAt(0.20, random.uniform(-15, 15))
        off_y.setKeyValueAt(0.30, random.uniform(-12, 12))
        off_y.setKeyValueAt(0.42, random.uniform(-10, 10))
        off_y.setKeyValueAt(0.55, random.uniform(-6, 6))
        off_y.setKeyValueAt(0.68, random.uniform(-4, 4))
        off_y.setKeyValueAt(0.80, random.uniform(-2, 2))
        off_y.setKeyValueAt(0.90, random.uniform(-1, 1))
        off_y.setKeyValueAt(1.0, 0)
        off_y.setEasingCurve(QEasingCurve.OutQuad)  # 抖动逐渐衰减
        self.anim_group.addAnimation(off_y)

        if on_finished:
            self.anim_group.finished.connect(on_finished)
        
        self.anim_group.start()


# ----------------------------------------------------------------------
# 主控件
# ----------------------------------------------------------------------
class DanmakuReviewWidget(QWidget):
    """
    弹幕抽奖控件。
    - 数据通过 set_data() 外部传入
    - 每条弹幕独立样式
    - 多轨道循环随机滚动，永不停止，保证不重叠、不越界
    - 中心主按钮（筛子动画）+ 弱化子按钮
    - 结果遮罩高亮 + 自动/手动隐藏
    - 结果历史列表
    """

    result_selected = pyqtSignal(object)
    main_button_clicked = pyqtSignal()
    manual_select_clicked = pyqtSignal()
    animation_finished = pyqtSignal()

    STOP_AUTO = "auto"
    STOP_MANUAL = "manual"
    RESULT_HIDE_AUTO = "auto"
    RESULT_HIDE_MANUAL = "manual"

    def __init__(self, parent=None):
        super().__init__(parent)

        self._items = []
        self._shuffled_indices = []
        self._fixed_result_index = None
        self._result = None

        self._track_count = 6
        self._base_speed = 2.0
        self._speed_factor = 1.0
        self._tracks = []
        self._track_y = []
        self._danmaku_rect = QRectF()
        self._top_margin = 60
        self._bottom_margin = 60
        self._min_gap_ratio = 0.6

        self._global_opacity = 1.0

        self._running = True
        self._paused = False
        self._stop_mode = self.STOP_AUTO
        self._result_hide_mode = self.RESULT_HIDE_AUTO
        self._result_hide_ms = 4000
        self._is_rolling = False
        self._history = []

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)

        self._result_hide_timer = QTimer(self)
        self._result_hide_timer.setSingleShot(True)
        self._result_hide_timer.timeout.connect(self.hide_result)

        self._result_visible = False
        self._result_text = ""
        self._result_opacity = 0.0

        self._build_ui()
        self._rebuild_tracks()

    # ==================================================================
    # UI 构建
    # ==================================================================
    def _build_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)

        self._center_container = QWidget(self)
        layout = QVBoxLayout(self._center_container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        self.main_btn = DiceButton(self._center_container)
        layout.addWidget(self.main_btn, alignment=Qt.AlignCenter)
        self.main_btn.clicked.connect(self.on_main_clicked)

        self.sub_btn = TransparentPushButton(self.tr("Manual choice"), self._center_container)
        self.sub_btn.setCursor(Qt.PointingHandCursor)
        self.sub_btn.setFlat(True)
        # self.sub_btn.setStyleSheet(
        #     "QPushButton{color:#AAAAAA;font-size:14px;background:transparent;"
        #     "border:none;text-decoration:underline;padding:4px 8px;}"
        #     "QPushButton:hover{color:#FFFFFF;}"
        # )
        # layout.addWidget(self.sub_btn, alignment=Qt.AlignCenter)
        self.sub_btn.hide()
        self.sub_btn.clicked.connect(self.manual_select_clicked.emit)

        self._center_container.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_center_container"):
            self._center_container.move(
                (self.width() - self._center_container.width()) // 2,
                (self.height() - self._center_container.height()) // 2,
            )
        self._rebuild_tracks()

    # ==================================================================
    # 轨道 / 显示区域
    # ==================================================================
    def _rebuild_tracks(self):
        rect = self._effective_danmaku_rect()
        if rect.height() <= 0 or self._track_count <= 0:
            return
        self._track_y = []
        step = rect.height() / self._track_count
        for i in range(self._track_count):
            self._track_y.append(rect.top() + step * (i + 0.5))
        while len(self._tracks) < self._track_count:
            self._tracks.append([])
        while len(self._tracks) > self._track_count:
            self._tracks.pop()

    def _effective_danmaku_rect(self):
        if self._danmaku_rect is not None and not self._danmaku_rect.isEmpty():
            return self._danmaku_rect
        r = self.rect()
        return QRectF(r.left(), r.top() + self._top_margin,
                      r.width(), r.height() - self._top_margin - self._bottom_margin)

    def set_danmaku_rect(self, rect):
        """rect: QRectF 或 None（None 表示充满控件，即默认行为）"""
        self._danmaku_rect = None if rect is None else QRectF(rect)
        self._rebuild_tracks()
        self.update()

    def set_margins(self, top, bottom):
        self._top_margin = top
        self._bottom_margin = bottom
        self._rebuild_tracks()
        self.update()

    def set_track_count(self, n):
        self._track_count = max(1, int(n))
        self._rebuild_tracks()

    # ==================================================================
    # 透明度（pyqtProperty，私有属性防递归）
    # ==================================================================
    def _get_global_opacity(self):
        return self._global_opacity

    def _set_global_opacity(self, v):
        self._global_opacity = float(max(0.0, min(1.0, v)))
        self.update()

    global_opacity = pyqtProperty(float, _get_global_opacity, _set_global_opacity)

    # ==================================================================
    # 数据接口（Model 传入）
    # ==================================================================
    def set_data(self, items):
        self._items = [
            (it if isinstance(it, DanmakuItem) else DanmakuItem(text=str(it)))
            for it in items
        ]
        self._reshuffle()
        for track in self._tracks:
            track.clear()
        self._seed_tracks()
        self._running = True
        if not self._timer.isActive():
            self._timer.start()

    def _reshuffle(self):
        self._shuffled_indices = list(range(len(self._items)))
        random.shuffle(self._shuffled_indices)

    def _seed_tracks(self):
        if not self._items:
            return
        rect = self._effective_danmaku_rect()
        for track in self._tracks:
            x = rect.left() - random.uniform(0, rect.width() * 0.3)
            for _ in range(3):
                idx = self._next_index()
                item = self._items[idx]
                track.append(_LiveDanmaku(item, x))
                x += item.text_width() + rect.width() * self._min_gap_ratio

    def _next_index(self):
        if not self._shuffled_indices:
            self._reshuffle()
        return self._shuffled_indices.pop(0)

    # ==================================================================
    # 内定结果
    # ==================================================================
    def set_fixed_result(self, index):
        self._fixed_result_index = index

    # ==================================================================
    # 弹幕启停 / 速度
    # ==================================================================
    def start(self):
        self._running = True
        self._paused = False
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._running = False
        self._timer.stop()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def set_speed_factor(self, factor):
        self._speed_factor = max(0.0, float(factor))

    def set_base_speed(self, speed):
        self._base_speed = max(0.1, float(speed))

    # ==================================================================
    # 按钮控制
    # ==================================================================
    def set_main_icon(self, path_or_icon):
        if isinstance(path_or_icon, str):
            self.main_btn.setIcon(QIcon(path_or_icon))
        else:
            self.main_btn.setIcon(path_or_icon)

    def set_sub_text(self, text):
        self.sub_btn.setText(text)

    def set_buttons_visible(self, visible):
        self._center_container.setVisible(visible)

    def set_buttons_enabled(self, enabled):
        self.main_btn.setEnabled(enabled)

    def show_main_button(self):
        self.main_btn.show()

    def hide_main_button(self):
        self.main_btn.hide()

    def show_sub_button(self):
        self.sub_btn.show()

    def hide_sub_button(self):
        self.sub_btn.hide()

    # ==================================================================
    # 停止模式 / 结果隐藏模式
    # ==================================================================
    def set_stop_mode(self, mode):
        self._stop_mode = mode

    def set_result_hide_mode(self, mode, duration_ms=None):
        self._result_hide_mode = mode
        if duration_ms is not None:
            self._result_hide_ms = int(duration_ms)

    # ==================================================================
    # 主按钮点击 -> 动画 + 加速 -> 选结果
    # ==================================================================
    def on_main_clicked(self):
        if self._is_rolling or not self._items:
            return
        self._is_rolling = True
        self.main_button_clicked.emit()
        self.set_speed_factor(4.0)
        self.main_btn.play_animation(duration=3000, on_finished=self._on_anim_finished)

    def _on_anim_finished(self):
        self.animation_finished.emit()
        if self._stop_mode == self.STOP_MANUAL:
            return
        self._finish_rolling()

    def stop_rolling(self):
        if self._is_rolling:
            self._finish_rolling()

    def _finish_rolling(self):
        self._is_rolling = False
        self.set_speed_factor(1.0)
        if self._fixed_result_index is not None and 0 <= self._fixed_result_index < len(self._items):
            chosen = self._items[self._fixed_result_index]
            self._fixed_result_index = None
        else:
            chosen = random.choice(self._items)
        self._result = chosen
        self._show_result(chosen)
        # self.result_selected.emit(chosen)

    # ==================================================================
    # 结果展示（遮罩高亮）
    # ==================================================================
    def _show_result(self, item):
        self.set_buttons_visible(False)
        self._result_text = item.text
        self._result = item
        self._result_visible = True
        self._result_opacity = 0.0
        self._add_history(item.text)
        self.update()
        if self._result_hide_mode == self.RESULT_HIDE_AUTO:
            self._result_hide_timer.start(self._result_hide_ms)

    def hide_result(self):
        self.result_selected.emit(self._result)
        self.set_buttons_visible(True)
        self._result_visible = False
        self._result_text = ""
        self._result_hide_timer.stop()
        self.update()

    def result(self):
        return self._result

    # ==================================================================
    # 历史记录
    # ==================================================================
    def _add_history(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self._history.append({"text": text, "time": ts})

    def get_history(self):
        return list(self._history)

    def clear_history(self):
        self._history.clear()

    # ==================================================================
    # 滚动核心（定时器 tick）
    # ==================================================================
    def _on_tick(self):
        if not self._running or self._paused or not self._items:
            return

        rect = self._effective_danmaku_rect()
        step = self._base_speed * self._speed_factor

        for track in self._tracks:
            for live in track:
                live.x -= step
            track[:] = [lv for lv in track if (lv.x + lv.width) > rect.left() - 10]
            if not track:
                self._spawn_on_track(track, rect.right() + rect.width() * self._min_gap_ratio)
            else:
                rightmost = max(lv.x + lv.width for lv in track)
                needed = rect.right() + rect.width() * self._min_gap_ratio
                if rightmost < needed:
                    self._spawn_on_track(track, rightmost + rect.width() * self._min_gap_ratio)

        self.update()

    def _spawn_on_track(self, track, x):
        idx = self._next_index()
        item = self._items[idx]
        track.append(_LiveDanmaku(item, x))

    # ==================================================================
    # 绘制
    # ==================================================================
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), Qt.transparent)

        danmaku_rect = self._effective_danmaku_rect()
        p.setClipRect(danmaku_rect.toRect())

        for i, track in enumerate(self._tracks):
            if i >= len(self._track_y):
                break
            base_y = self._track_y[i]
            for live in track:
                self._draw_danmaku(p, live, base_y, danmaku_rect)

        p.setClipping(False)

        if self._result_visible and self._result:
            self._draw_result_overlay(p)

    def _draw_danmaku(self, p, live, base_y, rect):
        item = live.item
        final_opacity = item.effective_opacity(self._global_opacity)
        if final_opacity <= 0.01:
            return

        font = item.build_font()
        p.setFont(font)
        metrics = QFontMetrics(font)
        text = item.text

        y = base_y + metrics.ascent() / 2.0 - metrics.descent() / 2.0

        x_left = live.x
        x_right = live.x + live.width
        if x_right < rect.left() or x_left > rect.right():
            return

        p.setPen(Qt.NoPen)
        p.setBrush(Qt.NoBrush)

        if item.stroke_color and item.stroke_width > 0:
            stroke = QColor(item.stroke_color)
            stroke.setAlphaF(final_opacity)   # QPen 无 setOpacity，用带 alpha 的颜色
            pen = QPen(stroke, item.stroke_width)
            p.setPen(pen)
            p.drawText(QPointF(x_left, y), text)

        p.setPen(QPen(item.color))
        p.setOpacity(final_opacity)
        p.drawText(QPointF(x_left, y), text)
        p.setOpacity(1.0)

    def _draw_result_overlay(self, p):
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))
        item = self._result
        cx = self.width() / 2
        cy = self.height() / 2

        font = item.build_font()
        font.setPointSize(max(font.pointSize(), 48))
        p.setFont(font)
        metrics = QFontMetrics(font)
        text = item.text
        tw = metrics.horizontalAdvance(text)
        th = metrics.height()
        rect = QRectF(cx - tw / 2 - 30, cy - th / 2 - 20, tw + 60, th + 40)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(40, 44, 60)))
        p.setOpacity(0.95)
        p.drawRoundedRect(rect, 16, 16)
        p.setOpacity(1.0)

        p.setPen(QPen(item.color if item.color.alpha() > 0 else QColor("#FFD700")))
        p.drawText(rect, Qt.AlignCenter, text)

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# ----------------------------------------------------------------------
# 历史记录独立展示控件（配套）
# ----------------------------------------------------------------------
class ResultHistoryWidget(QWidget):
    """抽奖结果历史列表控件"""

    item_clicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.label = QLabel("抽奖历史")
        self.label.setStyleSheet("color:#FFFFFF;font-size:14px;font-weight:bold;")
        layout.addWidget(self.label)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget{background:#1E2029;color:#FFFFFF;border:1px solid #333;border-radius:6px;}"
            "QListWidget::item{padding:6px;border-bottom:1px solid #2A2D36;}"
            "QListWidget::item:selected{background:#3A3F4B;}"
        )
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def _on_item_clicked(self, item):
        self.item_clicked.emit(item.data(Qt.UserRole))

    def add_record(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        lw = QListWidgetItem(f"[{ts}] {text}")
        lw.setData(Qt.UserRole, {"text": text, "time": ts})
        self.list_widget.insertItem(0, lw)

    def get_history(self):
        result = []
        for i in range(self.list_widget.count()):
            result.append(self.list_widget.item(i).data(Qt.UserRole))
        return result

    def clear(self):
        self.list_widget.clear()


# ----------------------------------------------------------------------
# 组合主窗口（弹幕 + 历史，演示用）
# ----------------------------------------------------------------------
class DanmakuReviewWindow(QWidget):
    """完整窗口：弹幕抽奖区 + 底部历史记录区"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("弹幕抽奖控件 - 完整演示")
        self.resize(900, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.danmaku = DanmakuReviewWidget()
        layout.addWidget(self.danmaku, stretch=1)

        self.history = ResultHistoryWidget()
        self.history.setMaximumHeight(160)
        layout.addWidget(self.history)

        # 信号联动：抽奖结果同步到历史控件
        self.danmaku.result_selected.connect(
            lambda item: self.history.add_record(item.text)
        )

    def set_data(self, items):
        self.danmaku.set_data(items)

    def set_main_icon(self, path):
        self.danmaku.set_main_icon(path)


# ----------------------------------------------------------------------
# 演示 / 验证（直接运行）
# ----------------------------------------------------------------------
def _make_sample_items():
    # 使用字典格式，可以精确指定每一项的样式属性
    samples = [
        {"text": "600519 贵州茅台", "color": "#FFD700", "font_size": 32, "bold": True, "opacity": 1.0},
        {"text": "000858 五粮液", "color": "#FF6B6B", "font_size": 28, "bold": True},
        {"text": "300750 宁德时代", "color": "#4ECDC4", "font_size": 24},
        {"text": "601318 中国平安", "color": "#A29BFE"},
        {"text": "000333 美的集团", "color": "#FFEAA7", "opacity": 0.8},
        {"text": "002594 比亚迪", "color": "#55EFC4", "font_size": 20, "bold": False},
        {"text": "600036 招商银行", "color": "#74B9FF"},
        {"text": "601988 中国银行", "color": "#FAB1A0", "font_size": 28, "opacity": 0.9},
        {"text": "300059 东方财富", "color": "#DFE6E9", "bold": True},
        {"text": "600030 中信证券", "color": "#FDCB6E", "font_size": 24, "opacity": 0.85},
    ]
    return _make_sample_items_by_list(samples)

def _make_sample_items_by_list(list_samples):
    """
    支持字典格式的弹幕数据解析。
    如果字典中缺少某个属性，则使用随机默认值兜底。
    """
    items = []
    for sample in list_samples:
        # 兼容旧版元组格式 (text, color)
        if isinstance(sample, (tuple, list)):
            text, color = sample
            font_size = random.choice([20, 24, 28, 32])
            bold = random.choice([True, False])
            opacity = random.uniform(0.7, 1.0)
        # 处理新版字典格式
        elif isinstance(sample, dict):
            text = sample.get("text", "Unknown")
            color = sample.get("color", "#FFFFFF")
            
            # 如果字典中没有指定，则随机生成
            font_size = sample.get("font_size", random.choice([20, 24, 28, 32]))
            bold = sample.get("bold", random.choice([True, False]))
            opacity = sample.get("opacity", random.uniform(0.7, 1.0))
        else:
            continue  # 跳过不支持的数据类型
            
        items.append(DanmakuItem(
            text=text,
            color=color,
            font_size=font_size,
            bold=bold,
            opacity=opacity,
            stroke_color="#000000",
            stroke_width=1,
        ))
    return items


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DanmakuReviewWindow()
    w.set_data(_make_sample_items())
    w.set_main_icon("dice_icon.svg")
    w.danmaku.set_sub_text("手动选择")
    w.danmaku.set_stop_mode(DanmakuReviewWidget.STOP_AUTO)
    w.danmaku.set_result_hide_mode(DanmakuReviewWidget.RESULT_HIDE_AUTO, duration_ms=4000)
    w.danmaku.global_opacity = 0.9
    w.danmaku.set_track_count(6)
    w.show()

    # 演示：3 秒后"内定"一次结果（下一次点击直接命中）
    QTimer.singleShot(3000, lambda: w.danmaku.set_fixed_result(0))

    sys.exit(app.exec_())
