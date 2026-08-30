# -*- coding: utf-8 -*-
"""
弹幕抽奖控件 - 人工确认界面
=================================
通过可视化面板，让人工逐项确认控件行为是否符合预期。

功能：
1. 左侧：控制面板（数据加载、启动/停止、加速、内定结果、透明度、显示区域、模式切换等）
2. 中间：DanmakuReviewWidget 主控件实时展示
3. 右侧：验证清单（人工勾选每一项是否符合预期）
4. 底部：结果历史 + 日志

用法：
    python confirm_ui.py
"""
import sys
import random
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QGroupBox, QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QListWidget, QListWidgetItem, QTextEdit, QFileDialog,
    QSlider, QLineEdit, QMessageBox, QFormLayout, QProgressBar,
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRectF
from PyQt5.QtGui import QFont, QColor

# 主控件（与 danmaku_widget.py 同目录）
from danmaku_widget_yb import (
    DanmakuReviewWidget,
    DanmakuItem,
    ResultHistoryWidget,
)

# 模式常量（定义在 DanmakuReviewWidget 类内，通过类属性引用，避免导入耦合）
W = DanmakuReviewWidget
STOP_AUTO = W.STOP_AUTO
STOP_MANUAL = W.STOP_MANUAL
RESULT_HIDE_AUTO = W.RESULT_HIDE_AUTO
RESULT_HIDE_MANUAL = W.RESULT_HIDE_MANUAL
del W


# ==========================================================
# 内置示例数据（个股代码 + 名称）
# ==========================================================
SAMPLE_STOCKS = [
    ("600519", "贵州茅台", "#FFD700"),
    ("300750", "宁德时代", "#4ECDC4"),
    ("000858", "五粮液",   "#FF6B6B"),
    ("601318", "中国平安", "#A78BFA"),
    ("600036", "招商银行", "#60A5FA"),
    ("002594", "比亚迪",   "#34D399"),
    ("601899", "紫金矿业", "#F472B6"),
    ("300059", "东方财富", "#FBBF24"),
    ("000333", "美的集团", "#22D3EE"),
    ("600900", "长江电力", "#F87171"),
    ("002415", "海康威视", "#C084FC"),
    ("601012", "隆基绿能", "#4ADE80"),
    ("600030", "中信证券", "#FB923C"),
    ("300760", "迈瑞医疗", "#38BDF8"),
    ("000651", "格力电器", "#E879F9"),
    ("601888", "中国中免", "#FACC15"),
    ("002304", "洋河股份", "#2DD4BF"),
    ("600276", "恒瑞医药", "#A3E635"),
    ("300015", "爱尔眼科", "#7C3AED"),
    ("000002", "万科A",    "#0EA5E9"),
]


def build_sample_items():
    """构造示例弹幕数据：每条样式随机（颜色/字号/粗体/透明度）"""
    items = []
    fonts = ["Microsoft YaHei", "SimHei", "Arial", "SimSun"]
    for code, name, color in SAMPLE_STOCKS:
        text = f"{code} {name}"
        has_stroke = random.choice([True, False])
        items.append(DanmakuItem(
            text=text,
            color=QColor(color),
            font_size=random.choice([20, 24, 28, 32]),
            bold=random.choice([True, False]),
            italic=random.choice([True, False]),
            opacity=random.uniform(0.7, 1.0),
            font_family=random.choice(fonts),
            stroke_color=QColor("#000000") if has_stroke else None,
            stroke_width=2 if has_stroke else 0,
        ))
    return items


# ==========================================================
# 人工确认清单项
# ==========================================================
CHECKLIST = [
    ("C01", "数据加载后立即自动滚动（无需点击）", "核心"),
    ("C02", "弹幕循环滚动，永不停止", "核心"),
    ("C03", "同轨道弹幕不重叠，内容完整可见", "核心"),
    ("C04", "弹幕不超出控件边界（在显示区域内）", "核心"),
    ("C05", "每条弹幕样式随机（颜色/字号/字体各异）", "核心"),
    ("C06", "点击主按钮触发筛子动画（旋转+缩放）", "核心"),
    ("C07", "动画期间弹幕加速滚动", "核心"),
    ("C08", "动画结束后随机出结果并展示", "核心"),
    ("C09", "结果展示时背景弱化（遮罩高亮）", "核心"),
    ("C10", "结果默认自动隐藏（可配时长）", "核心"),
    ("C11", "停止模式：自动 / 手动 可切换", "增强"),
    ("C12", "内定结果（set_fixed_result）生效", "增强"),
    ("C13", "全局透明度调节生效", "增强"),
    ("C14", "显示区域（set_danmaku_rect）生效", "增强"),
    ("C15", "结果历史列表记录每次结果", "增强"),
    ("C16", "子按钮点击发出信号", "增强"),
    ("C17", "按钮显隐接口正常", "增强"),
    ("C18", "pyqtProperty 无递归报错", "核心"),
]


class ChecklistWidget(QGroupBox):
    """右侧验证清单：人工逐项勾选"""
    def __init__(self, parent=None):
        super().__init__("人工确认清单", parent)
        self.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 13px; }"
        )
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        layout.addWidget(self.list_widget)

        for cid, desc, level in CHECKLIST:
            item = QListWidgetItem()
            mark = "[!!]" if level == "核心" else "[  ]"
            item.setText(f"{mark} {cid}  {desc}")
            item.setData(Qt.UserRole, cid)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

        btn_row = QHBoxLayout()
        self.btn_pass = QPushButton("✅ 全部通过")
        self.btn_pass.clicked.connect(self._mark_all)
        self.btn_report = QPushButton("📋 生成报告")
        self.btn_report.clicked.connect(self._gen_report)
        btn_row.addWidget(self.btn_pass)
        btn_row.addWidget(self.btn_report)
        layout.addLayout(btn_row)

    def _mark_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)

    def _gen_report(self):
        total = self.list_widget.count()
        passed = sum(
            1 for i in range(total)
            if self.list_widget.item(i).checkState() == Qt.Checked
        )
        lines = ["# 人工确认报告", f"时间: {datetime.now()}", ""]
        for i in range(total):
            it = self.list_widget.item(i)
            status = "✅" if it.checkState() == Qt.Checked else "❌"
            lines.append(f"{status} {it.text()}")
        lines.append("")
        lines.append(f"**通过: {passed}/{total}**")

        box = QMessageBox(self)
        box.setWindowTitle("确认报告")
        box.setText("\n".join(lines[:6]) + f"\n\n... 共 {total} 项，通过 {passed}/{total}")
        box.setDetailedText("\n".join(lines))
        box.exec_()

    def summary(self):
        total = self.list_widget.count()
        passed = sum(
            1 for i in range(total)
            if self.list_widget.item(i).checkState() == Qt.Checked
        )
        return passed, total


class LogWidget(QTextEdit):
    """底部日志"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(120)
        self.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.append(f"[{ts}] {msg}")


class ConfirmWindow(QWidget):
    """主确认界面"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("弹幕抽奖控件 - 人工确认界面")
        self.resize(1400, 800)

        # ---- 主控件 ----
        self.widget = DanmakuReviewWidget()
        self.widget.result_selected.connect(self._on_result)
        self.widget.manual_select_clicked.connect(self._on_manual)
        self.widget.animation_finished.connect(self._on_anim_done)

        self.history = ResultHistoryWidget()
        self.log = LogWidget()

        # ---- 布局 ----
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([300, 800, 320])

        main = QVBoxLayout(self)
        main.addWidget(splitter)
        main.addWidget(self._build_bottom())

        self.log.log("界面初始化完成")
        self._auto_load()  # 自动加载示例数据，验证「立即滚动」

    # ---------------- 左侧控制面板 ----------------
    def _build_left_panel(self):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setAlignment(Qt.AlignTop)

        # 数据
        g1 = QGroupBox("数据")
        f1 = QVBoxLayout(g1)
        self.btn_load = QPushButton("加载示例数据")
        self.btn_load.clicked.connect(self._auto_load)
        self.btn_clear = QPushButton("清空数据")
        self.btn_clear.clicked.connect(self._clear_data)
        self.btn_pause = QPushButton("暂停/恢复")
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.label_count = QLabel("弹幕数: 0")
        f1.addWidget(self.btn_load)
        f1.addWidget(self.btn_clear)
        f1.addWidget(self.btn_pause)
        f1.addWidget(self.label_count)

        # 筛选
        g2 = QGroupBox("筛选/抽奖")
        f2 = QVBoxLayout(g2)
        self.btn_roll = QPushButton("🎲 开始筛选")
        self.btn_roll.clicked.connect(self.widget.on_main_clicked)  # 触发动画+加速+选结果
        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.clicked.connect(self.widget.stop_rolling)
        f2.addWidget(self.btn_roll)
        f2.addWidget(self.btn_stop)

        # 停止模式
        self.combo_stop = QComboBox()
        self.combo_stop.addItem("自动停止", STOP_AUTO)
        self.combo_stop.addItem("手动停止", STOP_MANUAL)
        self.combo_stop.currentIndexChanged.connect(self._change_stop_mode)

        # 结果隐藏模式
        self.combo_hide = QComboBox()
        self.combo_hide.addItem("自动隐藏", RESULT_HIDE_AUTO)
        self.combo_hide.addItem("手动隐藏", RESULT_HIDE_MANUAL)
        self.combo_hide.currentIndexChanged.connect(self._change_hide_mode)

        self.spin_hide = QSpinBox()
        self.spin_hide.setRange(500, 10000)
        self.spin_hide.setValue(3000)
        self.spin_hide.setSuffix(" ms")
        self.spin_hide.valueChanged.connect(self._change_hide_duration)

        # 内定结果
        g3 = QGroupBox("内定结果")
        f3 = QVBoxLayout(g3)
        self.spin_fix = QSpinBox()
        self.spin_fix.setRange(-1, 1000)
        self.spin_fix.setValue(-1)
        self.spin_fix.setSpecialValueText("随机")
        self.spin_fix.valueChanged.connect(self._change_fixed)
        f3.addWidget(QLabel("指定索引 (-1=随机):"))
        f3.addWidget(self.spin_fix)

        # 透明度
        g4 = QGroupBox("全局透明度")
        f4 = QVBoxLayout(g4)
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(10, 100)
        self.slider_opacity.setValue(100)
        self.slider_opacity.valueChanged.connect(self._change_opacity)
        self.label_opacity = QLabel("1.00")
        f4.addWidget(self.slider_opacity)
        f4.addWidget(self.label_opacity)

        # 速度
        g5 = QGroupBox("速度倍率")
        f5 = QVBoxLayout(g5)
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.5, 10.0)
        self.spin_speed.setValue(1.0)
        self.spin_speed.setSingleStep(0.5)
        self.spin_speed.valueChanged.connect(self._change_speed)
        f5.addWidget(self.spin_speed)

        # 显示区域
        g6 = QGroupBox("显示区域")
        f6 = QFormLayout(g6)
        self.spin_x = QSpinBox(); self.spin_x.setRange(0, 500); self.spin_x.setValue(0)
        self.spin_y = QSpinBox(); self.spin_y.setRange(0, 500); self.spin_y.setValue(80)
        self.spin_w = QSpinBox(); self.spin_w.setRange(100, 2000); self.spin_w.setValue(900)
        self.spin_h = QSpinBox(); self.spin_h.setRange(100, 2000); self.spin_h.setValue(340)
        self.btn_apply_rect = QPushButton("应用区域")
        self.btn_apply_rect.clicked.connect(self._apply_rect)
        self.btn_full = QPushButton("充满控件")
        self.btn_full.clicked.connect(self._full_rect)
        f6.addRow("X:", self.spin_x)
        f6.addRow("Y:", self.spin_y)
        f6.addRow("W:", self.spin_w)
        f6.addRow("H:", self.spin_h)
        f6.addRow(self.btn_apply_rect)
        f6.addRow(self.btn_full)

        # 按钮显隐
        g7 = QGroupBox("按钮显隐")
        f7 = QHBoxLayout(g7)
        self.chk_main = QCheckBox("主按钮")
        self.chk_main.setChecked(True)
        self.chk_main.stateChanged.connect(self._toggle_main)
        self.chk_sub = QCheckBox("子按钮")
        self.chk_sub.setChecked(True)
        self.chk_sub.stateChanged.connect(self._toggle_sub)
        f7.addWidget(self.chk_main)
        f7.addWidget(self.chk_sub)

        # 图标
        self.btn_icon = QPushButton("选择主按钮图标...")
        self.btn_icon.clicked.connect(self._choose_icon)

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(QLabel("停止模式:"))
        layout.addWidget(self.combo_stop)
        layout.addWidget(QLabel("结果隐藏:"))
        layout.addWidget(self.combo_hide)
        layout.addWidget(self.spin_hide)
        layout.addWidget(g3)
        layout.addWidget(g4)
        layout.addWidget(g5)
        layout.addWidget(g6)
        layout.addWidget(g7)
        layout.addWidget(self.btn_icon)
        layout.addStretch()
        return box

    # ---------------- 中间主体 ----------------
    def _build_center(self):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.addWidget(self.widget, 1)
        return box

    # ---------------- 右侧清单 ----------------
    def _build_right(self):
        self.checklist = ChecklistWidget()
        return self.checklist

    # ---------------- 底部 ----------------
    def _build_bottom(self):
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.history, 1)
        layout.addWidget(self.log, 1)
        return box

    # ---------------- 槽函数 ----------------
    def _auto_load(self):
        items = build_sample_items()
        self.widget.set_data(items)
        self.spin_fix.setMaximum(max(0, len(items) - 1))
        self.label_count.setText(f"弹幕数: {len(items)}")
        self.log.log(f"加载 {len(items)} 条弹幕，已开始滚动")
        self.history.clear()

    def _clear_data(self):
        self.widget.set_data([])
        self.label_count.setText("弹幕数: 0")
        self.log.log("数据已清空")

    def _toggle_pause(self):
        if not hasattr(self, "_paused") or not self._paused:
            self.widget.pause()
            self._paused = True
            self.log.log("弹幕暂停")
        else:
            self.widget.resume()
            self._paused = False
            self.log.log("弹幕恢复")

    def _change_stop_mode(self):
        mode = self.combo_stop.currentData()
        self.widget.set_stop_mode(mode)
        self.log.log(f"停止模式: {'自动' if mode == STOP_AUTO else '手动'}")

    def _change_hide_mode(self):
        mode = self.combo_hide.currentData()
        self.widget.set_result_hide_mode(mode, duration_ms=self.spin_hide.value())
        self.log.log(f"结果隐藏: {'自动' if mode == RESULT_HIDE_AUTO else '手动'}")

    def _change_hide_duration(self, v):
        mode = self.combo_hide.currentData()
        self.widget.set_result_hide_mode(mode, duration_ms=v)

    def _change_fixed(self, idx):
        if idx < 0:
            self.widget.set_fixed_result(None)
            self.log.log("内定结果: 随机")
        else:
            self.widget.set_fixed_result(idx)
            self.log.log(f"内定结果: 索引 {idx}")

    def _change_opacity(self, v):
        val = v / 100.0
        self.widget.global_opacity = val
        self.label_opacity.setText(f"{val:.2f}")

    def _change_speed(self, v):
        self.widget.set_speed_factor(v)
        self.log.log(f"速度倍率: {v}")

    def _apply_rect(self):
        rect = QRectF(self.spin_x.value(), self.spin_y.value(),
                      self.spin_w.value(), self.spin_h.value())
        self.widget.set_danmaku_rect(rect)
        self.log.log(f"显示区域: {rect}")

    def _full_rect(self):
        self.widget.set_danmaku_rect(None)
        self.log.log("显示区域: 充满控件")

    def _toggle_main(self):
        if self.chk_main.isChecked():
            self.widget.show_main_button()
        else:
            self.widget.hide_main_button()

    def _toggle_sub(self):
        if self.chk_sub.isChecked():
            self.widget.show_sub_button()
        else:
            self.widget.hide_sub_button()

    def _choose_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图标", "", "SVG (*.svg);;PNG (*.png);;All (*)"
        )
        if path:
            self.widget.set_main_icon(path)
            self.log.log(f"图标: {path}")

    def _on_result(self, item):
        text = getattr(item, "text", str(item))
        self.history.add_record(text)
        self.log.log(f"🎯 结果: {text}")
        passed, total = self.checklist.summary()
        self.log.log(f"清单进度: {passed}/{total}")

    def _on_manual(self):
        self.log.log("子按钮(手动选择)被点击")

    def _on_anim_done(self):
        self.log.log("动画完成信号")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    win = ConfirmWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
