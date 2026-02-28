from PyQt5.QtCore import QObject, pyqtSignal

from manager.logging_manager import get_logger

class DemoTradingRecord(object):
    
    def __init__(self):
        self.code = None
        self.name = None

        self.pending_order_buy_date_time = None
        self.pending_order_buy_cancel_date_time = None
        
        self.buy_price = None           # 购买价格
        self.buy_date_time = None       # 购买时间

        self.buy_amount = None          # 购买金额
        self.buy_count = None           # 购买股数

        self.pending_order_sell_date_time = None
        self.pending_order_sell_cancel_date_time = None

        self.sell_price = None
        self.sell_date_time = None

        self.sell_amount = None
        self.sell_count = None

        self.status = 0                 # 0: 未交易，1: 买入挂单，2：买入撤单，3：卖出挂单，4：卖出撤单，5：持有中，6：交易完成
        self.trading_yield = 0.0        # 收益

    def get_status_text(self):
        if self.status == 0:
            return "未交易"
        elif self.status == 1:
            return "买入挂单"
        elif self.status == 2:
            return "买入撤单"
        elif self.status == 3:
            return "卖出挂单"
        elif self.status == 4:
            return "卖出撤单"
        elif self.status == 5:
            return "持有中"
        elif self.status == 6:
            return "交易完成"



class ReviewDemoTradingManager(QObject):
    sig_total_assets_and_available_balance_changed = pyqtSignal(float, float)
    sig_trading_status_changed = pyqtSignal(int)
    sig_trading_yield_changed = pyqtSignal(float)

    def __init__(self, total_assets=10000, available_balance = 10000, parent = None):
        super().__init__(parent)

        self.logger = get_logger(__name__)

        self.total_assets = total_assets               # 总资产
        self.available_balance = available_balance          # 可用资金

        self.current_trading_record = None
        self.trding_record_list = []

    def update_available_balance(self, target_status, price, count):
        if self.current_trading_record is None:  # 未交易
            self.total_assets = self.available_balance
        else:
            # available_balance只有2种情况需要更新：买入成交、卖出成交
            if target_status == 1:
                # 买入挂单情况
                if self.current_trading_record.status == 5:  # 买入成交
                    self.available_balance -= price * count
            elif target_status == 2:
                # 卖出挂单情况
                if self.current_trading_record.status == 6: # 卖出成交
                    self.available_balance += price * count

            # total_assets更新情况：未交易或交易完成，则总资产等于可用资金，否则更新
            if self.current_trading_record.status == 6:  # 交易完成
                self.total_assets = self.available_balance
            else:
                self.total_assets = self.available_balance + price * count

        # 发送信号通知外层控件更新
        self.sig_total_assets_and_available_balance_changed.emit(self.total_assets, self.available_balance)

    def get_trding_record_list(self):
        return self.trding_record_list

    def get_trading_status(self):
        if self.current_trading_record is None:
            return 0
        else:
            return self.current_trading_record.status

    def get_total_assets(self):
        return self.total_assets
    
    def set_total_assets(self, total_assets):
        self.total_assets = total_assets
    
    def get_available_balance(self):
        return self.available_balance
    
    def set_available_balance(self, available_balance):
        self.available_balance = available_balance

    def get_max_count_can_buy(self, price):
        self.logger.info(f"当前可用资金：{self.available_balance}, 价格：{price}")
        max_count = int(self.available_balance / price)  # 计算最大可买股数
        return (max_count // 100) * 100  # 取100的整数倍
    
    def get_buy_count(self, price, proportion=0):
        max_count_can_buy = self.get_max_count_can_buy(price)
        self.logger.info(f"可购买最大股数：{max_count_can_buy}")

        if proportion == 0:  # 满仓
            buy_count = max_count_can_buy
        elif proportion == 1:  # 1/2
            buy_count = (max_count_can_buy // 2 // 100) * 100
        elif proportion == 2:  # 1/3
            buy_count = (max_count_can_buy // 3 // 100) * 100
        elif proportion == 3:  # 1/4
            buy_count = (max_count_can_buy // 4 // 100) * 100
        elif proportion == 4:  # 1/5
            buy_count = (max_count_can_buy // 5 // 100) * 100
        else:
            buy_count = max_count_can_buy

        # 确保至少是100股的倍数且不为负
        buy_count = max(0, buy_count)
        return buy_count

    def pending_order_buy(self, code, name, price, count, date_time):
        '''
            指定价格买入挂单
        '''
        if count < 100:
            self.logger.warning("最低购买100股，请重新选择")
            return False
        
        if self.current_trading_record is not None:
            self.logger.warning("当前有未完成交易，请先处理")
            return False

        demo_trding_record = DemoTradingRecord()

        demo_trding_record.code = code
        demo_trding_record.name = name

        # 判断当前可用资金能否支持购买最低股数（100股）
        if self.available_balance < 100 * price:
            self.logger.warning("可用资金不足，请重新选择")
            return False

        demo_trding_record.buy_price = price
        demo_trding_record.buy_count = count
        demo_trding_record.buy_amount = price * count
        demo_trding_record.pending_order_buy_date_time = date_time

        demo_trding_record.status = 1   # 买入挂单
        
        self.current_trading_record = demo_trding_record

        self.logger.info(f"提交买入挂单, 时间：{self.current_trading_record.pending_order_buy_date_time}")
        self.sig_trading_status_changed.emit(1)

    def pending_order_sell(self, sell_price, count, date_time):
        if self.current_trading_record is None:
            self.logger.warning("当前无交易，请先处理")
            return False

        if count < 100:
            self.logger.warning("最低卖出100股，请重新选择")
            return False
        
        self.current_trading_record.sell_price = sell_price
        self.current_trading_record.pending_order_sell_date_time = date_time
        self.current_trading_record.sell_count = count
        self.current_trading_record.sell_amount = sell_price * count
        self.current_trading_record.status = 3  # 卖出挂单
        self.logger.info(f"提交卖出挂单, 时间：{date_time}")
        self.sig_trading_status_changed.emit(3)

    def update_trading_record(self, target_status, dict_kline_price, date_time):
        if self.current_trading_record is None:
            # self.logger.warning("当前无交易")
            return False
        
        # target_status: 0：撤单，1：买入成交判断，2：卖出成交判断，5：持有中，6：交易完成
        if target_status == 0 and (self.current_trading_record.status != 1 and self.current_trading_record.status != 3):
            self.logger.warning("当前无挂单，无法执行撤单操作")
            return False
        
        if target_status == 1 and self.current_trading_record.status != 1:
            self.logger.warning("当前无买入挂单，无法执行买入成交判断操作")
            return False
        
        if target_status == 2 and self.current_trading_record.status != 3:
            self.logger.warning("当前无卖出挂单，无法执行卖出成交判断操作")
            return False
        
        if dict_kline_price is None or dict_kline_price == {}:
            self.logger.warning("无K线数据，无法判断交易结果")
            return False
        
        min_price = dict_kline_price['low']
        max_price = dict_kline_price['high']
        open_price = dict_kline_price['open']
        close_price = dict_kline_price['close']
        
        # 回退情况处理
        if self.current_trading_record.status == 1:
            if date_time < self.current_trading_record.pending_order_buy_date_time:
                self.logger.warning("时间回退至买入挂单时间之前，自动取消买入挂单")

                self.current_trading_record.status = 2  # 买入撤单
                self.current_trading_record.pending_order_buy_cancel_date_time = date_time
                self.trding_record_list.append(self.current_trading_record)

                # 置None之前触发信号
                self.sig_trading_status_changed.emit(self.current_trading_record.status)
                self.current_trading_record = None
                return False
        # elif self.current_trading_record.status == 3:
        #     if date_time < self.current_trading_record.pending_order_sell_date_time:
        #         self.logger.warning("时间回退至卖出挂单时间之前，自动取消卖出挂单")

        #         self.current_trading_record.status = 4  # 卖出撤单
        #         self.current_trading_record.pending_order_sell_cancel_date_time = date_time
        #         self.trding_record_list.append(self.current_trading_record)
        #         self.sig_trading_status_changed.emit(self.current_trading_record.status)
        #         self.current_trading_record = None
        #         return False
        elif self.current_trading_record.status == 3 or self.current_trading_record.status == 5:
            if date_time < self.current_trading_record.buy_date_time:
                self.logger.warning("时间回退至买入成交时间之前，自动以最小或成本价平仓")

                self.current_trading_record.sell_price = min(min_price, self.current_trading_record.buy_price)
                self.current_trading_record.pending_order_sell_date_time = date_time
                self.current_trading_record.sell_count = self.current_trading_record.buy_count
                self.current_trading_record.sell_amount = self.current_trading_record.buy_amount

                self.current_trading_record.status = 6
                self.current_trading_record.sell_date_time = date_time
                self.current_trading_record.trading_yield = (self.current_trading_record.sell_price - self.current_trading_record.buy_price) / self.current_trading_record.buy_price
                self.update_available_balance(target_status, self.current_trading_record.sell_price, self.current_trading_record.sell_count)
                self.trding_record_list.append(self.current_trading_record)

                self.sig_trading_yield_changed.emit(self.current_trading_record.trading_yield)    # 通知更新收益率
                self.sig_trading_status_changed.emit(self.current_trading_record.status)
                self.current_trading_record = None

                return False
        
        # 更新交易状态信息
        if target_status == 0:
            if self.current_trading_record.status == 1:
                self.current_trading_record.status = 2  # 买入撤单后状态应该是未交易，当然买入撤单状态也属于未交易状态。
                self.current_trading_record.pending_order_buy_cancel_date_time = date_time
                self.logger.info(f"买入撤单成功, 时间：{date_time}")
                self.trding_record_list.append(self.current_trading_record)
                
            elif self.current_trading_record.status == 3:
                self.current_trading_record.status = 5  # 卖出撤单后状态应该是持有中
                self.current_trading_record.pending_order_sell_cancel_date_time = date_time
                self.logger.info(f"卖出撤单成功, 时间：{date_time}")
            
            # self.trding_record_list.append(self.current_trading_record)
            self.sig_trading_status_changed.emit(self.current_trading_record.status)

            if self.current_trading_record.status == 2:
                self.current_trading_record = None
        elif target_status == 1:
            if (min_price <= self.current_trading_record.buy_price and self.current_trading_record.buy_price <= max_price) or self.current_trading_record.buy_price >= max_price:
                if self.current_trading_record.buy_price > max_price:
                    self.current_trading_record.buy_price = open_price
                    self.current_trading_record.buy_amount = self.current_trading_record.buy_price * self.current_trading_record.buy_count

                # 买入挂单成交
                self.current_trading_record.status = 5  # 持有中
                self.current_trading_record.buy_date_time = date_time
                self.update_available_balance(target_status, self.current_trading_record.buy_price, self.current_trading_record.buy_count)
                self.logger.info(f"买入挂单成交, 时间：{date_time}，成交价格：{self.current_trading_record.buy_price}, 最低价格：{min_price}, 最高价格：{max_price}")
                self.sig_trading_status_changed.emit(self.current_trading_record.status)

        elif target_status == 2:
            # self.logger.info(f"卖出挂单判断, 时间：{date_time}, 最低价格：{min_price}, 最高价格：{max_price}")
            if (min_price <= self.current_trading_record.sell_price and self.current_trading_record.sell_price <= max_price) or min_price >= self.current_trading_record.sell_price:
                if min_price > self.current_trading_record.sell_price:
                    self.current_trading_record.sell_price = min_price
                    self.current_trading_record.sell_amount = min_price * self.current_trading_record.sell_count

                # 卖出挂单成交
                self.current_trading_record.status = 6
                self.current_trading_record.sell_date_time = date_time
                self.current_trading_record.trading_yield = (self.current_trading_record.sell_price - self.current_trading_record.buy_price) / self.current_trading_record.buy_price
                self.update_available_balance(target_status, self.current_trading_record.sell_price, self.current_trading_record.sell_count)
                self.trding_record_list.append(self.current_trading_record)

                self.sig_trading_status_changed.emit(self.current_trading_record.status)
                self.sig_trading_yield_changed.emit(self.current_trading_record.trading_yield)    # 通知更新收益率
                self.logger.info(f"卖出挂单成交，交易完成, 时间：{date_time}，成交价格：{self.current_trading_record.sell_price}, 最低价格：{min_price}, 最高价格：{max_price}")
                self.current_trading_record = None
            else:
                self.update_available_balance(target_status, close_price, self.current_trading_record.buy_count)
                self.current_trading_record.trading_yield = (close_price - self.current_trading_record.buy_price) / self.current_trading_record.buy_price
                self.sig_trading_yield_changed.emit(self.current_trading_record.trading_yield)    # 通知更新收益率
        elif target_status == 5 or target_status == 6:
            # 更新收益率
            self.current_trading_record.trading_yield = (close_price - self.current_trading_record.buy_price) / self.current_trading_record.buy_price
            self.update_available_balance(target_status, close_price, self.current_trading_record.buy_count)
            self.sig_trading_yield_changed.emit(self.current_trading_record.trading_yield)    # 通知更新收益率


    def reset_trading_record(self, total_assets=10000, available_balance = 10000):
        self.logger.info("重置交易记录")
        self.current_trading_record = None

        self.total_assets = total_assets               # 总资产
        self.available_balance = available_balance     # 可用资金

        self.sig_total_assets_and_available_balance_changed.emit(self.total_assets, self.available_balance)
