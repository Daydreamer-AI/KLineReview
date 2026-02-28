from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QListWidget, QListWidgetItem
from PyQt5.QtCore import QDate, QFile

import random
from datetime import date

from manager.logging_manager import get_logger
from gui.qt_widgets.MComponents.demo_trading_card_widget import DemoTradingCardWidget
from gui.qt_widgets.MComponents.demo_trading_record_widget import DemoTradingRecordWidget

from processor.baostock_processor import BaoStockProcessor
from manager.bao_stock_data_manager import BaostockDataManager
from manager.period_manager import TimePeriod
from manager.review_demo_trading_manager import ReviewDemoTradingManager

class ReviewWidget(QWidget):
    def __init__(self, parent=None):
        super(ReviewWidget, self).__init__(parent) 
        uic.loadUi('./src/gui/qt_widgets/MComponents/ReviewWidget.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()

        # self.load_data('sh.600000', "2025-12-08")

    def init_para(self):
        self.logger = get_logger(__name__)

        self.type = 0   # 0: 模块；1：对话框
        self.dict_progress_data = {}

        self.current_load_code = ""

        self.demo_trading_manager = ReviewDemoTradingManager()

    def init_ui(self):
        from gui.qt_widgets.MComponents.indicators.indicators_view_widget import IndicatorsViewWidget
        self.indicators_view_widget = IndicatorsViewWidget(self)
        self.indicators_view_widget.setProperty("review", True)
        self.indicators_view_widget.show_review_btn(False)

        self.verticalLayout_indicators_view.addWidget(self.indicators_view_widget)

        self.comboBox_period.addItems([TimePeriod.get_chinese_label(TimePeriod.DAY), TimePeriod.get_chinese_label(TimePeriod.WEEK), TimePeriod.get_chinese_label(TimePeriod.MINUTE_15), TimePeriod.get_chinese_label(TimePeriod.MINUTE_30), TimePeriod.get_chinese_label(TimePeriod.MINUTE_60)])
        self.comboBox_period.setCurrentIndex(0)

        self.btn_load_data_random.setAutoDefault(False)
        self.btn_load_data_random.setDefault(False)

        self.btn_load_data.setAutoDefault(False)
        self.btn_load_data.setDefault(False)

        self.playing_enabled(True, True)

        self.label_total_assets.setText(str(self.demo_trading_manager.get_total_assets()))
        self.label_available_balance.setText(str(self.demo_trading_manager.get_available_balance()))

        self.listWidget_trading_record = QListWidget(self)
        self.demo_trading_record_widget = DemoTradingRecordWidget(self)

        self.stackedWidget_trading_record.addWidget(self.listWidget_trading_record)
        self.stackedWidget_trading_record.addWidget(self.demo_trading_record_widget)
        self.stackedWidget_trading_record.setCurrentWidget(self.listWidget_trading_record)

        self.load_qss()
        self.btn_play.setProperty("is_play", False)
        self.btn_play.style().unpolish(self.btn_play)
        self.btn_play.style().polish(self.btn_play)
        self.btn_play.update()

    def init_connect(self):
        self.indicators_view_widget.sig_current_animation_index_changed.connect(self.slot_current_animation_index_changed)
        self.indicators_view_widget.sig_init_review_animation_finished.connect(self.slot_init_review_animation_finished)
        self.indicators_view_widget.sig_animation_play_finished.connect(self.slot_animation_play_finished)

        self.lineEdit_code.editingFinished.connect(self.slot_lineEdit_code_editingFinished)
        self.dateEdit.dateChanged.connect(self.slot_dateEdit_dateChanged)
        self.comboBox_period.currentIndexChanged.connect(self.slot_comboBox_period_currentIndexChanged)

        self.btn_load_data_random.clicked.connect(self.slot_btn_load_data_random_clicked)
        self.btn_load_data.clicked.connect(self.slot_btn_load_data_clicked)

        self.btn_play.clicked.connect(self.slot_btn_play_clicked)

        self.btn_back_to_front.clicked.connect(self.slot_btn_back_to_front_clicked)
        self.btn_back_ten.clicked.connect(self.slot_btn_back_ten_clicked)
        self.btn_back.clicked.connect(self.slot_btn_back_clicked)
        self.btn_move_on.clicked.connect(self.slot_btn_move_on_clicked)
        self.btn_move_on_10.clicked.connect(self.slot_btn_move_on_10_clicked)
        self.btn_move_to_last.clicked.connect(self.slot_btn_move_to_last_clicked)

        self.horizontalSlider_progress.valueChanged.connect(self.slot_horizontalSlider_progress_valueChanged)

        # 模拟交易
        self.lineEdit_price.editingFinished.connect(self.slot_lineEdit_price_editingFinished)
        self.btn_all.clicked.connect(self.slot_btn_all_clicked)
        self.btn_one_half.clicked.connect(self.slot_btn_one_half_clicked)
        self.btn_one_third.clicked.connect(self.slot_btn_one_third_clicked)
        self.btn_a_quarter.clicked.connect(self.slot_btn_a_quarter_clicked)
        self.btn_one_in_five.clicked.connect(self.slot_btn_one_in_five_clicked)

        self.btn_buy.clicked.connect(self.slot_btn_buy_clicked)
        self.btn_sell.clicked.connect(self.slot_btn_sell_clicked)
        self.btn_pending_order_cancel.clicked.connect(self.slot_btn_pending_order_cancel_clicked)

        self.demo_trading_manager.sig_total_assets_and_available_balance_changed.connect(self.update_assets_and_available_balance)
        self.demo_trading_manager.sig_trading_status_changed.connect(self.slot_demo_trading_manager_sig_trading_status_changed)
        self.demo_trading_record_widget.sig_btn_return_clicked.connect(self.slot_demo_trading_record_widget_sig_btn_return_clicked)

    def load_qss(self, theme="default"):
        qss_file_name = f":/theme/{theme}/mcomponents/review_widget.qss"
        self.logger.info(f"回放模块样式表文件路径：{qss_file_name}")
        qssFile = QFile(qss_file_name)
        if qssFile.open(QFile.ReadOnly):
            str_qss = str(qssFile.readAll(), encoding='utf-8')
            # self.logger.info(f"回放模块样式表内容：{str_qss}")
            self.setStyleSheet(str_qss)
        else:
            self.logger.warning("无法打开回放模块样式表文件")
        qssFile.close()


    def preload_data(self, df_row):
        self.logger.info(f"回放预加载数据: {df_row}")
        if df_row is None:
            self.logger.warning("回放预加载数据为空")
            return
        
        # 对话框模式才会预加载
        self.type = 1
        
        self.label_name.setText(df_row["name"])
        self.lineEdit_code.setText(df_row["code"])

        # self.dateEdit.blockSignals(True)
        self.dateEdit.setDate(QDate.fromString(df_row['date'], "yyyy-MM-dd"))
        # self.dateEdit.blockSignals(False)

        self.btn_load_data_random.hide()
        self.lineEdit_code.setEnabled(False)

    def update_assets_and_available_balance(self, total_assets, available_balance):
        self.label_total_assets.setText(f"{total_assets:.2f}")
        self.label_available_balance.setText(f"{available_balance:.2f}")

    def update_count_and_amount_labels(self, price, count):
        self.lineEdit_count.setText(str(count))
        self.lineEdit_amount.setText(str(count * price))

    def playing_enabled(self, is_playing, b_init=False):
        self.lineEdit_code.setEnabled(not is_playing and self.type == 0)
        self.dateEdit.setEnabled(True if b_init else not is_playing)

        self.btn_back_to_front.setEnabled(not is_playing)
        self.btn_back_ten.setEnabled(not is_playing)
        self.btn_back.setEnabled(not is_playing)
        self.btn_move_on.setEnabled(not is_playing)
        self.btn_move_on_10.setEnabled(not is_playing)
        self.btn_move_to_last.setEnabled(not is_playing)

        self.horizontalSlider_progress.setEnabled(not is_playing)

        self.btn_buy.setEnabled(not is_playing)
        self.btn_sell.setEnabled(not is_playing)
        self.btn_pending_order_cancel.setEnabled(not is_playing)

        self.btn_all.setEnabled(not is_playing)
        self.btn_one_half.setEnabled(not is_playing)
        self.btn_one_third.setEnabled(not is_playing)
        self.btn_a_quarter.setEnabled(not is_playing)
        self.btn_one_in_five.setEnabled(not is_playing)


    def update_progress_label(self, current_index):
        if self.dict_progress_data is not None and self.dict_progress_data != {}:
            s_current_progress = f"{current_index}/{self.dict_progress_data['max_index']}"
            self.label_progress.setText(s_current_progress)
        else:
            self.logger.info("进度数据为空")
            self.label_progress.setText("")

    def update_trading_widgets_status(self):
        trading_status = self.demo_trading_manager.get_trading_status()

        if trading_status == 1 or trading_status == 3:
            self.btn_all.setEnabled(False)
            self.btn_one_half.setEnabled(False)
            self.btn_one_third.setEnabled(False)
            self.btn_a_quarter.setEnabled(False)
            self.btn_one_in_five.setEnabled(False)
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(False)
            self.btn_pending_order_cancel.setEnabled(True)
        elif trading_status == 5:
            self.btn_all.setEnabled(False)
            self.btn_one_half.setEnabled(False)
            self.btn_one_third.setEnabled(False)
            self.btn_a_quarter.setEnabled(False)
            self.btn_one_in_five.setEnabled(False)
            self.btn_buy.setEnabled(False)
            self.btn_sell.setEnabled(True)
            self.btn_pending_order_cancel.setEnabled(False)
        else:
            self.btn_all.setEnabled(True)
            self.btn_one_half.setEnabled(True)
            self.btn_one_third.setEnabled(True)
            self.btn_a_quarter.setEnabled(True)
            self.btn_one_in_five.setEnabled(True)
            self.btn_buy.setEnabled(True)
            self.btn_sell.setEnabled(False)
            self.btn_pending_order_cancel.setEnabled(False)

    def reset_trading_record(self):
        self.lineEdit_price.blockSignals(True)
        self.lineEdit_price.clear()
        self.lineEdit_price.blockSignals(False)

        self.lineEdit_count.clear()
        self.lineEdit_amount.clear()

        # 清空收益率曲线

        # 清空交易记录列表

    def load_data(self, code, date):
        stock_codes = [code]
        bao_stock_data_manager = BaostockDataManager()
        new_dict_lastest_1d_stock_data = bao_stock_data_manager.get_lastest_row_data_dict_by_code_list_auto(stock_codes)
        # self.logger.info(f"new_dict_lastest_1d_stock_data: {new_dict_lastest_1d_stock_data}")

        if new_dict_lastest_1d_stock_data:
            self.indicators_view_widget.update_stock_data_dict(code)
            data = new_dict_lastest_1d_stock_data[code].iloc[-1]
            # self.indicators_view_widget.update_chart(data, '2025-12-08')
            self.dict_progress_data = self.indicators_view_widget.init_animation(data, date)
            # if self.dict_progress_data is not None and self.dict_progress_data != {}:
            #     self.horizontalSlider_progress.setMinimum(self.dict_progress_data['min_index'])
            #     self.horizontalSlider_progress.setMaximum(self.dict_progress_data['max_index'])

            #     self.horizontalSlider_progress.blockSignals(True)
            #     self.horizontalSlider_progress.setSliderPosition(self.dict_progress_data['start_date_index'])
            #     self.horizontalSlider_progress.blockSignals(False)

            #     self.update_progress_label(self.dict_progress_data['start_date_index'])
            # else:
            #     self.logger.info(f"初始化返回的进度数据为空")

            self.current_load_code = code

            # self.demo_trading_manager.reset_trading_record()  # 重新加载不用情况当前收益
            self.playing_enabled(False)
            self.update_trading_widgets_status()
            self.reset_trading_record()

        else:
            self.logger.info(f"结果为空")

    def get_random_date(self, latest_date_str=None, days_before_start=360, days_before_end=120):
        '''
        根据给定的最新日期和范围参数，在指定范围内随机返回一个日期
        
        Args:
            latest_date_str (str): 最新日期字符串，格式为 "YYYY-MM-DD"，默认为当前日期
            days_before_start (int): 最新日期往前推的起始天数，默认为30天
            days_before_end (int): 最新日期往前推的结束天数，默认为1天
        
        Returns:
            str: 格式为 "YYYY-MM-DD" 的随机日期字符串
            
        Example:
            # 在 2026-01-19 前 30 天到 1 天的范围内随机选择日期
            random_date = get_random_date("2026-01-19", 30, 1)
        '''
        from datetime import datetime, timedelta
        
        # 如果未提供最新日期，则使用当前日期
        if latest_date_str is None:
            latest_date = date.today()
        else:
            try:
                latest_date = datetime.strptime(latest_date_str, "%Y-%M-%D").date()
            except ValueError:
                # 处理输入日期格式错误的情况
                latest_date = date.today()
        
        # 计算范围边界
        start_date = latest_date - timedelta(days=days_before_start)
        end_date = latest_date - timedelta(days=days_before_end)
        
        # 确保开始日期不晚于结束日期
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        # 计算日期范围内的总天数
        total_days = (end_date - start_date).days
        
        # 在范围内随机选择一天
        random_day_offset = random.randint(0, total_days)
        random_date = start_date + timedelta(days=random_day_offset)
        
        return random_date.strftime("%Y-%m-%d")



    # -----------------槽函数----------------
    def slot_current_animation_index_changed(self, index):
        # self.logger.info(f"收到k线图进度: {index}")

        self.horizontalSlider_progress.blockSignals(True)
        self.horizontalSlider_progress.setSliderPosition(index)
        self.horizontalSlider_progress.blockSignals(False)

        self.update_progress_label(index)

        date_time = self.indicators_view_widget.get_current_date_time_by_index(index)
        dict_kline_price = self.indicators_view_widget.get_kline_price_by_index(index)

        trading_status = self.demo_trading_manager.get_trading_status()

        target_status = 0
        if trading_status == 1:
            target_status = 1
        elif trading_status == 3:
            target_status = 2
        elif trading_status == 5:
            target_status = 5
        
        self.demo_trading_manager.update_trading_record(target_status, dict_kline_price, date_time)

    def slot_init_review_animation_finished(self, success, dict_progress_data):
        if success:
            self.logger.info("回放动画初始化成功")
            self.dict_progress_data = dict_progress_data
            if self.dict_progress_data is not None and self.dict_progress_data != {}:
                self.horizontalSlider_progress.setMinimum(self.dict_progress_data['min_index'])
                self.horizontalSlider_progress.setMaximum(self.dict_progress_data['max_index'])

                self.horizontalSlider_progress.blockSignals(True)
                self.horizontalSlider_progress.setSliderPosition(self.dict_progress_data['start_date_index'])
                self.horizontalSlider_progress.blockSignals(False)

                self.update_progress_label(self.dict_progress_data['start_date_index'])

                # start_date = self.dict_progress_data['start_date']
                # self.logger.info(f"实际开始日期--start_date: {start_date}")

                # self.dateEdit.blockSignals(True)
                # self.dateEdit.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
                # self.dateEdit.blockSignals(False)

            else:
                self.logger.info(f"初始化返回的进度数据为空")

    def slot_animation_play_finished(self):
        self.slot_btn_play_clicked()

    def slot_lineEdit_code_editingFinished(self):
        code = self.lineEdit_code.text()
        dict_lastest_1d_data = BaostockDataManager().get_lastest_1d_stock_data_dict_from_cache()
        if code not in dict_lastest_1d_data:
            QMessageBox.warning(self, "提示", "请输入正确的股票代码")
            return
        
        self.label_name.setText(str(dict_lastest_1d_data[code]['name'].iloc[0]))

        self.lineEdit_code.blockSignals(True)
        self.lineEdit_code.clearFocus()
        self.lineEdit_code.blockSignals(False)

    def slot_dateEdit_dateChanged(self, date):
        self.logger.info(f"收到日期选择: {date}")
        s_date = date.toString("yyyy-MM-dd")
        self.logger.info(f"收到日期选择--s_date: {s_date}")

    def slot_comboBox_period_currentIndexChanged(self, index):
        text = self.comboBox_period.currentText()
        self.logger.info(f"收到周期选择: {text}, index: {index}")

    def slot_btn_load_data_random_clicked(self):
        # 从 dict_lastest_1d_data 中获取一个随机的 code 和对应的 name
        dict_lastest_1d_data = BaostockDataManager().get_lastest_1d_stock_data_dict_from_cache()
        if dict_lastest_1d_data:
            # 随机选择一个 code
            code = random.choice(list(dict_lastest_1d_data.keys()))
            
            # 获取对应的 name
            name = dict_lastest_1d_data[code]['name'].iloc[0]

            newest_date = dict_lastest_1d_data[code]['date'].iloc[0]
            
            print(f"随机股票代码: {code}, 对应名称: {name}，最新日期: {newest_date}")
        else:
            print("没有可用的股票数据")
            return
        
        date = self.get_random_date(newest_date)

        period = self.comboBox_period.currentText()
        self.logger.info(f"点击随机加载数据: {code}, {date}, {period}")

        if self.current_load_code == code:
            self.logger.info("当前股票数据已加载，无需重复加载")
            return
        
        self.load_data(code, date)

        start_date = self.dict_progress_data['start_date']
        self.logger.info(f"实际开始日期--start_date: {start_date}")

        self.label_name.setText(str(dict_lastest_1d_data[code]['name'].iloc[0]))

        self.lineEdit_code.blockSignals(True)
        self.lineEdit_code.setText(code)
        self.lineEdit_code.blockSignals(False)

        self.dateEdit.blockSignals(True)
        self.dateEdit.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
        self.dateEdit.blockSignals(False)

        self.btn_buy.setDefault(True)


    def slot_btn_load_data_clicked(self):
        code = self.lineEdit_code.text()
        date = self.dateEdit.date().toString("yyyy-MM-dd")
        period = self.comboBox_period.currentText()
        self.logger.info(f"点击加载数据: {code}, {date}, {period}")

        if self.current_load_code == code:
            self.logger.info("当前股票数据已加载，无需重复加载")
            return
        
        self.load_data(code, date)

        start_date = self.dict_progress_data['start_date']
        self.logger.info(f"实际开始日期--start_date: {start_date}")

        self.dateEdit.blockSignals(True)
        self.dateEdit.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
        self.dateEdit.blockSignals(False)

        self.btn_buy.setDefault(True)

    def slot_btn_play_clicked(self):
        if self.btn_play.property("is_play"):
            self.logger.info("暂停播放")
            self.indicators_view_widget.pause_animation()
            self.btn_play.setProperty("is_play", False)
            # self.btn_play.setIcon(QtGui.QIcon("./src/gui/qt_widgets/images/pause.png"))
            self.playing_enabled(False)
        else:
            self.logger.info("开始播放")
            self.indicators_view_widget.start_animation()
            self.btn_play.setProperty("is_play", True)
            self.playing_enabled(True)

        self.btn_play.style().unpolish(self.btn_play)
        self.btn_play.style().polish(self.btn_play)
        self.btn_play.update()

    def slot_btn_back_to_front_clicked(self):
        self.indicators_view_widget.back_to_front()

    def slot_btn_back_ten_clicked(self):
        self.indicators_view_widget.step_backward(10)

    def slot_btn_back_clicked(self):
        self.indicators_view_widget.step_backward()

    def slot_btn_move_on_clicked(self):
        self.indicators_view_widget.step_forward()

    def slot_btn_move_on_10_clicked(self):
        self.indicators_view_widget.step_forward(10)

    def slot_btn_move_to_last_clicked(self):
        self.indicators_view_widget.back_to_end()

    def slot_horizontalSlider_progress_valueChanged(self, value):
        self.logger.info(f"进度条值改变: {value}")
        self.indicators_view_widget.go_to_target_index(value)

    def slot_lineEdit_price_editingFinished(self):
        str_price = self.lineEdit_price.text()
        str_count = self.lineEdit_count.text()

        if str_price == "" or str_count == "":
            return
        self.lineEdit_amount.setText(str(float(str_price) * int(str_count)))

    def slot_btn_all_clicked(self):
        str_price = self.lineEdit_price.text()
        max_count = self.demo_trading_manager.get_buy_count(float(str_price))

        self.logger.info(f"最大可买数量: {max_count}")
        self.lineEdit_count.setText(str(max_count))
        self.lineEdit_amount.setText(str(max_count * float(str_price)))

    def slot_btn_one_half_clicked(self):
        str_price = self.lineEdit_price.text()
        max_count = self.demo_trading_manager.get_buy_count(float(str_price), 1)

        self.logger.info(f"最大可买数量: {max_count}")
        self.lineEdit_count.setText(str(max_count))
        self.lineEdit_amount.setText(str(max_count * float(str_price)))

    def slot_btn_one_third_clicked(self):
        str_price = self.lineEdit_price.text()
        max_count = self.demo_trading_manager.get_buy_count(float(str_price), 2)
        self.logger.info(f"最大可买数量: {max_count}")
        self.lineEdit_count.setText(str(max_count))
        self.lineEdit_amount.setText(str(max_count * float(str_price)))

    def slot_btn_a_quarter_clicked(self):
        str_price = self.lineEdit_price.text()
        max_count = self.demo_trading_manager.get_buy_count(float(str_price), 3)
        self.logger.info(f"最大可买数量: {max_count}")
        self.lineEdit_count.setText(str(max_count))
        self.lineEdit_amount.setText(str(max_count * float(str_price)))

    def slot_btn_one_in_five_clicked(self):
        str_price = self.lineEdit_price.text()
        max_count = self.demo_trading_manager.get_buy_count(float(str_price), 4)

        self.logger.info(f"最大可买数量: {max_count}")
        self.lineEdit_count.setText(str(max_count))
        self.lineEdit_amount.setText(str(max_count * float(str_price)))

    def slot_btn_buy_clicked(self):
        if self.current_load_code == "":
            self.logger.info("请先加载股票数据")
            return

        str_code = self.lineEdit_code.text()
        str_name = self.label_name.text()
        str_price = self.lineEdit_price.text()
        str_count = self.lineEdit_count.text()

        if str_price == "" or str_count == "":
            self.logger.info("请填写价格和数量")
            return

        current_index = self.horizontalSlider_progress.value()
        str_date_time = self.indicators_view_widget.get_current_date_time_by_index(current_index)
        self.logger.info(f"点击买入: {str_code}, {str_name}, {str_price}, {str_count}, {str_date_time}")
        self.demo_trading_manager.pending_order_buy(str_code, str_name, float(str_price), int(str_count), str_date_time)

    def slot_btn_sell_clicked(self):
        if self.current_load_code == "":
            self.logger.info("请先加载股票数据")
            return
        str_price = self.lineEdit_price.text()
        str_count = self.lineEdit_count.text()

        current_index = self.horizontalSlider_progress.value()
        str_date_time = self.indicators_view_widget.get_current_date_time_by_index(current_index)

        self.logger.info(f"点击卖出: {str_price}, {str_count}, {str_date_time}")
        self.demo_trading_manager.pending_order_sell(float(str_price), int(str_count), str_date_time)

    def slot_btn_pending_order_cancel_clicked(self):
        if self.current_load_code == "":
            self.logger.info("请先加载股票数据")
            return
        
        current_index = self.horizontalSlider_progress.value()
        str_date_time = self.indicators_view_widget.get_current_date_time_by_index(current_index)
        dict_kline_price = self.indicators_view_widget.get_kline_price_by_index(current_index)

        self.logger.info(f"点击取消挂单: {str_date_time}")
        self.demo_trading_manager.update_trading_record(0, dict_kline_price, str_date_time)

    def slot_demo_trading_manager_sig_trading_status_changed(self, status):
        self.update_trading_widgets_status()

        if status == 1:
            # 添加Item到ListWidget
            demo_trading_card_widget = DemoTradingCardWidget()
            demo_trading_card_widget.set_data(self.demo_trading_manager.current_trading_record)
            demo_trading_card_widget.update_ui()

            self.demo_trading_manager.sig_trading_yield_changed.connect(demo_trading_card_widget.slot_trading_status_changed)
            self.demo_trading_manager.sig_trading_status_changed.connect(demo_trading_card_widget.slot_trading_status_changed)
            demo_trading_card_widget.clicked.connect(self.slot_demo_trading_card_clicked)
            # demo_trading_card_widget.hovered.connect(self.slot_demo_trading_card_hovered)
            # demo_trading_card_widget.hoverLeft.connect(self.slot_demo_trading_card_hover_left)
            # demo_trading_card_widget.doubleClicked.connect(self.slot_demo_trading_card_double_clicked)

            item = QListWidgetItem(self.listWidget_trading_record)
            # 设置 item 的大小（可选）
            item.setSizeHint(demo_trading_card_widget.sizeHint())
            # item.setSizeHint(QtCore.QSize(200, 60))
            
            # 将 item 添加到 list widget，默认添加到最前
            # self.listWidget_trading_record.addItem(item)
            self.listWidget_trading_record.insertItem(0, item)
            
            # 将自定义 widget 设置为 item 的 widget
            self.listWidget_trading_record.setItemWidget(item, demo_trading_card_widget)
        elif status == 6:
            # 交易完成，更新收益曲线图
            list_data = self.demo_trading_manager.get_trding_record_list()
            self.logger.info(f"交易完成，更新收益曲线图，长度: {len(list_data)}")
            
            for data in list_data:
                self.logger.info(f"code: {data.code}")
                self.logger.info(f"name: {data.name}")

                self.logger.info(f"买入挂单时间: {data.pending_order_buy_date_time}")
                self.logger.info(f"买入挂单取消时间: {data.pending_order_buy_date_time}")

                self.logger.info(f"买入挂单价格: {data.buy_price}")
                self.logger.info(f"买入挂单成交时间: {data.buy_date_time}")

                # self.logger.info(f"买入金额: {data.buy_amount}")
                # self.logger.info(f"买入股数: {data.buy_count}")

                self.logger.info(f"买出挂单时间: {data.pending_order_sell_date_time}")
                self.logger.info(f"买出挂单取消时间: {data.pending_order_sell_cancel_date_time}")

                self.logger.info(f"买出挂单价格: {data.sell_price}")
                self.logger.info(f"买出挂单时间: {data.sell_date_time}")

                # self.logger.info(f"买出金额: {data.sell_amount}")
                # self.logger.info(f"买出股数: {data.sell_count}")

                self.logger.info(f"交易状态: {data.status}")
                self.logger.info(f"收益: {data.trading_yield}")

                self.logger.info("\n---------------------------------------------------------\n")

            self.widget_total_yield_curve.update_data(list_data)

    def slot_demo_trading_card_clicked(self, trading_record):
        self.logger.info(f"交易买入挂单时间：{trading_record.pending_order_buy_date_time}")
        self.demo_trading_record_widget.update_trading_record(trading_record)
        self.stackedWidget_trading_record.setCurrentWidget(self.demo_trading_record_widget)

    def slot_demo_trading_record_widget_sig_btn_return_clicked(self):
        self.stackedWidget_trading_record.setCurrentWidget(self.listWidget_trading_record)


