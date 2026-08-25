from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QListWidget, QListWidgetItem, QButtonGroup
from PyQt5.QtCore import QDate, QFile

import random
from datetime import date, datetime as dt, timedelta as td

from manager.logging_manager import get_logger
from gui.qt_widgets.MComponents.demo_trading_card_widget import DemoTradingCardWidget
from gui.qt_widgets.MComponents.demo_trading_record_widget import DemoTradingRecordWidget

from processor.baostock_processor import BaoStockProcessor
from processor.period_aggregator import aggregate_period
from manager.bao_stock_data_manager import BaostockDataManager
from manager.period_manager import TimePeriod
from manager.review_demo_trading_manager import ReviewDemoTradingManager

from common.common_api import *

class ReviewWidget(QWidget):
    # 复盘默认后台加载周期（预留调整接口，后续可改为用户配置）
    _DEFAULT_LOAD_PERIODS = [
        # TimePeriod.MINUTE_15,
        # TimePeriod.MINUTE_30,
        # TimePeriod.MINUTE_60,
        TimePeriod.DAY,
        TimePeriod.WEEK,
        TimePeriod.MONTH,
    ]

    # 基周期：远程只拉取基周期，周线等上级周期由基周期本地聚合生成（不依赖远程上级周期接口）
    _BASE_LOAD_PERIODS = [
        TimePeriod.DAY,
    ]

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
        self.dict_progress_data = {}    # 回放进度数据

        self.current_load_code = ""
        self.current_load_period = None
        self._is_loading = False
        self._load_periods = list(self._DEFAULT_LOAD_PERIODS)
        self._base_load_periods = list(self._BASE_LOAD_PERIODS)
        self._fetch_pending_periods = []
        self._fetch_failed_periods = []
        self._fetched_period_data = {}

        self.demo_trading_manager = ReviewDemoTradingManager()

    def init_ui(self):
        from gui.qt_widgets.MComponents.indicators.indicators_view_widget import IndicatorsViewWidget
        self.indicators_view_widget = IndicatorsViewWidget(self)
        self.indicators_view_widget.setProperty("review", True)
        self.indicators_view_widget.show_review_btn(False)

        self.verticalLayout_indicators_view.addWidget(self.indicators_view_widget)

        self.comboBox_period.addItems([TimePeriod.get_chinese_label(period) for period in self.get_load_periods()])
        self.comboBox_period.setCurrentText(TimePeriod.get_chinese_label(TimePeriod.DAY))

        self.btn_load_data_random.setAutoDefault(False)
        self.btn_load_data_random.setDefault(False)

        self.btn_load_data.setAutoDefault(False)
        self.btn_load_data.setDefault(False)

        self.playing_enabled(True, True)

        self.label_total_assets.setText(str(self.demo_trading_manager.get_total_assets()))
        self.label_available_balance.setText(str(self.demo_trading_manager.get_available_balance()))

        self.listWidget_trading_record = QListWidget(self)
        self.demo_trading_record_widget = DemoTradingRecordWidget(self)

        self.amout_button_group = QButtonGroup(self)
        self.amout_button_group.addButton(self.btn_all, 0)
        self.amout_button_group.addButton(self.btn_one_half, 1)
        self.amout_button_group.addButton(self.btn_one_third, 2)
        self.amout_button_group.addButton(self.btn_a_quarter, 3)
        self.amout_button_group.addButton(self.btn_one_in_five, 4)


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
        self.amout_button_group.buttonClicked.connect(self.slot_amout_button_group_buttonClicked)

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
        self.logger.info(f"更新价格、股数和金额标签: {price}, {count}")
        self.lineEdit_price.setText(f"{price:.2f}")
        
        # 持仓时无需更新
        if self.demo_trading_manager.get_trading_status() == 3 or self.demo_trading_manager.get_trading_status() == 5:
            count = self.lineEdit_count.text()
            self.lineEdit_amount.setText(f"{float(count) * price:.2f}")
            return
        
        self.lineEdit_count.setText(str(count))
        self.lineEdit_amount.setText(f"{count * price:.2f}")
        
    def update_count_and_amount_labels_by_kline_data(self, kline_data):
        checked_id = self.amout_button_group.checkedId()
        close = kline_data['close']
        max_count = self.demo_trading_manager.get_buy_count(close, checked_id)

        self.logger.info(f"最大可买数量: {max_count}")
        self.update_count_and_amount_labels(close, max_count)

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

    def get_load_periods(self):
        """获取当前复盘加载周期列表（预留调整接口）"""
        return list(self._load_periods)

    def get_base_load_periods(self):
        """获取远程实际拉取的基周期列表（上级周期由基周期本地聚合，不远程拉取）"""
        return list(self._base_load_periods)

    def set_load_periods(self, periods):
        """设置复盘加载周期列表（预留调整接口）"""
        valid_periods = []
        for period in periods:
            if isinstance(period, TimePeriod) and period not in valid_periods:
                valid_periods.append(period)
        if not valid_periods:
            self.logger.warning("加载周期列表为空或无效，保持原配置")
            return
        self._load_periods = valid_periods

        # 同步周期选择控件选项（保持当前选择，若不在新列表则回退到第一项）
        current_label = self.comboBox_period.currentText()
        period_labels = [TimePeriod.get_chinese_label(p) for p in valid_periods]
        self.comboBox_period.blockSignals(True)
        self.comboBox_period.clear()
        self.comboBox_period.addItems(period_labels)
        if current_label in period_labels:
            self.comboBox_period.setCurrentText(current_label)
        else:
            self.comboBox_period.setCurrentIndex(0)
        self.comboBox_period.blockSignals(False)

        self.logger.info(f"复盘加载周期更新为: {[TimePeriod.get_chinese_label(p) for p in valid_periods]}")

    def load_data(self, code, date):
        """复盘数据统一加载入口：仅由“加载/随机加载”按钮触发。

        一次性在后台从远程 Baostock 获取基周期（默认日线），
        周线等上级周期由基周期按复盘日期本地聚合生成（不依赖远程上级周期接口），
        全部加载完成后统一同步到 indicators_view_widget，并按用户在
        comboBox_period 中选择的周期作为初始显示周期。
        """
        if not code:
            self.logger.warning("股票代码为空，无法加载复盘数据")
            return
        if self._is_loading:
            self.logger.info("数据加载中，忽略重复加载请求")
            return

        # 更新模拟交易状态
        if self.current_load_code != "" and self.current_load_code != code:
            kline_data = self.indicators_view_widget.get_current_kline_data()
            self.demo_trading_manager.force_update_trading(kline_data)

        selected_period = TimePeriod.from_label(self.comboBox_period.currentText())
        self.logger.info(f"开始加载复盘数据: {code}, {date}, 显示周期={TimePeriod.get_chinese_label(selected_period)}")

        # 同股票所有配置周期均已注入内存缓存：仅按新日期重新定位动画，不重复拉取
        if self._all_periods_ready(code):
            self._on_all_periods_loaded(code, date, selected_period)
            return

        # 启动后台加载：缺失周期逐个从远程 Baostock 拉取
        # （baostock 为全局单会话，并发查询不安全，故按顺序串行下载）
        self._start_period_fetch_chain(code, date, selected_period)

    def _all_periods_ready(self, code):
        """当前代码的所有配置周期是否都已注入内存缓存（本次会话由远程数据构建）"""
        if self.current_load_code != code:
            return False
        for period in self.get_base_load_periods():
            cached_df = self.indicators_view_widget.get_stock_data_by_period(period)
            if cached_df is None or cached_df.empty:
                return False
        return True

    def _period_in_cache(self, code, period):
        """指定周期是否已在内存缓存中（仅限当前代码）"""
        if self.current_load_code != code:
            return False
        cached_df = self.indicators_view_widget.get_stock_data_by_period(period)
        return cached_df is not None and not cached_df.empty

    def _start_period_fetch_chain(self, code, date, selected_period):
        """按顺序从远程 Baostock 拉取缺失周期，全部完成后统一同步到 indicators_view_widget"""
        self._is_loading = True
        self.indicators_view_widget.set_period_buttons_enabled([])  # 加载中禁用周期切换按钮
        self.indicators_view_widget.show_loading("dots", "loading...")

        # 分钟级数据获取暂屏蔽：即使通过 set_load_periods 配置了分钟周期也跳过
        skipped_minute_periods = [p for p in self.get_base_load_periods() if TimePeriod.is_minute_level(p)]
        if skipped_minute_periods:
            self.logger.warning(f"分钟级数据获取暂屏蔽，跳过: {[TimePeriod.get_chinese_label(p) for p in skipped_minute_periods]}")

        self._fetch_pending_periods = [
            period for period in self.get_base_load_periods()
            if not TimePeriod.is_minute_level(period) and not self._period_in_cache(code, period)
        ]
        self._fetch_failed_periods = []
        self._fetched_period_data = {}

        if not self._fetch_pending_periods:
            self._on_all_periods_loaded(code, date, selected_period)
            return

        self.logger.info(f"需要远程获取的周期: {[TimePeriod.get_chinese_label(p) for p in self._fetch_pending_periods]}")
        self._fetch_next_period(code, date, selected_period)

    def _fetch_next_period(self, code, date, selected_period):
        if not self._fetch_pending_periods:
            self._on_all_periods_loaded(code, date, selected_period)
            return

        period = self._fetch_pending_periods.pop(0)
        fetch_start_date = self._get_fetch_start_date(date, period)

        from thread.baostock_data_fetch_task import BaostockDataFetchTask2
        from thread.task_pool import get_default_task_pool

        self.logger.info(f"从Baostock远程获取: {code} {TimePeriod.get_chinese_label(period)}, 起始={fetch_start_date}")
        baostock_data_fetch_task = BaostockDataFetchTask2(code=code, period=period, start_date=fetch_start_date)

        def on_completed(task_id, result):
            try:
                baostock_data_fetch_task.task_completed.disconnect(on_completed)
                baostock_data_fetch_task.task_error.disconnect(on_error)
            except TypeError:
                pass
            if isinstance(result, dict):
                self._fetched_period_data[period] = result.get('data')
            self._fetch_next_period(code, date, selected_period)

        def on_error(task_id, error):
            try:
                baostock_data_fetch_task.task_completed.disconnect(on_completed)
                baostock_data_fetch_task.task_error.disconnect(on_error)
            except TypeError:
                pass
            self._fetch_failed_periods.append(period)
            self.logger.error(f"远程获取失败: {code} {TimePeriod.get_chinese_label(period)}: {error}")
            self._fetch_next_period(code, date, selected_period)

        baostock_data_fetch_task.task_completed.connect(on_completed)
        baostock_data_fetch_task.task_error.connect(on_error)
        get_default_task_pool().submit(baostock_data_fetch_task)

    def _get_fetch_start_date(self, date_str, period):
        """根据复盘开始日期计算远程拉取起始日期（预留指标预热区间）。

        日/周线往前留 400 天（覆盖 MA60/MA52 等指标预热）；
        分钟线以复盘日期为起点并放宽 30 天，且不早于近两年，避免历史分钟数据量过大。
        """
        try:
            review_dt = dt.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            review_dt = dt.now()

        if TimePeriod.is_minute_level(period):
            floor_dt = dt(dt.now().year - 2, 1, 1)
            start_dt = max(review_dt - td(days=30), floor_dt)
        else:
            start_dt = review_dt - td(days=400)
        return start_dt.strftime("%Y-%m-%d")

    def _get_random_review_date(self):
        """前复权远程数据仅约三年：随机复盘日期限定在近三年窗口内，并预留指标预热区间。"""
        # baostock 前复权数据起点约为 3 年前；最早日期再向后留 250 天（约 8 个月）作指标预热
        earliest = (dt.now() - td(days=365 * 3 - 250)).strftime("%Y-%m-%d")
        return get_random_date(start_date=earliest)

    def _on_all_periods_loaded(self, code, date, selected_period):
        """所有周期数据就绪（远程拉取完成或内存缓存命中）：统一同步并初始化动画"""
        self._is_loading = False
        self.indicators_view_widget.hide_loading()

        if self._fetch_failed_periods:
            failed_text = "、".join(TimePeriod.get_chinese_label(p) for p in self._fetch_failed_periods)
            self.logger.warning(f"以下周期获取失败: {failed_text}")

        # 1. 组装各周期 DataFrame
        # 1.1 先组装基周期（本轮远程拉取结果优先，其余取内存缓存，均为远程数据）
        dict_stock_data = {}
        base_df = None
        for period in self.get_base_load_periods():
            df = None
            if period in self._fetched_period_data:
                df = self._fetched_period_data[period]
            else:
                cached_df = self.indicators_view_widget.get_stock_data_by_period(period)
                if self.current_load_code == code and cached_df is not None and not cached_df.empty:
                    df = cached_df
            if df is not None and not df.empty:
                dict_stock_data[period] = df
                if base_df is None:
                    base_df = df
        # 1.2 上级周期由基周期按复盘基准时刻 as_of 本地聚合生成，不依赖远程上级周期接口
        for period in self.get_load_periods():
            if period in dict_stock_data or base_df is None or base_df.empty:
                continue
            try:
                derived_df = aggregate_period(base_df, period, as_of=date)
            except Exception as e:
                self.logger.error(f"{code} 周期{TimePeriod.get_chinese_label(period)}聚合失败: {e}")
                derived_df = None
            if derived_df is not None and not derived_df.empty:
                dict_stock_data[period] = derived_df

        indicators_view_widget = self.indicators_view_widget
        indicators_view_widget.set_stock_data(code, dict_stock_data)

        # 2. 仅启用已加载周期的切换按钮（加载期间已全部禁用）
        indicators_view_widget.set_period_buttons_enabled(list(dict_stock_data.keys()))

        # 3. 确定初始显示周期：优先用户选择，缺失时回退到第一个可用周期
        display_period = selected_period if selected_period in dict_stock_data else (
            next(iter(dict_stock_data)) if dict_stock_data else None
        )

        if display_period is None:
            self.logger.warning(f"{code} 所有周期均无数据，无法初始化复盘")
            QMessageBox.warning(self, "提示", f"{code} 各周期均无数据，请检查网络")
            return

        if display_period != selected_period:
            self.logger.warning(
                f"所选周期{TimePeriod.get_chinese_label(selected_period)}无数据，"
                f"回退显示{TimePeriod.get_chinese_label(display_period)}"
            )

        indicators_view_widget.set_current_period(display_period)

        # 周期选择控件与初始显示周期保持一致
        self.comboBox_period.blockSignals(True)
        self.comboBox_period.setCurrentText(TimePeriod.get_chinese_label(display_period))
        self.comboBox_period.blockSignals(False)

        # 4. 动画锚点行取显示周期数据的最后一行（远程数据，含 code/name）
        data_row = dict_stock_data[display_period].iloc[-1]
        if 'name' in data_row:
            self.label_name.setText(str(data_row['name']))

        # 5. 日期越界保护：所选日期超出显示周期数据范围时回退到边界日期
        df_display = dict_stock_data[display_period]
        min_date = str(df_display['date'].iloc[0])
        max_date = str(df_display['date'].iloc[-1])
        if date < min_date:
            self.logger.warning(f"所选日期 {date} 早于数据起点 {min_date}，已回退到 {min_date}")
            date = min_date
        elif date > max_date:
            self.logger.warning(f"所选日期 {date} 晚于数据终点 {max_date}，已回退到 {max_date}")
            date = max_date

        # 6. 初始化复盘动画并刷新状态
        self.dict_progress_data = indicators_view_widget.init_animation(data_row, date)
        if not self.dict_progress_data:
            self.logger.warning(f"复盘动画初始化失败: {code}, {date}, {TimePeriod.get_chinese_label(display_period)}")

        self.current_load_code = code
        self.current_load_period = display_period

        self.playing_enabled(False)
        self.update_trading_widgets_status()
        self.reset_trading_record()

        # 用实际起始日期回填日期选择控件
        start_date = self.dict_progress_data.get('start_date') if self.dict_progress_data else None
        if start_date:
            self.dateEdit.blockSignals(True)
            self.dateEdit.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
            self.dateEdit.blockSignals(False)

        current_kline_data = self.indicators_view_widget.get_current_kline_data()
        self.update_count_and_amount_labels_by_kline_data(current_kline_data)

    def get_random_date(self, latest_date_str=None, days_before_start=360, days_before_end=120):
        '''
        根据给定的最新日期和范围参数，在指定范围内随机返回一个日期
        
        Args:
            latest_date_str (str): 最新日期字符串，格式为 "YYYY-MM-DD"，默认为当前日期
            days_before_start (int): 最新日期往前推的起始天数，默认为360天
            days_before_end (int): 最新日期往前推的结束天数，默认为120天
        
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
    def slot_bao_stock_info_query_started(self, task_id):
        self.logger.info(f"baostock info query started, task_id: {task_id}")
        self.frame_review.setEnabled(False)
    def slot_bao_stock_info_query_finished(self, task_id, result):
        self.logger.info(f"task_id: {task_id}, result: {result}")

        if result["result"]:
            self.frame_review.setEnabled(True)
        else:
            QMessageBox.warning(self, "提示", "BaoStock股票信息查询失败！请检查网络连接或稍后再试！")

    def slot_bao_stock_info_query_error(self, task_id, error):
        self.logger.info(f"task_id: {task_id}, error: {error}")

    def slot_current_animation_index_changed(self, index):
        # self.logger.info(f"收到k线图进度: {index}")

        self.horizontalSlider_progress.blockSignals(True)
        self.horizontalSlider_progress.setSliderPosition(index)
        self.horizontalSlider_progress.blockSignals(False)

        self.update_progress_label(index)

        current_kline_data = self.indicators_view_widget.get_current_kline_data()
        self.update_count_and_amount_labels_by_kline_data(current_kline_data)

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
        # 用本地股票信息库同步校验（不依赖后台日线缓存）
        name = BaostockDataManager().get_stock_name_by_code(code)
        if not name:
            QMessageBox.warning(self, "提示", "请输入正确的股票代码")
            return

        self.label_name.setText(str(name))

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
        bao_stock_data_manager = BaostockDataManager()

        # 从本地股票信息库同步获取“个股代码-名称”映射（不依赖后台日线缓存）
        dict_code_name = bao_stock_data_manager.get_all_stock_code_name_dict(code_column_name='code', name_column_name='name')
        if not dict_code_name:
            self.logger.warning("本地股票信息为空，无法随机加载")
            QMessageBox.warning(self, "提示", "本地暂无股票信息数据，请先下载股票列表")
            return

        # 随机选择一只股票
        code = random.choice(list(dict_code_name.keys()))
        name = dict_code_name[code]

        # 前复权远程数据仅约三年：日期限定在三年窗口内并预留指标预热区间
        date = self._get_random_review_date()

        print(f"随机股票代码: {code}, 对应名称: {name}，随机日期: {date}")
        period = self.comboBox_period.currentText()
        self.logger.info(f"点击随机加载数据: {code}, {date}, {period}")

        self.label_name.setText(str(name))
        self.lineEdit_code.blockSignals(True)
        self.lineEdit_code.setText(code)
        self.lineEdit_code.blockSignals(False)

        self.load_data(code, date)
        self.btn_buy.setDefault(True)

    def slot_btn_load_data_clicked(self):
        code = self.lineEdit_code.text()
        date = self.dateEdit.date().toString("yyyy-MM-dd")
        period = self.comboBox_period.currentText()
        self.logger.info(f"点击加载数据: {code}, {date}, {period}")

        self.load_data(code, date)
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
        amout = float(str_price) * int(str_count)
        self.lineEdit_amount.setText(f'{amout:.2f}')

    def slot_amout_button_group_buttonClicked(self, button):
        checked_id = self.amout_button_group.checkedId()
        str_price = self.lineEdit_price.text()
        if str_price == "":
            return
        
        max_count = self.demo_trading_manager.get_buy_count(float(str_price), checked_id)
        self.logger.info(f"最大可买数量: {max_count}")
        self.update_count_and_amount_labels(float(str_price), max_count)

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


