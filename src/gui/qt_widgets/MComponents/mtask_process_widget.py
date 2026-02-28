from PyQt5 import uic
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, Qt

from thread.base_task import TaskStatus
from thread.baostock_data_fetch_task import BaostockDataFetchTask
from thread.task_pool import get_default_task_pool

from manager.logging_manager import get_logger

class MTaskProcessWidget(QWidget):
    processValueChanged = pyqtSignal(int)
    pause_clicked = pyqtSignal(int)
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(MTaskProcessWidget, self).__init__(parent)
        self.ui = uic.loadUi("./src/gui/qt_widgets/MComponents/MTaskProcessWidget.ui", self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self): 
        self.logger = get_logger(__name__)
        self.task = None

    def init_ui(self):
        self.reset_ui()

    def init_connect(self):
        self.horizontalSlider_process.valueChanged.connect(self.slot_horizontalSlider_process_valueChanged)
        self.btn_pause.clicked.connect(self.slot_btn_pause_clicked)
        self.btn_cancel.clicked.connect(self.slot_btn_cancel_clicked)
        self.btn_detail.clicked.connect(self.slot_btn_detail_clicked)

    def set_task(self, task):
        self.task = task

        if self.task:
            self.task.task_completed.connect(self.slot_baostock_data_fetch_task_completed)
            self.task.task_progress.connect(self.slot_task_progress)
            self.task.task_cancelled.connect(self.slot_task_cancelled)
            # 如果是BaostockDataFetchTask
            if isinstance(self.task, BaostockDataFetchTask):
                self.task.sig_progress_changed.connect(self.slot_progress_changed)

    def reset_ui(self):
        self.widget_detail.hide()
        self.label_process.setText('--/--')

        # self.horizontalSlider_process.blockSignals(True)
        self.horizontalSlider_process.setValue(0)
        # self.horizontalSlider_process.blockSignals(False)

        self.btn_pause.setText('开始') 

        self.btn_cancel.setEnabled(False)

    def update_detail_ui(self, text):
        # self.label_detail.setText(text)
        pass

    def show_detail_ui(self, b_show=True):
        # self.widget_detail.setVisible(b_show)
        if b_show:
            self.btn_detail.show()
            # self.widget_detail.show()
        else:
            self.btn_detail.hide()
            self.widget_detail.hide()

    def slot_horizontalSlider_process_valueChanged(self, value):
        self.processValueChanged.emit(value)

    def slot_btn_pause_clicked(self):
        if self.task is None: 
            return
        
        task_status = self.task.get_task_status()
        self.logger.info(f"task_status: {task_status.value}")
        if task_status == TaskStatus.PENDING or task_status == TaskStatus.CANCELLED or task_status == TaskStatus.COMPLETED or task_status == TaskStatus.FAILED:
            # 如果任务已完成、失败或已取消，重置后再提交
            if task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.task.reset()
            
            task_id = get_default_task_pool().submit(self.task)
            self.logger.info(f"开始执行任务：{task_id}")

            self.btn_cancel.setEnabled(True)
            self.btn_pause.setText('暂停')
        elif task_status == TaskStatus.RUNNING:
            self.task.pause()
            self.btn_pause.setText('继续')
            self.logger.info(f"暂停任务")
        elif task_status == TaskStatus.PAUSED:
            self.task.resume()
            self.btn_pause.setText('暂停')
            self.logger.info(f"继续任务")

        self.pause_clicked.emit(task_status.value)

    def slot_btn_cancel_clicked(self):
        if self.task:
            get_default_task_pool().cancel_task(self.task.get_task_id())

        self.reset_ui()
        self.cancel_clicked.emit()

    def slot_btn_detail_clicked(self):
        if self.widget_detail.isVisible():
            self.widget_detail.hide()
        else:
            self.widget_detail.show()

    def slot_baostock_data_fetch_task_completed(self, task_id, result):
        self.logger.info(f"task_id: {task_id}, result: {result}")


    def slot_task_progress(self, task_id, progress):
        self.logger.info(f"task_id: {task_id}, progress: {progress}")

    def slot_progress_changed(self, completed_tasks, total_tasks):
        if completed_tasks == 0:
            self.horizontalSlider_process.setMinimum(completed_tasks)
            self.horizontalSlider_process.setMaximum(total_tasks)

        self.horizontalSlider_process.setValue(completed_tasks)
        self.label_process.setText(f"{completed_tasks}/{total_tasks}")

        # 更新detail ui

    def slot_task_cancelled(self, task_id):
        self.logger.info(f"task_id: {task_id} cancelled")
