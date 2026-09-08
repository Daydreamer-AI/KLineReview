import sys
import random
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QPushButton, 
                             QVBoxLayout, QLabel, QGraphicsOpacityEffect)
from PyQt5.QtGui import (QPainter, QColor, QFont, QFontMetrics, QLinearGradient, 
                         QBrush, QPen)
from PyQt5.QtCore import Qt, QTimer, QRect, pyqtProperty, QEasingCurve, QPoint

# ================= 配置常量 =================
MAX_FONT_SIZE = 60      # 允许的最大字号
MIN_FONT_SIZE = 20      # 允许的最小字号
TRACK_PADDING = 10      # 轨道之间的垂直间距
HORIZONTAL_GAP = 80     # 同轨道弹幕之间的水平安全距离
BASE_SPEED = 2.0        # 基础滚动速度
ACCEL_SPEED = 12.0      # 加速后的滚动速度 (抽奖时)

# 结果展示配置
RESULT_SHOW_DURATION = 3000  # 默认自动隐藏时间 (毫秒)

# 模拟股票池数据
STOCK_POOL = [
    "002594 比亚迪", "600036 招商银行", "601012 隆基绿能", 
    "601888 中国中免", "300750 宁德时代", "600519 贵州茅台",
    "000858 五粮液", "000333 美的集团", "601318 中国平安"
]

class DanmakuItem:
    """单条弹幕的数据模型"""
    def __init__(self, text, track_idx, font_size, y_pos):
        self.text = text
        self.track_idx = track_idx
        self.font_size = font_size
        self.y_pos = y_pos
        self.x_pos = 0  # 初始位置由生成器决定
        self.color = QColor(random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        self.speed = BASE_SPEED
        self.width = 0  # 将在绘制前计算

class DanmakuWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("无限循环弹幕抽奖器 - 终极修复版")
        self.setStyleSheet("background-color: #1a1a1a; border: none;")
        
        # --- 核心状态变量 ---
        self.is_lottery_active = False
        self.active_danmakus = []
        self.current_index = 0  # 无限循环指针
        
        # 轨道系统
        self.tracks = [] 
        self.track_height = 0
        
        # 结果展示层变量
        self.final_result = None
        self._result_opacity = 0.0
        self._result_scale = 0.5
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._auto_hide_result)
        
        # 主刷新定时器 (60FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(16) 
        
        # UI 布局
        self.btn_layout = QHBoxLayout()
        self.btn_layout.addStretch()
        
        self.btn_start = QPushButton("🚀 开始筛选")
        self.btn_start.setFixedSize(120, 40)
        self.btn_start.setStyleSheet("""
            QPushButton { background-color: #FFD700; color: black; border-radius: 20px; font-weight: bold; }
            QPushButton:hover { background-color: #FFC107; }
        """)
        self.btn_start.clicked.connect(self.toggle_lottery)
        
        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.setFixedSize(100, 40)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #FF4D4D; color: white; border-radius: 20px; font-weight: bold; }
            QPushButton:hover { background-color: #FF3333; }
        """)
        self.btn_stop.clicked.connect(self.stop_lottery)
        self.btn_stop.hide()
        
        self.btn_layout.addWidget(self.btn_start)
        self.btn_layout.addWidget(self.btn_stop)
        self.btn_layout.addStretch()
        
        main_layout = QVBoxLayout(self)
        main_layout.addStretch()
        main_layout.addLayout(self.btn_layout)
        main_layout.addSpacing(20)
        
        self.resize(1200, 800)
        self.calculate_tracks()

    def calculate_tracks(self):
        """预计算轨道高度和数量"""
        max_fm = QFontMetrics(QFont("Microsoft YaHei", MAX_FONT_SIZE))
        max_h = max_fm.height()
        self.track_height = max_h + TRACK_PADDING
        h = self.height()
        count = max(1, h // self.track_height)
        # 初始化轨道占用记录 [最后一条弹幕的右边缘X坐标]
        self.tracks = [-1000] * count 

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.calculate_tracks()

    def toggle_lottery(self):
        if not self.is_lottery_active:
            self.is_lottery_active = True
            self.btn_start.hide()
            self.btn_stop.show()
            # 加速所有现有弹幕
            for item in self.active_danmakus:
                item.speed = ACCEL_SPEED
        else:
            self.stop_lottery()

    def stop_lottery(self):
        if not self.is_lottery_active:
            return
            
        self.is_lottery_active = False
        self.btn_stop.hide()
        self.btn_start.show()
        
        # 恢复速度
        for item in self.active_danmakus:
            item.speed = BASE_SPEED
            
        # 抽取结果并展示
        winner = random.choice(STOCK_POOL)
        self.show_result(winner)

    def show_result(self, text):
        self.final_result = text
        self._result_opacity = 1.0
        self._result_scale = 0.5
        self.update()
        # 启动自动隐藏计时器
        self.hide_timer.start(RESULT_SHOW_DURATION)

    def _auto_hide_result(self):
        """平滑淡出"""
        # 这里可以使用 QPropertyAnimation，但为了简单直接设置
        # 实际项目中建议用动画类
        self.final_result = None
        self._result_opacity = 0.0
        self.update()

    def mousePressEvent(self, event):
        """点击任意位置手动隐藏结果"""
        if self.final_result and self._result_opacity > 0:
            self.hide_timer.stop()
            self._auto_hide_result()
        super().mousePressEvent(event)

    def update_logic(self):
        """核心逻辑循环：移动、清理、生成"""
        w = self.width()
        current_speed = ACCEL_SPEED if self.is_lottery_active else BASE_SPEED
        
        # 1. 移动与清理
        next_danmakus = []
        for item in self.active_danmakus:
            item.x_pos -= item.speed
            # 只有完全离开屏幕才销毁
            if item.x_pos + item.width > -50:
                next_danmakus.append(item)
            else:
                # 释放轨道占用
                if 0 <= item.track_idx < len(self.tracks):
                    self.tracks[item.track_idx] = -1000
        self.active_danmakus = next_danmakus
        
        # 2. 尝试生成新弹幕 (每帧都有概率生成，保证密度)
        spawn_chance = 0.3 if not self.is_lottery_active else 0.6
        if random.random() < spawn_chance:
            self._spawn_danmaku(w)
            
        self.update()

    def _spawn_danmaku(self, screen_w):
        """智能生成弹幕：寻找空闲轨道"""
        if not self.tracks: return
        
        # 随机选一个轨道尝试
        track_idx = random.randint(0, len(self.tracks) - 1)
        last_x = self.tracks[track_idx]
        
        # 检查碰撞：如果该轨道最后一条弹幕还没走远，则放弃本次生成
        if last_x > screen_w - HORIZONTAL_GAP:
            return
            
        # 获取文本 (无限循环)
        text = STOCK_POOL[self.current_index % len(STOCK_POOL)]
        self.current_index += 1
        
        # 随机字体大小
        f_size = random.randint(MIN_FONT_SIZE, MAX_FONT_SIZE)
        fm = QFontMetrics(QFont("Microsoft YaHei", f_size))
        t_width = fm.horizontalAdvance(text)
        
        # 创建弹幕
        y_base = track_idx * self.track_height + TRACK_PADDING // 2
        item = DanmakuItem(text, track_idx, f_size, y_base)
        item.width = t_width
        item.x_pos = screen_w  # 从最右侧开始
        item.speed = ACCEL_SPEED if self.is_lottery_active else BASE_SPEED
        
        self.active_danmakus.append(item)
        # 锁定轨道
        self.tracks[track_idx] = screen_w 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # === Layer 1: 绘制滚动弹幕 ===
        # 强制裁剪，防止溢出
        painter.setClipRect(self.rect())
        
        for item in self.active_danmakus:
            font = QFont("Microsoft YaHei", item.font_size, QFont.Bold)
            painter.setFont(font)
            painter.setPen(item.color)
            # 垂直居中于轨道内
            fm = QFontMetrics(font)
            y = item.y_pos + fm.ascent()
            painter.drawText(int(item.x_pos), int(y), item.text)
            
        # === Layer 2: 绘制结果展示 ===
        if self.final_result and self._result_opacity > 0.01:
            painter.save()
            # 设置裁剪区域，确保结果也不画出界
            painter.setClipRect(self.rect()) 
            
            w, h = self.width(), self.height()
            painter.translate(w // 2, h // 2)
            painter.scale(self._result_scale, self._result_scale)
            
            # 绘制发光背景
            glow_font = QFont("Microsoft YaHei", 80, QFont.Bold)
            painter.setFont(glow_font)
            painter.setPen(Qt.NoPen)
            
            # 简单的辉光模拟
            for i in range(3, 0, -1):
                c = QColor(255, 215, 0, int(40 / i))
                painter.setBrush(c)
                painter.drawText(QRect(-400, -60, 800, 120), Qt.AlignCenter, self.final_result)
            
            # 绘制主体文字
            painter.setPen(QColor(255, 255, 255))
            painter.setBrush(Qt.NoBrush)
            painter.drawText(QRect(-400, -60, 800, 120), Qt.AlignCenter, self.final_result)
            
            painter.restore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DanmakuWidget()
    window.show()
    sys.exit(app.exec_())