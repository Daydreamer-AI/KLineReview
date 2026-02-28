# from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
# from PyQt5.QtQuickWidgets import QQuickWidget # 关键导入
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


# 创建一个用于通信的Python对象
class PolicyFilterSettingBridge(QObject):
    # 定义一个信号，用于向QML发送消息
    messageToQml = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    # 一个槽函数，用于接收来自QML的消息
    @pyqtSlot(str)
    def receiveFromQml(self, message):
        print(f"Python received: {message}")
        # 收到消息后，可以发射信号回QML或执行其他逻辑
        self.messageToQml.emit(f"Echo: {message}")