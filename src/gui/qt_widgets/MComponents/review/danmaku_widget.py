import sys
import random
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect

class DanmakuItem:
    """单条弹幕的数据模型"""
    def __init__(self, text, track, color="#FFFFFF", font_size=24, font_family="Microsoft YaHei"):
        self.text = text
        self.color = QColor(color)
        self.font = QFont(font_family, font_size, QFont.Bold)
        self.font_size = font_size
        self.track = track  # 绑定的轨道索引
        self.x = 0          
        self.width = 0      

class DanmakuView(QWidget):
    """横向弹幕滚动抽奖控件"""
    selection_finished = pyqtSignal(str)
    manual_select_clicked = pyqtSignal()

    # 预设的随机样式池，用于在外部未指定时随机分配
    STYLE_POOL = [
        {"color": "#FFFFFF", "font_size": 24, "font_family": "Microsoft YaHei"},
        {"color": "#FF4500", "font_size": 28, "font_family": "SimHei"},
        {"color": "#00FF00", "font_size": 20, "font_family": "KaiTi"},
        {"color": "#1E90FF", "font_size": 26, "font_family": "Microsoft YaHei"},
        {"color": "#FFD700", "font_size": 22, "font_family": "SimSun"},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        
        self._data_pool = []        # 原始数据池
        self._active_danmakus = []  # 当前屏幕上活跃的弹幕
        self._rigged_result = None
        self._is_rolling = False
        self._speed_multiplier = 1.0
        self._current_index = 0     # 循环指针
        
        self._track_height = 50
        self._tracks = []  
        
        self._init_ui()
        self._init_timer()

    # ================= 1. 外部接口 (API) =================
    def set_model(self, data_list):
        """接收外部传入的数据列表，初始化轨道并立即开始无限循环滚动"""
        self._data_pool = []
        for item in data_list:
            if isinstance(item, str):
                self._data_pool.append({"text": item})
            elif isinstance(item, dict):
                self._data_pool.append(item)
                
        self._current_index = 0
        self._init_tracks()
        
        if self._data_pool and not self._is_rolling:
            self._is_rolling = True
            self._timer.start()

    def set_rigged_result(self, text: str):
        self._rigged_result = text

    def set_center_controls_visible(self, visible: bool):
        self._center_widget.setVisible(visible)

    # ================= 2. 核心绘制逻辑 =================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))

        for dm in self._active_danmakus:
            painter.setFont(dm.font)
            painter.setPen(QPen(dm.color))
            text_rect = QRect(int(dm.x), int(dm.y), dm.width, dm.font_size + 10)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, dm.text)

    # ================= 3. 动画与定时器逻辑 =================
    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS
        self._timer.timeout.connect(self._update_danmakus)

    def _update_danmakus(self):
        base_speed = 2.0
        for dm in self._active_danmakus:
            dm.x -= base_speed * self._speed_multiplier
            self._tracks[dm.track] = dm.x + dm.width

        self._active_danmakus = [dm for dm in self._active_danmakus if dm.x + dm.width > 0]
        
        # 只要处于滚动状态，就持续尝试生成新弹幕（实现无限循环）
        if self._is_rolling and self._data_pool:
            self._try_spawn_danmaku()

        self.update()

    def _init_tracks(self):
        track_count = max(1, self.height() // self._track_height)
        self._tracks = [-9999] * track_count

    def _get_next_item(self):
        """获取下一条数据，并处理循环和随机样式"""
        if not self._data_pool:
            return None
            
        item = self._data_pool[self._current_index].copy()  # 浅拷贝，避免污染原数据
        
        # 如果外部没有指定颜色或字号，则从样式池中随机抽取一套
        if "color" not in item or "font_size" not in item:
            random_style = random.choice(self.STYLE_POOL)
            item.update(random_style)
            
        # 移动指针，实现无限循环
        self._current_index = (self._current_index + 1) % len(self._data_pool)
        return item

    def _try_spawn_danmaku(self):
        available_tracks = []
        safe_margin = 50  
        
        for i, right_edge in enumerate(self._tracks):
            if right_edge + safe_margin < self.width():
                available_tracks.append(i)
                
        if not available_tracks:
            return

        track = random.choice(available_tracks)
        item = self._get_next_item()
        if not item:
            return
        
        dm = DanmakuItem(
            text=item.get("text", ""),
            track=track,
            color=item.get("color", "#FFFFFF"),
            font_size=item.get("font_size", 24),
            font_family=item.get("font_family", "Microsoft YaHei")
        )
        
        fm = QFontMetrics(dm.font)
        dm.width = fm.horizontalAdvance(dm.text)
        dm.y = track * self._track_height + (self._track_height - dm.font_size) // 2
        dm.x = self.width()  
        
        self._active_danmakus.append(dm)
        self._tracks[track] = dm.x + dm.width

    # ================= 4. 交互逻辑 =================
    def _on_main_btn_clicked(self):
        if not self._is_rolling or not self._data_pool:
            return
        
        # 1. 触发加速效果
        self._speed_multiplier = 3.0
        
        # 2. 决定最终结果
        final_result = self._rigged_result
        if not final_result:
            final_item = random.choice(self._data_pool)
            final_result = final_item.get("text", "")
            self._rigged_result = final_result

        # 3. 将内定结果强制插入到指针的下一个位置，确保它必定出场
        rigged_item = {"text": final_result, "color": "#FFD700", "font_size": 32}
        self._data_pool.insert(self._current_index, rigged_item)
        
        # 4. 延迟恢复基础速度，并发送完成信号
        QTimer.singleShot(2000, lambda: self._on_roll_finished(final_result))

    def _on_roll_finished(self, result):
        self._speed_multiplier = 1.0
        self.selection_finished.emit(result)
        self._rigged_result = None

    # ================= 5. 内部初始化 =================
    def _init_ui(self):
        self._center_widget = QWidget(self)
        layout = QVBoxLayout(self._center_widget)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignCenter)

        self._main_btn = QPushButton("🎲 开始筛选")
        self._main_btn.setFixedSize(120, 50)
        self._main_btn.setCursor(Qt.PointingHandCursor)
        self._main_btn.setStyleSheet("""
            QPushButton { background-color: #FFD700; border-radius: 25px; border: none; 
                          font-size: 16px; font-weight: bold; color: #333; }
            QPushButton:hover { background-color: #FFC000; }
        """)
        
        self._sub_btn = QPushButton("手动选择")
        self._sub_btn.setCursor(Qt.PointingHandCursor)
        self._sub_btn.setStyleSheet("""
            QPushButton { color: #AAAAAA; background: transparent; border: none; 
                          text-decoration: underline; font-size: 14px; }
            QPushButton:hover { color: #FFFFFF; }
        """)

        layout.addWidget(self._main_btn, 0, Qt.AlignHCenter)
        layout.addWidget(self._sub_btn, 0, Qt.AlignHCenter)

        self._main_btn.clicked.connect(self._on_main_btn_clicked)
        self._sub_btn.clicked.connect(self.manual_select_clicked.emit)


# ================= 测试用例 =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 测试数据：包含纯字符串和自定义样式字典
    stocks = [
        "600519 贵州茅台",
        {"text": "000858 五粮液", "color": "#FF4500", "font_size": 28},
        "300750 宁德时代",
        "002594 比亚迪",
        {"text": "601318 中国平安", "color": "#1E90FF", "font_size": 26},
        "600036 招商银行"
    ]
    
    view = DanmakuView()
    view.setWindowTitle("无限循环弹幕抽奖器")
    view.resize(800, 500)
    view.set_model(stocks)
    view.selection_finished.connect(lambda t: print(f"🎉 最终选中: {t}"))
    
    view.show()
    sys.exit(app.exec_())