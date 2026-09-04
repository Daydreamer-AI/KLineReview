from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QFile

import pyqtgraph as pg
import numpy as np
import pandas as pd

from manager.logging_manager import get_logger

from gui.qt_widgets.MComponents.indicators.base_indicator_widget import BaseIndicatorWidget, signal_manager
from gui.qt_widgets.MComponents.indicators.kline_widget import KLineWidget
from gui.qt_widgets.MComponents.indicators.volume_widget import VolumeWidget
from gui.qt_widgets.MComponents.indicators.amount_widget import AmountWidget
from gui.qt_widgets.MComponents.indicators.macd_widget import MacdWidget
from gui.qt_widgets.MComponents.indicators.kdj_widget import KdjWidget
from gui.qt_widgets.MComponents.indicators.rsi_widget import RsiWidget
from gui.qt_widgets.MComponents.indicators.boll_widget import BollWidget

from gui.qt_widgets.MComponents.review.mloading_widget import LoadingWidget

from indicators import stock_data_indicators as sdi

from manager.period_manager import TimePeriod, ReviewPeriodProcessData
from processor.period_aggregator import period_start_key, aggregate_period

from manager.indicators_config_manager import get_indicator_config_manager, IndicatrosEnum

class IndicatorsViewWidget(QWidget):
    _shared_object_id = 0

    sig_current_animation_index_changed = pyqtSignal(int)
    sig_init_review_animation_finished = pyqtSignal(bool, object)
    sig_animation_play_finished = pyqtSignal()
    sig_period_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super(IndicatorsViewWidget, self).__init__(parent)
        uic.loadUi('./src/gui/qt_widgets/MComponents/indicators/IndicatorsViewWidget.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    # 清理资源
    def __del__(self):
        self.logger.info(f"开始清理类型{self.type}指标视图及其资源。当前共有{IndicatorsViewWidget._shared_object_id}个对象。")
        IndicatorsViewWidget._shared_object_id -= 1
        self.logger.info(f"清理后共有{IndicatorsViewWidget._shared_object_id}个对象。")

    def init_para(self):
        self.logger = get_logger(__name__)

        self.type = IndicatorsViewWidget._shared_object_id    # type    # 0：行情，1：策略，2：复盘
        IndicatorsViewWidget._shared_object_id += 1

        self.indicator_widgets = {} 
        self.kline_widget = None
        self.loading_widget = None

        # self.df_data列结构：
        # 日线级别：date, code, name, open, high, low, close, volume, amount, change_percent, turnover_rate, adjustflag, diff, dea, macd, ma5, ma10, ma20, ma24, ma30, ma52, ma60, volume_ratio
        # 周线及以上级别（无change_percent）：date, code, name, open, high, low, close, volume, amount, turnover_rate, adjustflag, diff, dea, macd, ma5, ma10, ma20, ma24, ma30, ma52, ma60, volume_ratio
        # 分钟级别（多time，无change_percent）：date, time, code, name, open, high, low, close, volume, amount, adjustflag, diff, dea, macd, ma5, ma10, ma20, ma24, ma30, ma52, ma60, volume_ratio
        self.df_data = None                 # pd.DataFrame

        self.current_selected_code = ""
        self.dict_stock_data = {}         # {TimePeriod: DataFrame}，只保存选中code的各个级别的k线数据


        # 复盘相关参数
        self._base_stock_data = {}        # {TimePeriod: DataFrame}，注入时的原始基周期数据，供切换时重建进行中bar
        self.animation_timer = QtCore.QTimer()
        self.animation_timer.timeout.connect(self.slot_animation_step)
        self.start_animation_index = 0
        self.current_animation_index = 0
        self.min_animation_index = 0
        self.max_animation_index = -1
        self.animation_speed = 1000  # 毫秒
        self.is_playing = False

        self.last_period_btn_checked_id = 7

        self.dict_period_process_data = {}  # {TimePeriod: ReviewPeriodProcessData}，保存周期切换时的状态
        self.min_period = TimePeriod.DAY    # 已切换成功的最小周期
        self.index_changed = False

    def init_ui(self):
        self.period_button_group = QtWidgets.QButtonGroup(self)
        self.period_button_group.addButton(self.btn_time)
        self.period_button_group.addButton(self.btn_1m, 0)
        self.period_button_group.addButton(self.btn_5m, 1)
        self.period_button_group.addButton(self.btn_10m, 2)
        self.period_button_group.addButton(self.btn_15m, 3)
        self.period_button_group.addButton(self.btn_30m, 4)
        self.period_button_group.addButton(self.btn_60m, 5)
        self.period_button_group.addButton(self.btn_120m, 6)
        self.period_button_group.addButton(self.btn_1d, 7)
        self.period_button_group.addButton(self.btn_1w, 8)
        self.period_button_group.addButton(self.btn_M, 9)
        self.period_button_group.addButton(self.btn_45m, 10)
        self.period_button_group.addButton(self.btn_90m, 11)

        self.btn_time.setEnabled(False)
        self.btn_1m.setEnabled(False)
        # 5/10/15/30/60/120 分钟默认禁用；复盘加载完成后由 set_period_buttons_enabled 按注入周期控制
        self.btn_5m.setEnabled(False)
        self.btn_10m.setEnabled(False)
        self.btn_15m.setEnabled(False)
        self.btn_30m.setEnabled(False)
        self.btn_45m.setEnabled(False)
        self.btn_60m.setEnabled(False)
        self.btn_90m.setEnabled(False)
        self.btn_120m.setEnabled(False)

        self.btn_1d.setEnabled(False)
        self.btn_1w.setEnabled(False)
        self.btn_M.setEnabled(False)

        self.btn_1d.setChecked(True)

        self.kline_widget = KLineWidget(self.df_data, self.type, self)
        self.verticalLayout.addWidget(self.kline_widget, 3)
        self.btn_indicator_ma.setChecked(True)
        self.kline_widget.show_ma()
        self.kline_widget.set_period(TimePeriod.DAY)
        self.kline_widget.set_period_text(self.tr("1D"))
        self.kline_widget.set_indicator_name(self.tr("MA"))

        # self.load_qss()

    def init_connect(self):
        self.period_button_group.buttonClicked.connect(self.slot_period_button_clicked)
        self.btn_indicator_volume.clicked.connect(self.slot_btn_indicator_volume_clicked)
        self.btn_indicator_amount.clicked.connect(self.slot_btn_indicator_amount_clicked)
        self.btn_indicator_macd.clicked.connect(self.slot_btn_indicator_macd_clicked)
        self.btn_indicator_kdj.clicked.connect(self.slot_btn_indicator_kdj_clicked)
        self.btn_indicator_rsi.clicked.connect(self.slot_btn_indicator_rsi_clicked)
        self.btn_indicator_boll.clicked.connect(self.slot_btn_indicator_boll_clicked)

        self.btn_indicator_ma.clicked.connect(self.slot_btn_indicator_ma_clicked)

        if self.kline_widget is not None:
            kline_plot_widget = self.kline_widget.get_plot_widget()
            if kline_plot_widget:
                # 注意和slot_mouse_moved处理的区别。每个视图的y轴坐标值不一致，所以需要子类重写单独处理。而鼠标移动时，可复用部分代码，所以放在父类中实现，同时抛出全局信号，让子类定制处理
                kline_plot_widget.sigRangeChanged.connect(self.slot_range_changed)
                kline_plot_widget.scene().sigMouseMoved.connect(self.kline_widget.slot_mouse_moved)
                # kline_plot_widget.scene().sigMouseMoved.connect(
                #     lambda pos, widget_source=self.kline_widget: self.slot_mouse_moved(pos, widget_source)
                # )

        self.btn_review.clicked.connect(self.slot_btn_review_clicked)

    def load_qss(self, theme="default"):
        qss_file_name = f":/theme/{theme}/mcomponents/mcomponents.qss"
        self.logger.info(f"样式表文件路径：{qss_file_name}")
        qssFile = QFile(qss_file_name)
        if qssFile.open(QFile.ReadOnly):
            self.setStyleSheet(str(qssFile.readAll(), encoding='utf-8'))
        else:
            self.logger.warning("无法打开自定义模块样式表文件")
        qssFile.close()

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

    def hide_loading(self):
        """隐藏Loading控件"""
        if self.loading_widget:
            self.loading_widget.hide_loading()
            self.loading_widget = None

    def resizeEvent(self, event):
        """窗口大小变化时重新定位Loading控件"""
        super().resizeEvent(event)
        if self.loading_widget:
            self.loading_widget.move(
                (self.width() - self.loading_widget.width()) // 2,
                (self.height() - self.loading_widget.height()) // 2
            )


    def show_period_frame(self, b_show=True):
        if b_show:
            self.frame_period.show()
        else:
            self.frame_period.hide()

    def show_review_btn(self, b_show=True):
        if b_show:
            self.btn_review.show()
        else:
            self.btn_review.hide()

    def enable_period_btn(self, b_enable=True):
        # checked_id = self.period_button_group.checkedId()
        for btn in self.period_button_group.buttons():
            if btn.isChecked():  # 忽略选中的按钮
                continue
            
            if self.period_button_group.id(btn) in [0]:  # 仅 1 分钟无数据源，保持禁用
                continue

            btn.setEnabled(b_enable)

    def get_current_date_time_by_index(self, index):
        if self.df_data is None or self.df_data.empty:  # 获取数据失败
            return None
        
        if index < 0 or index > len(self.df_data) - 1:  # 索引超出范围
            self.logger.info(f"索引超出范围，index: {index}, df的长度: {len(self.df_data)}")
            return None
        
        checked_id = self.period_button_group.checkedId()
        target_period_text = self.period_button_group.button(checked_id).text()
        target_period = TimePeriod.from_label(target_period_text)
        s_date_time_col = "time" if "time" in self.df_data.columns else "date"
        current_date_time = self.df_data[s_date_time_col].iloc[-1]
        return current_date_time
    
    def get_min_and_max_price_by_index(self, index):
        if self.df_data is None or self.df_data.empty:  # 获取数据失败
            return None
        
        if index < 0 or index > len(self.df_data) - 1:  # 索引超出范围
            self.logger.info(f"索引超出范围，index: {index}, df的长度: {len(self.df_data)}")
            return None
        
        min_price, max_price = self.df_data["low"].iloc[index], self.df_data["high"].iloc[index]
        return min_price, max_price
    
    def get_kline_price_by_index(self, index):
        if self.df_data is None or self.df_data.empty:  # 获取数据失败
            return None
        
        if index < 0 or index > len(self.df_data) - 1:  # 索引超出范围
            self.logger.info(f"索引超出范围，index: {index}, df的长度: {len(self.df_data)}")
            return None
        
        dict_return = {"low": self.df_data["low"].iloc[index],
                       "high": self.df_data["high"].iloc[index],
                       "open": self.df_data["open"].iloc[index],
                       "close": self.df_data["close"].iloc[index]
        }

        return dict_return

    def get_current_kline_data(self):
        """返回最后一条K线数据"""
        df_data = self.get_stock_data()
        if df_data.empty:
            return pd.DataFrame()
        
        return df_data.iloc[self.current_animation_index]

    def get_stock_data(self):
        checked_btn = self.period_button_group.checkedButton()
        if checked_btn is None:
            return pd.DataFrame()
        
        period_text = checked_btn.text()
        time_period = TimePeriod.from_label(period_text)

        if time_period not in self.dict_stock_data.keys():   # 暂无该级别数据
            return pd.DataFrame()
    
        return self.dict_stock_data[time_period]
    
    def get_stock_data_by_period(self, period):
        if period not in self.dict_stock_data.keys():   # 暂无该级别数据
            return pd.DataFrame()
    
        return self.dict_stock_data[period]

    def get_base_stock_data_by_period(self, period):
        """获取注入时的原始基周期数据（不含切换时重建的进行中 bar）"""
        return self._base_stock_data.get(period)



    def get_current_period(self):
        """返回当前选中的周期（TimePeriod），未选中时返回 None。"""
        checked_btn = self.period_button_group.checkedButton()
        if checked_btn is None:
            return None
        return TimePeriod.from_label(checked_btn.text())

    def set_stock_data(self, code, dict_stock_data):
        """
        外部注入股票各周期K线数据，本控件不再自行获取数据，只负责缓存维护。

        Args:
            code: 股票代码，如 'sh.600000'
            dict_stock_data: {TimePeriod: DataFrame}，各周期K线数据（建议含指标列，
                             列结构参考 init_para 中的注释）
        """
        if code != self.current_selected_code:
            self.logger.info(f"切换股票：{self.current_selected_code} -> {code}")
            self.dict_stock_data = {}
            self._base_stock_data = {}
            self.current_selected_code = code

        if not dict_stock_data:
            self.logger.warning(f"外部注入的{code}数据为空，跳过缓存更新")
            return

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        valid_dict = {}
        for period, df in dict_stock_data.items():
            if df is None or df.empty:
                self.logger.warning(f"{code}的{TimePeriod.get_chinese_label(period)}数据为空，跳过")
                continue
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                self.logger.warning(f"{code}的{TimePeriod.get_chinese_label(period)}数据缺少列：{missing_cols}，可能导致绘图异常")
            valid_dict[period] = df

        if not valid_dict:
            self.logger.warning(f"{code}的各周期数据均为空，缓存未更新")
            return

        self.dict_stock_data.update(valid_dict)
        self._base_stock_data.update({period: df.copy() for period, df in valid_dict.items()})
        periods_text = [TimePeriod.get_chinese_label(period) for period in valid_dict.keys()]
        self.logger.info(f"已注入{code}的{len(valid_dict)}个周期数据：{periods_text}")

    def show_default_indicator(self):
        self.btn_indicator_volume.setChecked(True)
        self.slot_btn_indicator_volume_clicked()

        self.btn_indicator_macd.setChecked(True)
        self.slot_btn_indicator_macd_clicked()

    def clear_chart(self):
        # TODO: 待完善
        pass

    def update_chart(self, data, start_index=None):
        code = data['code']
        if code != self.current_selected_code or not self.dict_stock_data:
            self.logger.warning(f"未找到{code}的外部注入数据，请先调用 set_stock_data(code, dict_stock_data) 注入数据")
            return
        self.kline_widget.set_stock_name(data['name'])

        df = self.get_stock_data()
        if df is None or df.empty:
            checked_btn = self.period_button_group.checkedButton()
            period_text = checked_btn.text() if checked_btn else "未知"
            self.logger.warning(f"{code}的当前周期[{period_text}]数据未注入，无法更新图表")
            return

        if start_index is not None and start_index != "":  # 获取数据成功
            # 若当前周期含进行中 bar，先按目标位置同步（前进后未走完 bar 自动走完）
            self._sync_partial_bar_for_position(start_index)
            df = self.get_stock_data()
            if df is None or df.empty:
                return
            # self.logger.info(f"df的长度: {len(df)}")
            # if self.max_animation_index == -1:
            #     self.max_animation_index = len(df) - 1

            if start_index < 0 or start_index > len(df) - 1:  # 索引超出范围
                # self.logger.info(f"索引超出范围，start_index: {start_index}, df的长度: {len(df)}")
                return

            # 边界检查
            start_index = max(0, min(start_index, len(df) - 1))
            # 获取指定索引前（包含指定索引）的数据
            self.df_data = df.iloc[:start_index+1]
            # self.logger.info(f"self.df_data的长度: {len(self.df_data)}\n{self.df_data.tail(1)}")
            
            # 设置当前动画索引为start_index
            self.current_animation_index = start_index
            checked_id = self.period_button_group.checkedId()
            target_period_text = self.period_button_group.button(checked_id).text()
            target_period = TimePeriod.from_label(target_period_text)
            self.dict_period_process_data[target_period].current_index = start_index
            s_date_time_col = "time" if "time" in self.df_data.columns else "date"
            self.dict_period_process_data[target_period].current_date_time = self.df_data[s_date_time_col].iloc[-1]

            if start_index != self.current_animation_index:
                self.index_changed = True
            else:
                self.index_changed = False

            self.sig_current_animation_index_changed.emit(self.current_animation_index)

            # self.logger.info(f"获取{code}的索引{start_index}数据成功")
        else:
            self.df_data = df

        if self.df_data is None or self.df_data.empty:  # 获取数据失败
            return

        # if self.kline_widget is None:
        #     self.kline_widget = KLineWidget(self.df_data, self)
        #     self.verticalLayout.addWidget(self.kline_widget, 3)
        #     self.btn_indicator_ma.setChecked(True)
        #     self.kline_widget.show_ma()

        #     kline_plot_widget = self.kline_widget.get_plot_widget()
        #     if kline_plot_widget:
        #         kline_plot_widget.sigRangeChanged.connect(self.slot_range_changed)
        
        self.kline_widget.update_data(self.df_data)

        is_ma_checked = self.btn_indicator_ma.isChecked()
        self.kline_widget.show_ma(is_ma_checked)

        self.update_indicator_chart(self.df_data)

        #if start_date is None or start_date == "":
        self.kline_widget.auto_scale_to_latest(120)

        # 更新最后一根k线指标值

    def _sync_partial_bar_for_position(self, index):
        """当前周期数据若含进行中 bar，按目标索引代表的复盘位置重新构建（前进后自动走完）。

        复盘动画在周期内前进时，未走完的 bar（如盘中当日、周中当周、进行中分钟槽）
        应随位置前进自动补全；以目标索引 bar 的 as_of 时刻重建当前周期数据，
        随后 update_chart 用重建后的数据重新截断。
        """
        if self.property("review") is None:
            return
        period = self.get_current_period()
        df = self.get_stock_data()
        if df is None or df.empty:
            return
        if 'is_complete' not in df.columns or bool(df['is_complete'].all()):
            return
        if index < 0 or index >= len(df):
            return
        if 'time' in df.columns:
            as_of = df['time'].iloc[index]
        else:
            as_of = df['date'].iloc[index]
        self._refresh_derived_period_data(period, as_of)

    def update_indicator_chart(self, df_data):
        is_volume_checked = self.btn_indicator_volume.isChecked()
        if is_volume_checked:
            volume_widget = self.indicator_widgets[IndicatrosEnum.get_label(IndicatrosEnum.VOLUME)]
            if volume_widget is None:
                self.btn_indicator_volume.setChecked(False)
            else:
                volume_widget.update_data(df_data)
            

        is_amount_checked = self.btn_indicator_amount.isChecked()
        if is_amount_checked:
            amount_widget = self.indicator_widgets[IndicatrosEnum.get_label(IndicatrosEnum.AMOUNT)]
            if amount_widget is None:
                self.btn_indicator_amount.setChecked(False)
            else:
                amount_widget.update_data(df_data)

        is_macd_checked = self.btn_indicator_macd.isChecked()
        if is_macd_checked:
            macd_widget = self.indicator_widgets[IndicatrosEnum.get_label(IndicatrosEnum.MACD)]
            if macd_widget is None:
                self.btn_indicator_macd.setChecked(False)
            else:
                macd_widget.update_data(df_data)

        is_kdj_checked = self.btn_indicator_kdj.isChecked()
        if is_kdj_checked:
            kdj_widget = self.indicator_widgets[IndicatrosEnum.get_label(IndicatrosEnum.KDJ)]
            if kdj_widget is None:
                self.btn_indicator_kdj.setChecked(False)
            else:
                kdj_widget.update_data(df_data)

        is_rsi_checked = self.btn_indicator_rsi.isChecked()
        if is_rsi_checked:
            rsi_widget = self.indicator_widgets[IndicatrosEnum.get_label(IndicatrosEnum.RSI)]
            if rsi_widget is None:
                self.btn_indicator_rsi.setChecked(False)
            else:
                rsi_widget.update_data(df_data)

        is_boll_checked = self.btn_indicator_boll.isChecked()
        if is_boll_checked:
            boll_widget = self.indicator_widgets[IndicatrosEnum.get_label(IndicatrosEnum.BOLL)]
            if boll_widget is None:
                self.btn_indicator_boll.setChecked(False)
            else:
                boll_widget.update_data(df_data)


    def draw_volume(self):
        widget = VolumeWidget(self.df_data, self.type, self)
        return widget

    def draw_amount(self):
        widget = AmountWidget(self.df_data, self.type, self)
        return widget

    def draw_macd(self):
        widget = MacdWidget(self.df_data, self.type, self)
        return widget

    def draw_kdj(self):
        # 因源数据中没有自带KDJ指标，需要手动计算
        if IndicatrosEnum.KDJ_K.value not in self.df_data.columns or IndicatrosEnum.KDJ_D.value not in self.df_data.columns or IndicatrosEnum.KDJ_J.value not in self.df_data.columns:
            sdi.kdj(self.df_data) 

        widget = KdjWidget(self.df_data, self.type, self)
        return widget

    def draw_rsi(self):
        # 因源数据中没有自带RSI指标，需要手动计算
        rsi_columns = get_indicator_config_manager().get_user_config_columns_by_indicator_type(IndicatrosEnum.RSI.value)
        missing_rsi = [col for col in rsi_columns if col not in self.df_data.columns]
        if missing_rsi:
            sdi.rsi(self.df_data, period=6)   # 计算RSI6
            sdi.rsi(self.df_data, period=12)  # 计算RSI12
            sdi.rsi(self.df_data, period=24)  # 计算RSI24

        widget = RsiWidget(self.df_data, self.type, self)
        return widget

    def draw_boll(self):
        # 因源数据中没有自带BOLL指标，需要手动计算
        boll_columns = [IndicatrosEnum.BOLL_UPPER.value, IndicatrosEnum.BOLL_MID.value, IndicatrosEnum.BOLL_LOWER.value]
        missing_boll = [col for col in boll_columns if col not in self.df_data.columns]
        if missing_boll:
            sdi.boll(self.df_data)

        widget = BollWidget(self.df_data, self.type, self)
        return widget

    def add_indicator_chart(self, indicator_name):
        '''
            动态添加指标图
        '''
        if self.df_data is None or self.df_data.empty:
            self.logger.warning(f"数据为空，无法添加指标图：{indicator_name}")
            return None
        
        # 先检查是否支持该指标
        supported_indicators = [IndicatrosEnum.get_label(IndicatrosEnum.VOLUME), IndicatrosEnum.get_label(IndicatrosEnum.AMOUNT), IndicatrosEnum.get_label(IndicatrosEnum.MACD), IndicatrosEnum.get_label(IndicatrosEnum.KDJ), IndicatrosEnum.get_label(IndicatrosEnum.RSI), IndicatrosEnum.get_label(IndicatrosEnum.BOLL)]
        if indicator_name not in supported_indicators:
            self.logger.warning(f"不支持的指标：{indicator_name}")
            return None
        
        # 检查是否已经添加了该指标
        if indicator_name in self.indicator_widgets:
            self.logger.info(f"指标 {indicator_name} 已经存在")
            return self.indicator_widgets[indicator_name]

        indicator_widget = None
        if indicator_name == IndicatrosEnum.get_label(IndicatrosEnum.VOLUME):
            indicator_widget = self.draw_volume()
        elif indicator_name == IndicatrosEnum.get_label(IndicatrosEnum.AMOUNT):
            indicator_widget = self.draw_amount()
        elif indicator_name == IndicatrosEnum.get_label(IndicatrosEnum.MACD):
            indicator_widget = self.draw_macd()
        elif indicator_name == IndicatrosEnum.get_label(IndicatrosEnum.KDJ):
            indicator_widget = self.draw_kdj()
        elif indicator_name == IndicatrosEnum.get_label(IndicatrosEnum.RSI):
            indicator_widget = self.draw_rsi()
        elif indicator_name == IndicatrosEnum.get_label(IndicatrosEnum.BOLL):
            indicator_widget = self.draw_boll()
        else:
            self.logger.warning(f"不支持的指标：{indicator_name}")

        # 检查是否成功创建了widget
        if indicator_widget is None:
            self.logger.warning(f"无法创建指标 {indicator_name} 的图表")
            return None

         # 设置图表属性以保持一致性
        if hasattr(indicator_widget, 'get_plot_widget'):
            plot_widget = indicator_widget.get_plot_widget()
            if plot_widget:
                plot_widget.getAxis('left').setWidth(60)
                kline_plot_widget = self.kline_widget.get_plot_widget()
                if kline_plot_widget:
                    plot_widget.setXLink(kline_plot_widget)
                    kline_plot_widget.setXLink(plot_widget)
        
        if indicator_name == IndicatrosEnum.get_label(IndicatrosEnum.VOLUME):
            # 成交量指标图固定在k线图下方
            # 找到K线图在布局中的索引位置
            kline_index = self.verticalLayout.indexOf(self.kline_widget)
            # 在K线图后面插入成交量图（即K线图下方）
            if kline_index != -1:
                self.verticalLayout.insertWidget(kline_index + 1, indicator_widget, 1)
            else:
                # 如果没找到K线图，添加到末尾
                self.verticalLayout.addWidget(indicator_widget, 1)
        else:
            self.verticalLayout.addWidget(indicator_widget, 1)

        # 缩放同步和鼠标移动
        plot_widget = indicator_widget.get_plot_widget()
        if plot_widget:
            plot_widget.sigRangeChanged.connect(self.slot_range_changed)
            plot_widget.scene().sigMouseMoved.connect(indicator_widget.slot_mouse_moved)
            # plot_widget.scene().sigMouseMoved.connect(
            #     lambda pos, widget_source=indicator_widget: self.slot_mouse_moved(pos, widget_source)
            # )

        # 保存图表引用
        self.indicator_widgets[indicator_name] = indicator_widget
        return indicator_widget

    def remove_indicator_chart(self, indicator_name):
        '''
            移除动态添加的指标图
        '''
        # 检查指标是否存在
        if indicator_name not in self.indicator_widgets:
            self.logger.warning(f"指标 {indicator_name} 不存在")
            return False

        # 获取要移除的widget
        widget = self.indicator_widgets[indicator_name]
        
        # 从布局中移除
        self.verticalLayout.removeWidget(widget)
        
        # 隐藏并删除widget
        widget.setParent(None)
        widget.deleteLater()
        
        # 从字典中移除引用
        del self.indicator_widgets[indicator_name]
        
        self.logger.info(f"成功移除指标 {indicator_name}")
        return True

    def remove_all_indicator_charts(self):
        '''
            移除所有动态添加的指标图
        '''
        # 创建指标名称列表的副本，因为我们在迭代过程中会修改原字典
        indicator_names = list(self.indicator_widgets.keys())
        
        for indicator_name in indicator_names:
            self.remove_indicator_chart(indicator_name)
        
        self.logger.info("成功移除所有指标图表")

    def set_period(self, period):
        self.kline_widget.set_period(period)
        for indicator_name, widget in self.indicator_widgets.items():
            widget.set_period(period)

    def set_current_period(self, period):
        """外部指定当前展示周期（如复盘数据加载完成后同步周期按钮/图表），不触发 slot_period_button_clicked 的切换逻辑"""
        for btn in self.period_button_group.buttons():
            if self.period_button_group.id(btn) < 0:  # btn_time（分时）不作为周期切换目标
                continue
            if TimePeriod.from_label(btn.text()) == period:
                btn.setChecked(True)
                self.last_period_btn_checked_id = self.period_button_group.id(btn)
                self.set_period(period)
                self.kline_widget.set_period_text(btn.text())
                return True
        self.logger.warning(f"未找到周期 {TimePeriod.get_chinese_label(period)} 对应的周期按钮")
        return False

    def set_period_buttons_enabled(self, periods=None):
        """按周期列表启用/禁用切换按钮（不触碰分时按钮）。

        复盘数据后台加载期间调用 set_period_buttons_enabled([]) 全部禁用；
        加载完成同步后传入已加载周期列表，仅启用对应按钮。
        """
        enabled_periods = set(periods) if periods else set()
        for btn in self.period_button_group.buttons():
            if self.period_button_group.id(btn) < 0:  # btn_time
                continue
            btn.setEnabled(TimePeriod.from_label(btn.text()) in enabled_periods)

    def get_time_intervals_for_period(self, period):
        """
        根据周期返回对应的时间区间列表
        返回: [(start_time, end_time), ...] 格式的列表
        分钟级按 A 股两段交易时段（09:30-11:30、13:00-15:00）按周期分钟数切槽，
        与聚合器共用同一时段规则；非分钟级返回空列表。
        """
        if not TimePeriod.is_minute_level(period):
            return []
        minutes = int(TimePeriod.get_number_label(period))
        from processor.period_aggregator import get_minute_slot_intervals
        return get_minute_slot_intervals(minutes)

    def add_minutes(self, time_obj, minutes):
        """给time对象加上指定分钟数"""
        dummy_date = pd.Timestamp("2020-01-01")
        datetime_obj = pd.Timestamp.combine(dummy_date, time_obj)
        new_datetime = datetime_obj + pd.Timedelta(minutes=minutes)
        return new_datetime.time()

    def get_target_index(self, last_checked_id, target_checked_id):
        last_period_text = self.period_button_group.button(last_checked_id).text()
        last_period = TimePeriod.from_label(last_period_text)

        target_period_text = self.period_button_group.button(target_checked_id).text()
        target_period = TimePeriod.from_label(target_period_text)

        if TimePeriod.is_minute_level(last_period) and TimePeriod.is_minute_level(target_period):
            current_time = self.df_data.iloc[self.current_animation_index]['time']
            # 将current_time转换为datetime对象
            if isinstance(current_time, str):
                current_time = pd.to_datetime(current_time)
            
            # 根据目标周期确定时间区间
            target_time_intervals = self.get_time_intervals_for_period(last_period)
            
            # 查找current_time在哪个时间区间内
            for i, (start_time, end_time) in enumerate(target_time_intervals):
                # 构造完整的日期时间用于比较
                current_date = current_time.date()
                interval_start = pd.Timestamp.combine(current_date, start_time)
                interval_end = pd.Timestamp.combine(current_date, end_time)
                
                if interval_start <= current_time <= interval_end:
                    return i
        
        return -1
    
    def get_min_process_data_period(self):
        """
        获取已存在的最小周期
        """
        if not self.dict_period_process_data:
            return None
        
    
        # 定义周期优先级顺序
        period_order = TimePeriod.get_period_list()
        
        # 获取存在的周期集合
        existing_periods = set(self.dict_period_process_data.keys())
        
        # 按照优先级顺序查找第一个存在的周期
        for period in period_order:
            if period in existing_periods:
                return period
        
        return None
    
    def get_min_process_data_period_current_time(self):
        """
        获取已存在最小周期的当前索引的time
        """
        if not self.dict_period_process_data:
            return None
        
        s_min_time = ""
        for period, process_data in self.dict_period_process_data.items():
            if TimePeriod.is_minute_level(period):
                df = self.get_stock_data_by_period(period)
                index = self.dict_period_process_data[period].current_index
                time = df.iloc[index]['time']
                if not s_min_time or time < s_min_time:
                    s_min_time = time
        return s_min_time

    def get_target_index_auto(self, last_period, target_period):
        # 核心逻辑：
        # 第一次切换目标周期时，根据当前self.dict_period_process_data存储的最小周期的当前索引，确定目标周期的索引
        min_period_chinese_text = TimePeriod.get_chinese_label(self.min_period)
        last_period_chinese_text = TimePeriod.get_chinese_label(last_period)
        target_period_chinese_text = TimePeriod.get_chinese_label(target_period)
        self.logger.info(f"已切换成功的最小周期：{min_period_chinese_text}，来源周期：{last_period_chinese_text}，目标周期：{target_period_chinese_text}")
        current_time = self.dict_period_process_data[last_period].current_date_time
        self.logger.info(f"来源周期的current_time：{current_time}")
        if target_period not in self.dict_period_process_data:
            if TimePeriod.is_minute_level(target_period):
                return self.get_target_index_by_time(current_time, target_period)
                
            return -1
        
        if TimePeriod.is_minute_level(self.min_period) and TimePeriod.is_minute_level(target_period):
            # 最小周期当前索引的time。问题：已加载15、30、60分钟数据时，15切30,30分钟级别能前进，切换15分钟还是未前进的时间。
            # df = self.get_stock_data_by_period(self.min_period)
            # index = self.dict_period_process_data[self.min_period].current_index
            # current_time = df.iloc[index]['time']
            # self.logger.info(f"已切换成功的最小周期当前索引的time：{current_time}")

            # 这里应该得到所有分钟级索引数据的最小time。问题：当已加载15、30、60分钟数据时，30切60，再切15分钟前进，30、60分钟数据不会同步。
            # current_time = self.get_min_process_data_period_current_time()
            # self.logger.info(f"已切换成功的周期当前索引最小的time：{current_time}，所属周期：{min_period_chinese_text}")

            # 这里应该得到来源周期的current_time，将据此得到目标周期的start_time。
            # 问题：会自动跳整顿。例如：当已加载15、30、60分钟时，15分钟前进到xx:15, xx:45时，此时切30、60分钟，会自动跳到对应整点（xx:15-xx:30, xx:45-xx:00), 再切换15分钟时，同样会自动跳整点（这应该是正常的）
            # 处理：last_period索引没有变化时，自动切换到target_period的start_time
            # current_time = self.dict_period_process_data[last_period].current_date_time
            b_check = self.dict_period_process_data[last_period].current_index == self.dict_period_process_data[last_period].current_start_index
            b_check_2 = True    # self.dict_period_process_data[target_period].current_index == self.dict_period_process_data[target_period].current_start_index
            if TimePeriod.is_minute_level(last_period):
                self.logger.info(f"来源周期是分钟级别，来源周期当前时间：{self.dict_period_process_data[last_period].current_date_time}， 目标周期当前时间：{self.dict_period_process_data[target_period].current_date_time}")
                # b_check_2 = self.dict_period_process_data[last_period].current_date_time <= self.dict_period_process_data[target_period].current_date_time
                # TODO: 分钟级别跨周期切换时的优化
                if last_period < target_period:
                    # 小周期切大周期
                    b_check_2 = self.dict_period_process_data[last_period].current_date_time <= self.dict_period_process_data[target_period].current_date_time
                else:
                    # 大周期切小周期
                    b_check_2 = self.dict_period_process_data[last_period].current_date_time >= self.dict_period_process_data[target_period].current_date_time

                self.logger.info(f"b_check_2: {b_check_2}")

            if b_check and b_check_2:
                self.logger.info(f"来源周期last_period索引没有变化，自动切换到目标周期target_period的上次索引时间")
                current_time = self.dict_period_process_data[target_period].current_date_time

            self.logger.info(f"更新后的current_time：{current_time}")

            return self.get_target_index_by_time(current_time, target_period)

        return -1
    
    def is_period_process_data_index_changed(self):
        for period, process_data in self.dict_period_process_data.items():
            if self.dict_period_process_data[period].current_index != self.dict_period_process_data[period].current_start_index:
                return True
            
        return False
    
    def get_target_index_by_time(self, current_time, target_period):
        # 将current_time转换为datetime对象
        if isinstance(current_time, str):
            current_time = pd.to_datetime(current_time)

        # 根据目标周期确定时间区间
        target_time_intervals = self.get_time_intervals_for_period(target_period)

        # 查找current_time在哪个时间区间内
        for i, (start_time, end_time) in enumerate(target_time_intervals):
            # 构造完整的日期时间用于比较
            current_date = current_time.date()
            interval_start = pd.Timestamp.combine(current_date, start_time)
            interval_end = pd.Timestamp.combine(current_date, end_time)
            
            if interval_start <= current_time <= interval_end:
                return i
            
        return -1

    def _get_anchor_matching_indices(self, df, period, as_of):
        """通用锚定匹配：返回目标周期中“周期开始时刻 <= as_of”的 bar 位置列表。

        日线及以上：周期开始由 bar 日期推导（周=周一、月=1 日、日=当日），
        进行中（未走完）的 bar 周期开始时刻早于 as_of，也会被匹配到；
        分钟级：限定 as_of 当日，匹配“bar 开始时刻 <= as_of”的 bar
        （当前分钟级获取暂屏蔽，保留原按日定位语义作为扩展预留）。
        """
        if df is None or df.empty:
            return []
        if TimePeriod.is_minute_level(period):
            if 'time' not in df.columns:
                return []
            dates = pd.to_datetime(df['date'])
            times = pd.to_datetime(
                df['date'].astype(str) + ' ' + df['time'].astype(str).str[-8:], errors='coerce')
            starts = [period_start_key(period, t) for t in times]
            return [
                i for i, (d, s) in enumerate(zip(dates, starts))
                # 分钟 bar 区间为 [start, end)：as_of 恰为某根 bar 起始时刻时属于上一根 bar
                if pd.notna(s) and d.date() == as_of.date() and s < as_of
            ]
        dates = pd.to_datetime(df['date'])
        starts = [period_start_key(period, d) for d in dates]
        return [i for i, s in enumerate(starts) if s <= as_of]

    def _refresh_derived_period_data(self, period, as_of):
        """周期切换前按当前复盘位置重新生成上级周期数据（上级周期由基周期本地聚合）。

        复盘动画前进后，进行中周期（如当周）的 bar 随复盘位置变化，切换前需重新聚合，
        否则会锚定到加载时刻生成的部分周期 bar，或把未走完的周期显示为完整周期。
        """
        as_of = pd.Timestamp(as_of)
        if period == TimePeriod.DAY:
            day_df = self._build_partial_day_df(as_of)
            if day_df is not None:
                self.dict_stock_data[TimePeriod.DAY] = day_df
            return
        if TimePeriod.is_minute_level(period):
            minute_bases = [
                p for p in self.dict_stock_data
                if TimePeriod.is_minute_level(p) and p < period
            ]
            if not minute_bases:
                return
            base_period = min(minute_bases)
            base_df = self._base_stock_data.get(base_period)
            if base_df is None:
                base_df = self.dict_stock_data.get(base_period)
        else:
            # 周/月等：以“进行中当日”为基聚合（as_of 带时间时当日为盘中形态，否则为完整日线）
            base_df = self._build_partial_day_df(as_of)
        if base_df is None or base_df.empty:
            return
        try:
            derived_df = aggregate_period(base_df, period, as_of=as_of)
        except Exception as e:
            self.logger.error(f"周期{TimePeriod.get_chinese_label(period)}切换前聚合失败: {e}")
            return
        if derived_df is not None and not derived_df.empty:
            self.dict_stock_data[period] = derived_df

    def _build_partial_day_df(self, as_of):
        """构建日线展示数据：完整日线 + 盘中 as_of 时把当日 bar 重建为进行中形态。

        返回的日线 DataFrame 带 time 列（完整日为 'YYYY-MM-DD 15:00:00'，进行中当日为 as_of），
        便于从日线再切回分钟级时沿用盘中时间；周/月聚合也以该数据为基，保证未走完当日不泄漏。
        """
        base_day = self._base_stock_data.get(TimePeriod.DAY)
        if base_day is None:
            base_day = self.dict_stock_data.get(TimePeriod.DAY)
        if base_day is None or base_day.empty:
            return None
        as_of = pd.Timestamp(as_of)
        day_df = base_day.copy()
        if 'time' not in day_df.columns:
            day_df['time'] = pd.to_datetime(day_df['date']).dt.strftime('%Y-%m-%d') + ' 15:00:00'
        day_df['is_complete'] = True
        if as_of.time() == pd.Timestamp('00:00:00').time():
            return day_df
        minute_bases = [p for p in self.dict_stock_data if TimePeriod.is_minute_level(p)]
        if not minute_bases:
            return day_df
        minute_base = self._base_stock_data.get(min(minute_bases))
        if minute_base is None:
            minute_base = self.dict_stock_data.get(min(minute_bases))
        if minute_base is None or minute_base.empty:
            return day_df
        mdates = pd.to_datetime(minute_base['date'])
        mtimes = pd.to_datetime(
            minute_base['date'].astype(str) + ' ' + minute_base['time'].astype(str).str[-8:], errors='coerce')
        day_mask = mdates.dt.date == as_of.date()
        sub = minute_base[day_mask & (mtimes <= as_of)]
        if sub.empty:
            return day_df
        target_idx = day_df.index[pd.to_datetime(day_df['date']).dt.date == as_of.date()]
        if len(target_idx) == 0:
            return day_df
        idx = target_idx[0]
        day_df.loc[idx, 'open'] = sub['open'].iloc[0]
        day_df.loc[idx, 'high'] = sub['high'].max()
        day_df.loc[idx, 'low'] = sub['low'].min()
        day_df.loc[idx, 'close'] = sub['close'].iloc[-1]
        day_df.loc[idx, 'volume'] = sub['volume'].sum()
        if 'amount' in sub.columns and 'amount' in day_df.columns:
            day_df.loc[idx, 'amount'] = sub['amount'].sum()
        if 'turnover_rate' in sub.columns and 'turnover_rate' in day_df.columns:
            day_df.loc[idx, 'turnover_rate'] = sub['turnover_rate'].sum()
        day_df.loc[idx, 'time'] = as_of.strftime('%Y-%m-%d %H:%M:%S')
        last_time = mtimes[day_mask].max()
        day_df.loc[idx, 'is_complete'] = bool(pd.notna(last_time) and as_of >= last_time)
        # 重算指标与涨跌幅（以进行中 close 为准，as-of 语义）
        if 'change_percent' in day_df.columns:
            day_df = day_df.drop(columns=['change_percent'])
        sdi.default_indicators_auto_calculate(day_df)
        return day_df

    # -----------------------复盘回放相关接口----------------------
    def init_animation(self, data, start_date, b_init=True):
        dict_return = {}
        code = data['code']
        self.logger.info(f"初始化动画：{code}, 日期：{start_date}")
        if code != self.current_selected_code or not self.dict_stock_data:
            self.logger.warning(f"未找到{code}的外部注入数据，请先调用 set_stock_data(code, dict_stock_data) 注入数据")
            self.sig_init_review_animation_finished.emit(False, dict_return)
            return dict_return
        df = self.get_stock_data()

        if df is None or df.empty:
            self.logger.warning(f"数据为空，无法初始化动画：{code}")
            self.sig_init_review_animation_finished.emit(False, dict_return)
            return dict_return
        
        if start_date is not None and start_date != "":
            self.min_animation_index = 0
            self.max_animation_index = len(df) - 1

            checked_id = self.period_button_group.checkedId()
            last_period_text = self.period_button_group.button(self.last_period_btn_checked_id).text()
            last_period = TimePeriod.from_label(last_period_text)

            target_period_text = self.period_button_group.button(checked_id).text()
            target_period = TimePeriod.from_label(target_period_text)
            current_period_date_col = 'time' if TimePeriod.is_minute_level(last_period) else 'date'

            # 统一锚定：以复盘基准时刻 as_of 为准，匹配“周期开始时刻 <= as_of”的 bar。
            # 上级周期包含进行中（未走完）bar：周中复盘时当周 bar 由基周期聚合生成，
            # 其周期开始（如周一）<= as_of 即应被选中，不再使用 date < start_date 跳过当周。
            as_of = pd.Timestamp(start_date)
            last_process = self.dict_period_process_data.get(last_period)
            source_has_time = (
                last_process is not None
                and last_process.current_date_time
                and ' ' in str(last_process.current_date_time)
            )
            if source_has_time:
                # 分钟级来源或日线进行中当日：沿用当前精确时间
                try:
                    as_of = pd.to_datetime(last_process.current_date_time)
                except (ValueError, TypeError):
                    pass
            elif TimePeriod.is_minute_level(target_period):
                # 非分钟级来源或初始加载切分钟级：以当日收盘时刻定位（进行中分钟数据由基周期聚合）
                as_of = pd.Timestamp(start_date) + pd.Timedelta(hours=15)
            matching_indices = self._get_anchor_matching_indices(df, target_period, as_of)
            # 初始加载时目标数据未覆盖 as_of（如分钟数据源仅保留当年，复盘日期早于分钟数据起点）：
            # 回退到数据起始位置保证出图；周期切换场景由 slot 回退到来源周期，避免复盘位置漂移
            if b_init and not matching_indices and df is not None and not df.empty:
                self.logger.warning(
                    f"周期{TimePeriod.get_chinese_label(target_period)}在 as_of={start_date} 无匹配数据，回退到数据起始位置")
                matching_indices = [0]

            if b_init:
                if len(matching_indices) > 0:
                        # 普通处理
                        self.logger.info(f"动画初始化--找到 {len(matching_indices)} 个匹配的日期记录")
                        self.start_animation_index = matching_indices[-1]
                        self.logger.info(f"start_date索引: {self.start_animation_index}")

                        review_period_process_data = ReviewPeriodProcessData()
                        review_period_process_data.current_period = target_period
                        review_period_process_data.current_start_date_time = df['date'].iloc[self.start_animation_index]
                        review_period_process_data.current_min_index = 0
                        review_period_process_data.current_max_index = self.max_animation_index
                        review_period_process_data.current_index = self.start_animation_index
                        review_period_process_data.current_start_index = self.start_animation_index
                        self.dict_period_process_data[target_period] = review_period_process_data

                        self.update_chart(data, self.start_animation_index)
                        dict_return = {
                            "start_date_index": self.start_animation_index,
                            "min_index": self.min_animation_index,
                            "max_index": self.max_animation_index,
                            "start_date": review_period_process_data.current_start_date_time
                        }

                        self.last_period_btn_checked_id = checked_id
                        self.min_period = target_period
                else:
                    self.logger.warning(f"普通处理--未找到匹配的日期记录：{start_date}")
            else:

                matching_indices_len = len(matching_indices)
                self.logger.info(f"切换--找到 {matching_indices_len} 个匹配的日期记录")

                if matching_indices_len > 0:
                    # 周期切换步骤。来源周期，目标周期
                    # 目标周期是否第一次切换？
                    # 第一次切换默认到最后索引
                    # 不是第一次切换则判断来源周期索引是否发生变化
                    # 有发生变化则更新目标周期索引，没有发生变化则自动切换到目标周期索引
                    s_last_period_text = TimePeriod.get_chinese_label(last_period)
                    s_target_period_text = TimePeriod.get_chinese_label(target_period)
                    self.logger.info(f"周期切换--来源周期：{s_last_period_text}，目标周期：{s_target_period_text}")
                    
                    self.logger.info(f"来源周期当前索引：{self.current_animation_index}，开始索引：{self.start_animation_index}")
                    
                    last_current_index = self.dict_period_process_data[last_period].current_index
                    last_start_index = self.dict_period_process_data[last_period].current_start_index
                    self.logger.info(f"来源周期[{s_last_period_text}]索引：{last_current_index}，日期：{self.dict_period_process_data[last_period].current_date_time}，来源周期[{s_last_period_text}]开始索引：{last_start_index}, 开始日期：{self.dict_period_process_data[last_period].current_start_date_time}")
                    
                    # 统一取“周期开始时刻 <= as_of”的最后一根 bar（进行中 bar 也包含）
                    index = -1
                    self.logger.info(f"目标周期索引：{index}")
                    self.start_animation_index = matching_indices[index]
                    if target_period not in self.dict_period_process_data:
                        # 第1次切换，默认到最后索引
                        self.logger.info(f"第1次切换")
                        # index = self.get_target_index_auto(last_period, target_period)
                        # self.start_animation_index = matching_indices[index]
                    else:
                        target_current_index = self.dict_period_process_data[target_period].current_index
                        target_start_index = self.dict_period_process_data[target_period].current_start_index
                        self.logger.info(f"上次目标周期[{s_target_period_text}]索引：{target_current_index}，日期：{self.dict_period_process_data[target_period].current_date_time}，上次目标周期[{s_target_period_text}]开始索引：{target_start_index}，日期：{self.dict_period_process_data[target_period].current_start_date_time}")
                        # b_check = self.current_animation_index == self.dict_period_process_data[last_period].current_start_index
                        # b_check_2 = start_date == self.dict_period_process_data[last_period].current_start_date_time
                        # b_check_3 = start_date == self.dict_period_process_data[target_period].current_start_date_time
                        # b_check_4 = not self.is_period_process_data_index_changed()
                        # if b_check and b_check_2 and b_check_3 and b_check_4:
                        #     # 来源周期索引没有发生变化，则自动切换到目标周期索引
                        #     self.logger.info(f"自动切换到目标周期[{s_target_period_text}]索引")
                        #     self.start_animation_index = self.dict_period_process_data[target_period].current_index
                        # else:
                            # 来源周期索引有发生变化，则更新周期索引
                            # if not TimePeriod.is_minute_level(last_period):
                            #     index = -1
                            # else:
                            # index = self.get_target_index_auto(last_period, target_period)
                            # self.start_animation_index = matching_indices[index]

                            # 优化：更新来源周期索引判断是否合成目标周期索引对应的值

                    review_period_process_data = ReviewPeriodProcessData()
                    review_period_process_data.current_period = target_period
                    review_period_process_data.current_start_date_time = df['date'].iloc[self.start_animation_index]
                    review_period_process_data.current_min_index = 0
                    review_period_process_data.current_max_index = self.max_animation_index
                    review_period_process_data.current_index = self.start_animation_index
                    review_period_process_data.current_start_index = self.start_animation_index
                    self.dict_period_process_data[target_period] = review_period_process_data
                    if target_period < self.min_period:
                        self.min_period = target_period
                        self.logger.info(f"更新最小周期为：{TimePeriod.get_chinese_label(self.min_period)}")

                    self.update_chart(data, self.start_animation_index)
                    dict_return = {
                            "start_date_index": self.start_animation_index,
                            "min_index": self.min_animation_index,
                            "max_index": self.max_animation_index,
                            "start_date": review_period_process_data.current_start_date_time
                        }
                else:
                    self.logger.warning(f"周期切换处理--未找到匹配的日期记录：{start_date}")
            
        else:
            self.logger.info("start_date为空")


        self.sig_init_review_animation_finished.emit(True, dict_return)
        return dict_return

    # 添加播放控制方法
    def start_animation(self, start_index=None):
        """开始动画播放"""
        self.animation_timer.start(self.animation_speed)
        self.is_playing = True
        self.enable_period_btn(False)

    def pause_animation(self):
        """暂停动画播放"""
        self.animation_timer.stop()
        self.is_playing = False
        self.enable_period_btn(True)

    def stop_animation(self):
        """停止动画播放"""
        self.animation_timer.stop()
        self.is_playing = False
        self.enable_period_btn(True)

    def set_animation_speed(self, speed_ms):
        """设置动画播放速度"""
        self.animation_speed = speed_ms
        if self.is_playing:
            self.animation_timer.stop()
            self.animation_timer.start(self.animation_speed)

    def step_forward(self, steps=1):
        """向前播放指定步数"""
        if self.df_data is None or self.df_data.empty:
            return
        
        new_index = self.current_animation_index + steps

        if new_index < 0:
            QMessageBox.warning(self, "提示", "已到达最前")
            self.sig_animation_play_finished.emit()
            return
        
        if new_index > self.max_animation_index:
            QMessageBox.warning(self, "提示", "已到达最后")
            return

        data = self.df_data.iloc[0]
        self.update_chart(data, new_index)

    def step_backward(self, steps=1):
        """向后回退指定步数"""
        if self.df_data is None or self.df_data.empty:
            return
        
        new_index = self.current_animation_index - steps

        if new_index < 0:
            QMessageBox.warning(self, "提示", "已到达最前")
            return

        data = self.df_data.iloc[0]
        self.update_chart(data, new_index)

    def back_to_front(self):
        """回到最前"""
        if self.df_data is None or self.df_data.empty:
            return
        
        data = self.df_data.iloc[0]
        self.update_chart(data, 0)

    def back_to_end(self):
        """回到最后"""
        if self.df_data is None or self.df_data.empty:
            return
        
        data = self.df_data.iloc[0]
        self.update_chart(data, self.max_animation_index)

    def go_to_target_index(self, index):
        """跳转到指定索引"""
        if self.df_data is None or self.df_data.empty:
            return
        
        if index == self.current_animation_index:
            return

        data = self.df_data.iloc[0]
        self.update_chart(data, index)


    # --------------------------槽函数-------------------------------
    def slot_period_button_clicked(self, btn):
        if self.df_data is None or self.df_data.empty:
            self.logger.warning("数据为空，无法切换图表周期数据")
            return
        target_period = TimePeriod.from_label(btn.text())

        # 复盘模式：周期数据只由外部（加载/随机加载按钮）按需注入；
        # 未注入的周期不允许切换，回退到原周期并提示，不触发上层数据加载。
        if self.property("review") is not None and target_period not in self.dict_stock_data:
            self.logger.warning(
                f"{self.current_selected_code}未注入{TimePeriod.get_chinese_label(target_period)}数据，"
                f"请通过加载按钮加载该周期后再切换"
            )
            last_btn = self.period_button_group.button(self.last_period_btn_checked_id)
            if last_btn is not None and last_btn is not btn:
                last_btn.setChecked(True)
            return

        self.set_period(target_period)
        if target_period not in self.dict_stock_data:
            self.logger.warning(f"{self.current_selected_code}未注入{TimePeriod.get_chinese_label(target_period)}数据，切换后图表可能为空")
        checked_id = self.period_button_group.checkedId()
        if self.property("review") is not None:
            # self.logger.info(f"所属复盘模块，暂不支持周期切换")
            list_btns = self.period_button_group.buttons()
            if checked_id >= 0 and checked_id < len(list_btns):
                target_period_text = self.period_button_group.button(checked_id).text()
                last_period_text = self.period_button_group.button(self.last_period_btn_checked_id).text()
                self.logger.info(f"此前周期id：{self.last_period_btn_checked_id}，名称：{last_period_text}，切换到目标周期id：{checked_id}，名称：{target_period_text}")
                # 切换前按当前复盘位置重新生成上级周期数据（上级周期由基周期本地聚合）
                # 分钟级需携带完整 date+time，否则进行中槽位会按日期 00:00 定位
                last_period = TimePeriod.from_label(last_period_text)
                current_date_time = (
                    self.df_data.iloc[self.current_animation_index]['time']
                    if 'time' in self.df_data.columns
                    else self.df_data.iloc[self.current_animation_index]['date']
                )
                self._refresh_derived_period_data(
                    target_period, current_date_time)
                dict_return = self.init_animation(self.df_data.iloc[0], current_date_time, False)
                if not dict_return:
                    # 目标周期数据未覆盖当前复盘位置：回退到来源周期，避免复盘位置漂移
                    self.logger.warning(
                        f"周期{TimePeriod.get_chinese_label(target_period)}数据未覆盖当前位置 {current_date_time}，保持原周期")
                    last_btn = self.period_button_group.button(self.last_period_btn_checked_id)
                    if last_btn is not None:
                        last_btn.setChecked(True)
                    self.set_period(last_period)
                    self.update_chart(self.df_data.iloc[0], self.current_animation_index)
                    if last_btn is not None:
                        self.kline_widget.set_period_text(last_btn.text())
                    self.sig_period_changed.emit(last_period)
                    return
                # if checked_id < self.last_period_btn_checked_id:
                #     # 大周期切小周期
                #     # 需更新：self.current_animation_index，self.min_animation_index，self.max_animation_index，并通知外层控件
                #     self.init_animation(self.df_data.iloc[0], self.df_data.iloc[self.current_animation_index]['date'])
                # else:
                #     # 小周期切大周期。问题：合成未走完的k线数据。
                #     self.logger.info(f"暂不支持小周期切大周期")
                #     # self.init_animation(self.df_data.iloc[0], self.df_data.iloc[self.current_animation_index]['date'], checked_id)
            else:
                self.logger.warning(f"当前选中的按钮ID: {checked_id} 不存在")
                return
        else:
            self.update_chart(self.df_data.iloc[0])

        # 周期切换完成后通知外部（外部可按需补齐该周期数据并刷新图表）
        self.sig_period_changed.emit(target_period)

        self.kline_widget.set_period_text(btn.text())
        self.last_period_btn_checked_id = checked_id
        

    def slot_btn_indicator_volume_clicked(self):
        is_checked = self.btn_indicator_volume.isChecked()
        if is_checked:
            widget = self.add_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.VOLUME))
            if widget is None:
                self.btn_indicator_volume.setChecked(False)
        else:
            self.remove_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.VOLUME))

    def slot_btn_indicator_amount_clicked(self):
        is_checked = self.btn_indicator_amount.isChecked()
        if is_checked:
            widget = self.add_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.AMOUNT))
            if widget is None:
                self.btn_indicator_amount.setChecked(False)
        else:
            self.remove_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.AMOUNT))

    def slot_btn_indicator_macd_clicked(self):
        is_checked = self.btn_indicator_macd.isChecked()
        if is_checked:
            widget = self.add_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.MACD))
            if widget is None:
                self.btn_indicator_macd.setChecked(False)
        else:
            self.remove_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.MACD))

    def slot_btn_indicator_kdj_clicked(self):
        is_checked = self.btn_indicator_kdj.isChecked()
        if is_checked:
            widget = self.add_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.KDJ))
            if widget is None:
                self.btn_indicator_kdj.setChecked(False)
        else:
            self.remove_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.KDJ))

    def slot_btn_indicator_rsi_clicked(self):
        is_checked = self.btn_indicator_rsi.isChecked()
        if is_checked:
            widget = self.add_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.RSI))
            if widget is None:
                self.btn_indicator_rsi.setChecked(False)
        else:
            self.remove_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.RSI))

    def slot_btn_indicator_boll_clicked(self):
        is_checked = self.btn_indicator_boll.isChecked()
        if is_checked:
            widget = self.add_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.BOLL))
            if widget is None:
                self.btn_indicator_boll.setChecked(False)
        else:
            self.remove_indicator_chart(IndicatrosEnum.get_label(IndicatrosEnum.BOLL))

    def slot_btn_indicator_ma_clicked(self):
        is_checked = self.btn_indicator_ma.isChecked()
        self.kline_widget.show_ma(is_checked)

    def slot_range_changed(self):
        '''
            当任何指标图的plot_widget的X轴范围改变时调用
        '''
        self.kline_widget.slot_range_changed()

        # 同步所有指标图表
        for indicator_name, widget in self.indicator_widgets.items():
            widget.slot_range_changed()

    def slot_btn_review_clicked(self):
        from gui.qt_widgets.review.review_dialog import ReviewDialog
        dlg = ReviewDialog()
        dlg.preload_data(self.df_data.iloc[-1])
        dlg.exec()

    def slot_animation_step(self):
        if self.current_animation_index >= self.max_animation_index:
            self.logger.info("已到达最后，播放结束")
            self.stop_animation()
            self.sig_animation_play_finished.emit()
            return
        
        self.step_forward()

