import sys
import math
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout

class MaskWidget(QWidget):
    """
    遮罩层控件 - 可以单独使用，也可以配合Loading控件使用
    """
    def __init__(self, parent=None, opacity=0.7, color=QColor(0, 0, 0, 128)):
        super().__init__(parent)
        self.opacity = opacity
        self.mask_color = color
        
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # 覆盖整个父窗口
        if parent:
            parent.installEventFilter(self)
            self.setGeometry(parent.rect())
    
    def paintEvent(self, event):
        """绘制半透明遮罩"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置透明度
        painter.setOpacity(self.opacity)
        
        # 填充背景色
        painter.fillRect(self.rect(), self.mask_color)
    
    def resizeEvent(self, event):
        """窗口大小变化时重新调整位置和大小"""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)

class LoadingAnimation(QWidget):
    """
    加载动画控件 - 提供多种动画效果
    """
    def __init__(self, parent=None, animation_type="rotating", size=80):
        super().__init__(parent)
        self.animation_type = animation_type  # rotating, dots, bar
        self.size = size
        self.angle = 0
        self.dot_radius = 5
        self.dot_count = 8
        self.progress = 0
        
        # 设置固定大小
        self.setFixedSize(size, size)
        
        # 颜色设置
        self.primary_color = QColor(66, 133, 244)  # Material Blue
        self.secondary_color = QColor(219, 68, 55)  # Material Red
        self.tertiary_color = QColor(244, 180, 0)   # Material Yellow
        
        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        
        # 启动动画
        if animation_type == "bar":
            self.timer.start(50)  # 进度条动画更快
        else:
            self.timer.start(50)  # 其他动画50ms更新一次
        
        # 属性动画（用于淡入淡出效果）
        self._opacity = 1.0
        self.opacity_animation = QPropertyAnimation(self, b"opacity")
        self.opacity_animation.setDuration(300)
    
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        self._opacity = value
        self.update()
    
    opacity = pyqtProperty(float, get_opacity, set_opacity)
    
    def update_animation(self):
        """更新动画状态"""
        if self.animation_type == "rotating":
            self.angle = (self.angle + 10) % 360
        elif self.animation_type == "dots":
            self.angle = (self.angle + 5) % 360
        elif self.animation_type == "bar":
            self.progress = (self.progress + 3) % 100
        self.update()
    
    def paintEvent(self, event):
        """绘制加载动画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置透明度
        painter.setOpacity(self._opacity)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        if self.animation_type == "rotating":
            self.draw_rotating_circle(painter, center_x, center_y)
        elif self.animation_type == "dots":
            self.draw_rotating_dots(painter, center_x, center_y)
        elif self.animation_type == "bar":
            self.draw_progress_bar(painter, center_x, center_y)
    
    def draw_rotating_circle(self, painter, center_x, center_y):
        """绘制旋转圆圈动画"""
        radius = min(center_x, center_y) - 10
        
        # 绘制背景圆环
        pen = QPen(self.primary_color)
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center_x - radius, center_y - radius, 
                           radius * 2, radius * 2)
        
        # 绘制旋转圆弧
        pen.setColor(self.secondary_color)
        painter.setPen(pen)
        
        start_angle = self.angle * 16
        span_angle = 120 * 16  # 120度弧长
        
        painter.drawArc(center_x - radius, center_y - radius,
                       radius * 2, radius * 2,
                       start_angle, span_angle)
    
    def draw_rotating_dots(self, painter, center_x, center_y):
        """绘制旋转点阵动画"""
        radius = min(center_x, center_y) - 15
        
        for i in range(self.dot_count):
            angle = 2 * math.pi * i / self.dot_count + math.radians(self.angle)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            # 根据位置设置颜色和大小
            dot_size = self.dot_radius * (0.5 + 0.5 * abs(math.sin(angle + math.radians(self.angle))))
            
            # 设置颜色渐变
            color_ratio = (i + self.angle / 360) % 1.0
            if color_ratio < 0.33:
                color = self.primary_color
            elif color_ratio < 0.66:
                color = self.secondary_color
            else:
                color = self.tertiary_color
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x - dot_size), int(y - dot_size),
                              int(dot_size * 2), int(dot_size * 2))
    
    def draw_progress_bar(self, painter, center_x, center_y):
        """绘制进度条动画"""
        bar_width = self.width() - 40
        bar_height = 8
        bar_x = 20
        bar_y = center_y - bar_height // 2
        
        # 绘制背景条
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(200, 200, 200, 100)))
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, 4, 4)
        
        # 绘制进度条
        progress_width = int(bar_width * self.progress / 100)
        
        # 创建渐变
        gradient = QColor(self.primary_color)
        gradient.setAlpha(200)
        painter.setBrush(QBrush(gradient))
        
        # 绘制进度条（带圆角）
        path = QPainterPath()
        path.addRoundedRect(bar_x, bar_y, progress_width, bar_height, 4, 4)
        painter.drawPath(path)
        
        # 绘制进度文本
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial", 10))
        text = f"{self.progress}%"
        text_rect = painter.boundingRect(0, 0, 100, 100, Qt.AlignCenter, text)
        painter.drawText(center_x - text_rect.width() // 2,
                        bar_y - 10, text)
    
    def fade_out(self):
        """淡出动画"""
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.opacity_animation.start()
    
    def fade_in(self):
        """淡入动画"""
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.opacity_animation.start()
    
    def stop(self):
        """停止动画"""
        self.timer.stop()
    
    def start(self):
        """开始动画"""
        self.timer.start(50)

class LoadingWidget(QWidget):
    """
    完整的Loading控件 - 包含遮罩和加载动画
    """
    def __init__(self, parent=None, message="加载中...", animation_type="rotating", 
                 show_mask=True, mask_opacity=0.7):
        super().__init__(parent)
        
        self.message = message
        self.animation_type = animation_type
        self.show_mask = show_mask
        self.mask_opacity = mask_opacity
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # 创建遮罩（如果需要）
        if self.show_mask and self.parent():
            self.mask = MaskWidget(self.parent(), self.mask_opacity)
        else:
            self.mask = None
        
        # 创建加载动画
        self.loading_animation = LoadingAnimation(self, self.animation_type, 80)
        
        # 创建消息标签
        self.message_label = QLabel(self.message)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        
        # 添加到布局
        layout.addWidget(self.loading_animation, 0, Qt.AlignCenter)
        layout.addWidget(self.message_label, 0, Qt.AlignCenter)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(60, 60, 60, 200);
                border-radius: 10px;
                padding: 20px;
            }
        """)
        
        # 设置固定大小
        self.setFixedSize(200, 180)
    
    def show_loading(self):
        """显示Loading"""
        if self.mask:
            self.mask.show()
        
        self.loading_animation.fade_in()
        self.show()
    
    def hide_loading(self):
        """隐藏Loading"""
        if self.mask:
            self.mask.hide()
        
        self.loading_animation.fade_out()
        QTimer.singleShot(300, self.hide)  # 等待淡出动画完成
    
    def set_message(self, message):
        """设置加载消息"""
        self.message = message
        self.message_label.setText(message)
    
    def set_animation_type(self, animation_type):
        """设置动画类型"""
        self.animation_type = animation_type
        # 这里可以重新创建动画控件，简化处理
        self.loading_animation.stop()
        self.layout().removeWidget(self.loading_animation)
        self.loading_animation.deleteLater()
        
        self.loading_animation = LoadingAnimation(self, animation_type, 80)
        self.layout().insertWidget(0, self.loading_animation, 0, Qt.AlignCenter)

class ExampleWindow(QWidget):
    """
    示例窗口 - 演示Loading控件的使用
    """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.loading_widget = None
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('PyQt5 Loading控件示例')
        self.setGeometry(300, 300, 800, 600)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 创建标题
        title_label = QLabel("自定义Loading控件演示")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin-bottom: 20px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # 创建控制按钮区域
        control_layout = QHBoxLayout()
        
        # 创建各种Loading按钮
        self.btn_simple = QPushButton("显示简单Loading")
        self.btn_simple.clicked.connect(self.show_simple_loading)
        
        self.btn_with_text = QPushButton("显示带文本Loading")
        self.btn_with_text.clicked.connect(self.show_loading_with_text)
        
        self.btn_dots = QPushButton("显示点阵动画")
        self.btn_dots.clicked.connect(self.show_dots_animation)
        
        self.btn_progress = QPushButton("显示进度条动画")
        self.btn_progress.clicked.connect(self.show_progress_animation)
        
        control_layout.addWidget(self.btn_simple)
        control_layout.addWidget(self.btn_with_text)
        control_layout.addWidget(self.btn_dots)
        control_layout.addWidget(self.btn_progress)
        
        main_layout.addLayout(control_layout)
        
        # 创建状态显示区域
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                font-size: 16px;
                min-height: 100px;
            }
        """)
        main_layout.addWidget(self.status_label)
        
        # 创建底部按钮
        bottom_layout = QHBoxLayout()
        
        self.btn_hide = QPushButton("隐藏Loading")
        self.btn_hide.clicked.connect(self.hide_loading)
        self.btn_hide.setEnabled(False)
        
        self.btn_change_text = QPushButton("更改加载文本")
        self.btn_change_text.clicked.connect(self.change_loading_text)
        self.btn_change_text.setEnabled(False)
        
        bottom_layout.addWidget(self.btn_hide)
        bottom_layout.addWidget(self.btn_change_text)
        
        main_layout.addLayout(bottom_layout)
        
        # 创建说明文本
        instruction = QLabel(
            "提示：点击上方按钮显示不同类型的Loading控件。\n"
            "Loading会阻止用户与界面交互，直到隐藏。"
        )
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(instruction)
        
        self.setLayout(main_layout)
    
    def show_simple_loading(self):
        """显示简单Loading"""
        self.update_status("显示简单旋转动画Loading...")
        self.show_loading("rotating", "加载中...")
    
    def show_loading_with_text(self):
        """显示带文本的Loading"""
        self.update_status("显示带自定义文本的Loading...")
        self.show_loading("rotating", "正在处理数据，请稍候...")
    
    def show_dots_animation(self):
        """显示点阵动画"""
        self.update_status("显示点阵动画Loading...")
        self.show_loading("dots", "处理中...")
    
    def show_progress_animation(self):
        """显示进度条动画"""
        self.update_status("显示进度条动画Loading...")
        self.show_loading("bar", "正在下载...")
    
    def show_loading(self, animation_type="rotating", message="加载中..."):
        """显示Loading控件"""
        # 如果已经有Loading，先移除
        if self.loading_widget:
            self.hide_loading()
        
        # 创建新的Loading控件
        self.loading_widget = LoadingWidget(
            self, 
            message=message,
            animation_type=animation_type,
            show_mask=True,
            mask_opacity=0.5
        )
        
        # 居中显示
        self.loading_widget.move(
            (self.width() - self.loading_widget.width()) // 2,
            (self.height() - self.loading_widget.height()) // 2
        )
        
        # 显示Loading
        self.loading_widget.show_loading()
        
        # 禁用其他按钮
        self.set_buttons_enabled(False)
        self.btn_hide.setEnabled(True)
        self.btn_change_text.setEnabled(True)
    
    def hide_loading(self):
        """隐藏Loading控件"""
        if self.loading_widget:
            self.loading_widget.hide_loading()
            self.loading_widget = None
        
        self.update_status("Loading已隐藏")
        
        # 启用其他按钮
        self.set_buttons_enabled(True)
        self.btn_hide.setEnabled(False)
        self.btn_change_text.setEnabled(False)
    
    def change_loading_text(self):
        """更改Loading文本"""
        if self.loading_widget:
            import random
            messages = [
                "正在处理数据...",
                "请稍候...",
                "加载资源中...",
                "正在计算...",
                "即将完成...",
                "处理中，请不要关闭窗口..."
            ]
            new_message = random.choice(messages)
            self.loading_widget.set_message(new_message)
            self.update_status(f"已更改加载文本为: {new_message}")
    
    def set_buttons_enabled(self, enabled):
        """设置按钮启用状态"""
        self.btn_simple.setEnabled(enabled)
        self.btn_with_text.setEnabled(enabled)
        self.btn_dots.setEnabled(enabled)
        self.btn_progress.setEnabled(enabled)
    
    def update_status(self, message):
        """更新状态文本"""
        self.status_label.setText(message)
    
    def resizeEvent(self, event):
        """窗口大小变化时重新定位Loading控件"""
        super().resizeEvent(event)
        if self.loading_widget:
            self.loading_widget.move(
                (self.width() - self.loading_widget.width()) // 2,
                (self.height() - self.loading_widget.height()) // 2
            )

# 使用示例
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示示例窗口
    window = ExampleWindow()
    window.show()
    
    sys.exit(app.exec_())