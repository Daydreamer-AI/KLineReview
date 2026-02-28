from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout
from PyQt5.QtCore import pyqtSlot
# from controller.processor_controller import processor_controller_instance

from processor.baostock_processor import BaoStockProcessor
from processor.ak_stock_data_processor import AKStockDataProcessor

from common.common_api import *
import datetime
from manager.logging_manager import get_logger

from gui.qt_widgets.main.minute_level_select_dialog import MinuteLevelSelectDialog
from gui.qt_widgets.main.stock_data_fetch_widget import StockDataFetchWidget

class HomeWidget(QWidget):
    def __init__(self):
        super().__init__()

        # 加载 UI 文件，第二个参数 self 表示将控件加载到当前窗口
        # 注意：PyQt5 在加载 .ui文件时，如果发现槽函数名称符合 on_对象名_信号名的格式，​​会自动连接​​信号和槽
        uic.loadUi('./src/gui/qt_widgets/main/HomeWidget.ui', self)  # 确保路径正确

        self.logger = get_logger(__name__)

        self.bao_stock_data_fetch_widget = StockDataFetchWidget(self)
        self.show_bao_stock_data_fetch_widget(False)

        self.init_processors()
        self.init_connect()
    
    def init_processors(self):
        """初始化所有处理器（如Baostock）"""
        self.logger.info("初始化所有处理器")
        try:
            ak_success = AKStockDataProcessor().initialize()
            self.logger.info("AK股票数据初始化完成")
            success = BaoStockProcessor().initialize()
            if ak_success and success:
                self.logger.info("所有处理器初始化成功")
                # BaoStockProcessor().load_all_local_stock_data()     # 待优化，放后台加载
                BaoStockProcessor().start_background_loading()
                # BaoStockProcessor().create_baostock_table_indexes()   # 创建索引
            else:
                self.logger.info("处理器初始化失败")
                # 可以进行一些UI提示，例如设置label的文本为红色警告
                quit()
        except Exception as e:
            self.logger.info(f"初始化过程中发生错误: {e}")

    def init_connect(self):
        """连接信号槽"""
        # 连接信号槽 (示例：假设UI文件中有一个名为 pushButton 的按钮)
        # Baostock
        self.btn_get_all_stocks.clicked.connect(self.slot_btn_get_all_stocks_clicked)
        self.btn_query_sh_main.clicked.connect(self.slot_btn_query_sh_main_clicked)
        self.btn_query_sz_main.clicked.connect(self.slot_btn_query_sz_main_clicked)
        self.btn_query_gem.clicked.connect(self.slot_btn_query_gem_clicked)
        self.btn_query_star.clicked.connect(self.slot_btn_query_star_clicked)

        self.btn_query_minute_level.clicked.connect(self.slot_btn_query_minute_level_clicked)

        self.btn_auto_process_all_stock_data.clicked.connect(self.slot_btn_auto_process_all_stock_data_clicked)

        # AKShare
        self.btn_get_akshare_stocks_info.clicked.connect(self.slot_btn_get_akshare_stocks_info_clicked)

        self.btn_update_sh_main_data.clicked.connect(self.slot_btn_update_sh_main_data_clicked)
        self.btn_update_sz_main_data.clicked.connect(self.slot_btn_update_sz_main_data_clicked)
        self.btn_update_gem_data.clicked.connect(self.slot_btn_update_gem_data_clicked)
        self.btn_update_star_data.clicked.connect(self.slot_btn_update_star_data_clicked)
        self.btn_update_weekly_data.clicked.connect(self.slot_btn_update_weekly_data_clicked)

        self.btn_update_float_cap.clicked.connect(self.slot_btn_update_float_cap_clicked)
        self.btn_query_float_cap.clicked.connect(self.slot_btn_query_float_cap_clicked)

        self.btn_update_ths_board_industry_data.clicked.connect(self.slot_btn_update_ths_board_industry_data_clicked)
        self.btn_query_ths_board_industry_data.clicked.connect(self.slot_btn_query_ths_board_industry_data_clicked)

        self.btn_update_ths_board_concept_data.clicked.connect(self.slot_btn_update_ths_board_concept_data_clicked)
        self.btn_query_ths_board_concept_data.clicked.connect(self.slot_btn_query_ths_board_concept_data_clicked)

        self.btn_update_chip_distribution_data_eastmoney.clicked.connect(self.slot_btn_update_chip_distribution_data_eastmoney_clicked)
        self.btn_get_chip_distribution_data_eastmoney.clicked.connect(self.slot_btn_get_chip_distribution_data_eastmoney_clicked)

        self.btn_update_popularity_rank_stock_data.clicked.connect(self.slot_btn_update_popularity_rank_stock_data_clicked)
        self.btn_get_popularity_rank_stock_data.clicked.connect(self.slot_btn_get_popularity_rank_stock_data_clicked)

        self.btn_update_em_industry_board_data.clicked.connect(self.slot_btn_update_em_industry_board_data_clicked)
        self.btn_query_em_industry_board_data.clicked.connect(self.slot_btn_query_em_industry_board_data_clicked)

        self.btn_update_em_industry_board_cons.clicked.connect(self.slot_btn_update_em_industry_board_cons_clicked)
        self.btn_query_em_industry_board_cons.clicked.connect(self.slot_btn_query_em_industry_board_cons_clicked)

        self.btn_market_activity_legu.clicked.connect(self.slot_btn_market_activity_legu_clicked)
        self.btn_query_market_activity_legu.clicked.connect(self.slot_btn_query_market_activity_legu_clicked)

    def show_bao_stock_data_fetch_widget(self, b_show=True):
        if b_show:
            # 居中显示
            self.bao_stock_data_fetch_widget.move(self.geometry().center() - self.bao_stock_data_fetch_widget.rect().center())
            self.bao_stock_data_fetch_widget.show()
        else:
            self.bao_stock_data_fetch_widget.hide()

    def closeEvent(self, event):
        """
        重写 closeEvent，当窗口请求关闭时调用。
        这是执行清理操作的理想位置。
        """
        self.logger.info("开始执行清理操作...")
        try:
            BaoStockProcessor().cleanup() # 清理所有处理器
        except Exception as e:
            self.logger.info(f"清理过程中发生错误: {e}")
        finally:
            # 确保事件继续传递，允许窗口关闭
            event.accept()
            self.logger.info("清理完成，窗口关闭。")

    # 槽函数
    # Baostock
    @pyqtSlot()
    def slot_btn_get_all_stocks_clicked(self):
        self.logger.info("Baostock--获取A股所有股票数据基本信息")
        BaoStockProcessor().get_and_save_all_stocks_from_bao()
        # BaoStockProcessor().get_all_stocks_from_db()
        self.logger.info("Baostock--获取A股所有股票数据基本信息完成")

    @pyqtSlot()
    def slot_btn_query_sh_main_clicked(self):
        self.logger.info("Baostock--查询沪市主板股票数据")
        # BaoStockProcessor().process_sh_main_stock_daily_data()
        # BaoStockProcessor().process_sh_main_stock_weekly_data()
        BaoStockProcessor().start_sh_main_stock_data_background_update()
        self.logger.info("Baostock--查询沪市主板股票数据完成")

    @pyqtSlot()
    def slot_btn_query_sz_main_clicked(self):
        self.logger.info("Baostock--查询深市主板股票数据")
        # BaoStockProcessor().process_sz_main_stock_daily_data()
        # BaoStockProcessor().process_sz_main_stock_weekly_data()
        BaoStockProcessor().start_sz_main_stock_data_background_update()
        self.logger.info("Baostock--查询深市主板股票数据完成")
    @pyqtSlot()
    def slot_btn_query_gem_clicked(self):
        self.logger.info("Baostock--查询创业板股票数据")
        # BaoStockProcessor().process_gem_stock_daily_data()
        # BaoStockProcessor().process_gem_stock_weekly_data()
        BaoStockProcessor().start_gem_stock_data_background_update()
        self.logger.info("Baostock--查询创业板股票数据完成")

    @pyqtSlot()
    def slot_btn_query_star_clicked(self):
        self.logger.info("Baostock--查询科创板股票数据")
        # BaoStockProcessor().process_star_stock_daily_data()
        # BaoStockProcessor().process_star_stock_weekly_data()
        BaoStockProcessor().start_star_stock_data_background_update()
        self.logger.info("Baostock--查询科创板股票数据")

    @pyqtSlot()
    def slot_btn_query_minute_level_clicked(self):
        self.logger.info("Baostock--查询A股所有股票分钟级别数据")
        dlg = MinuteLevelSelectDialog()
        ret = dlg.exec()
        self.logger.info(f"MinuteLevelSelectDialog--返回值: {ret}")
        if ret == 1:
            target_code = dlg.get_target_code()

            type_id = dlg.get_checked_board_type()
            level_id = dlg.get_checked_minute_level()
            self.logger.info(f"MinuteLevelSelectDialog--选择的板块: {type_id}")
            self.logger.info(f"MinuteLevelSelectDialog--选择的级别: {level_id}")

            result = None

            if target_code != '':
                self.logger.info(f"MinuteLevelSelectDialog--选择的股票: {target_code}")
                # result = BaoStockProcessor().process_and_save_minute_level_stock_data(target_code, str(level_id))
                result = BaoStockProcessor().process_minute_level_stock_data(target_code, str(level_id))
                # if result is not None and not result.empty:
                #     sdi.default_indicators_auto_calculate(result)
            else:
                board_type = 'sh_main'
                if type_id == 1:  # 沪市
                    board_type = 'sh_main'
                elif type_id == 2:  # 深市
                    board_type = 'sz_main'
                elif type_id == 3:  # 创业板
                    board_type = 'gem'
                elif type_id == 4:  # 科创板
                    board_type = 'star'
                elif type_id == 5:  # 北交所
                    board_type = 'bse'

                self.logger.info(f"MinuteLevelSelectDialog--选择的板块: {board_type}")

                BaoStockProcessor().start_minute_level_stock_data_background_update(board_type, str(level_id))

            if result is not None and not result.empty:
                self.logger.info(f"process_minute_level_stock_data--结果: \n{result.tail(3)}")
        else:
            pass

        self.logger.info("Baostock--查询A股所有股票分钟级别数据完成")

    def slot_btn_auto_process_all_stock_data_clicked(self):
        self.logger.info("自动处理所有股票数据")
        # BaoStockProcessor().auto_process_all_stock_data()
        self.show_bao_stock_data_fetch_widget(True)

    # =================================================================================AKShare==========================================================================
    @pyqtSlot()
    def slot_btn_get_akshare_stocks_info_clicked(self):
        self.logger.info("AKShare--查询A股所有股票级别信息")
        AKStockDataProcessor().get_stocks_info_and_save_to_db()
        self.logger.info("AKShare--查询A股所有股票级别信息完成")

    @pyqtSlot()
    def slot_btn_update_sh_main_data_clicked(self):
        self.logger.info("AKShare--更新沪市主板股票数据")
        self.logger.info("AKShare--更新沪市主板股票数据完成")

    @pyqtSlot()
    def slot_btn_update_sz_main_data_clicked(self):
        self.logger.info("AKShare--更新深市主板股票数据")
        self.logger.info("AKShare--更新深市主板股票数据完成")

    @pyqtSlot()
    def slot_btn_update_gem_data_clicked(self):
        self.logger.info("AKShare--更新创业板股票数据")
        self.logger.info("AKShare--更新创业板股票数据完成")

    @pyqtSlot()
    def slot_btn_update_star_data_clicked(self):
        self.logger.info("AKShare--更新科创板股票数据")
        self.logger.info("AKShare--更新科创板股票数据完成")
        

    @pyqtSlot()
    def slot_btn_update_weekly_data_clicked(self):
        self.logger.info("AKShare--更新股票周线数据")
        self.logger.info("AKShare--更新股票周线数据完成")
        

    @pyqtSlot()
    def slot_btn_update_float_cap_clicked(self):
        # 周更 or 月更，更新所有股票流通市值
        self.logger.info("AKShare--更新所有股票流通市值")
        AKStockDataProcessor().get_all_stocks_from_eastmoney()
        self.logger.info("AKShare--更新所有股票流通市值完成")

    @pyqtSlot()
    def slot_btn_query_float_cap_clicked(self):
        self.logger.info("AKShare--查询最后一个交易日所有股票流通市值")
        # result = AKStockDataProcessor().query_eastmoney_stock_data()
        # self.logger.info(result)
        result = AKStockDataProcessor().get_latest_eastmoney_stock_data()
        self.logger.info(result)
        self.logger.info("AKShare--查询最后一个交易日所有股票流通市值完成")

    @pyqtSlot()
    def slot_btn_update_ths_board_industry_data_clicked(self):
        self.logger.info("AKShare--更新同花顺行业板块数据")
        AKStockDataProcessor().process_and_save_ths_board_industry()
        self.logger.info("AKShare--更新同花顺行业板块数据完成")

    @pyqtSlot()
    def slot_btn_query_ths_board_industry_data_clicked(self):
        self.logger.info("AKShare--查询最后一个交易日的同花顺行业板块数据")
        # result = AKStockDataProcessor().query_ths_board_industry_data()
        # self.logger.info(result)
        result = AKStockDataProcessor().get_latest_ths_board_industry_data()
        self.logger.info(result)
        self.logger.info("AKShare--查询最后一个交易日的同花顺行业板块数据完成")

    @pyqtSlot()
    def slot_btn_update_ths_board_concept_data_clicked(self):
        self.logger.info("AKShare--更新同花顺概念板块数据")
        # AKStockDataProcessor().query_ths_concept_board_info()
        AKStockDataProcessor().process_ths_board_concept_overview_data()
        self.logger.info("AKShare--更新同花顺概念板块数据完成")

    @pyqtSlot()
    def slot_btn_query_ths_board_concept_data_clicked(self):
        self.logger.info("AKShare--查询最后一个交易日的同花顺概念板块数据")
        # result = AKStockDataProcessor().query_ths_board_industry_data()
        # self.logger.info(result)

        # result = AKStockDataProcessor().get_latest_ths_concept_board_info()
        # self.logger.info(result)

        result = AKStockDataProcessor().get_latest_ths_board_concept_overview()
        self.logger.info(result)

        self.logger.info("AKShare--查询最后一个交易日的同花顺概念板块数据完成")

    @pyqtSlot()
    def slot_btn_update_chip_distribution_data_eastmoney_clicked(self):
        self.logger.info("AKShare--更新所有股票筹码分布数据")
        AKStockDataProcessor().process_and_insert_eastmoney_stock_chip_distribution_data_to_db()
        self.logger.info("AKShare--更新所有股票筹码分布数据完成")

    @pyqtSlot()
    def slot_btn_get_chip_distribution_data_eastmoney_clicked(self):
        self.logger.info("AKShare--查询所有股票筹码分布数据")
        AKStockDataProcessor().query_eastmoney_stock_chip_distribution_data()
        self.logger.info("AKShare--查询所有股票筹码分布数据完成")

    @pyqtSlot()
    def slot_btn_update_popularity_rank_stock_data_clicked(self):
        self.logger.info("AKShare--更新人气榜数据")
        AKStockDataProcessor().get_popularity_rank_stock_data_from_eastmoney()
        self.logger.info("AKShare--更新人气榜数据完成")

    @pyqtSlot()
    def slot_btn_get_popularity_rank_stock_data_clicked(self):
        self.logger.info("AKShare--查询人气榜数据")
        result = AKStockDataProcessor().query_popularity_rank_stock_data()
        # result = AKStockDataProcessor().get_latest_popularity_rank_stock_data
        self.logger.info(result)
        self.logger.info("AKShare--查询人气榜数据完成")

    def slot_btn_update_em_industry_board_data_clicked(self):
        self.logger.info("AKShare--更新东财行业板块数据")
        result = AKStockDataProcessor().auto_process_and_save_em_industry_board_data()
        # result = AKStockDataProcessor().get_latest_popularity_rank_stock_data
        self.logger.info(result)
        self.logger.info("AKShare--更新东财行业板块数据完成")

    def slot_btn_query_em_industry_board_data_clicked(self):
        self.logger.info("AKShare--查询东财行业板块数据")
        result = AKStockDataProcessor().get_latest_em_industry_board_data()
        self.logger.info(result)
        self.logger.info("AKShare--查询东财行业板块数据完成")

    def slot_btn_update_em_industry_board_cons_clicked(self):
        self.logger.info("AKShare--更新东财行业板块成份数据")
        result = AKStockDataProcessor().process_and_save_em_industry_board_cons()
        self.logger.info(result)
        self.logger.info("AKShare--更新东财行业板块成份数据完成")

    def slot_btn_query_em_industry_board_cons_clicked(self):
        self.logger.info("AKShare--查询东财行业板块成份股数据")
        result = AKStockDataProcessor().get_latest_em_industry_board_cons_data()
        self.logger.info(result)
        self.logger.info("AKShare--查询东财行业板块成份股数据完成")

    def slot_btn_market_activity_legu_clicked(self):
        self.logger.info("AKShare--更新乐咕乐股市场活跃度")
        result = AKStockDataProcessor().process_market_activity_legu()
        self.logger.info(result)
        self.logger.info("AKShare--更新乐咕乐股市场活跃度完成")

    def slot_btn_query_market_activity_legu_clicked(self):
        self.logger.info("AKShare--查询乐咕乐股市场活跃度")
        result = AKStockDataProcessor().get_latest_market_activity_legu_data()
        self.logger.info(result)
        self.logger.info("AKShare--查询乐咕乐股市场活跃度完成")
        
