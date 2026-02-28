from PyQt5.QtCore import QObject, pyqtSlot

class MainBridge(QObject):
    """
    一个后端对象，用于处理QML界面的信号和调用。
    必须继承自QObject，这样它的信号和槽才能被QML识别。
    """

    @pyqtSlot(str)
    def receiveFromQML(self, message):
        """
        一个槽函数，用于接收来自QML的信号。
        使用@pyqtSlot装饰器声明它接收一个字符串参数。
        """
        print(f"Python端收到: {message}")