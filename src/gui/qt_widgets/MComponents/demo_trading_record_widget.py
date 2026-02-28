from PyQt5 import uic
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from pathlib import Path

class DemoTradingRecordWidget(QWidget):
    sig_btn_return_clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def setup_ui(self):
        ui_file = Path(__file__).parent / "DemoTradingRecordWidget.ui"
        
        # 检查文件是否存在
        if not ui_file.exists():
            raise FileNotFoundError(
                f"找不到UI文件: {ui_file.absolute()}\n"
                f"当前工作目录: {Path.cwd()}"
            )
        
        uic.loadUi(str(ui_file), self)

    def init_para(self):
        pass

    def init_ui(self):
        self.setup_ui()
        self.reset_trading_record()

    def init_connect(self):
        self.btn_return.clicked.connect(self.slot_btn_return_clicked)

    def reset_trading_record(self):
        self.label_name.setText("--")
        self.label_code.setText("--")

        self.label_order_buy_time.setText("--")
        self.label_order_buy_cancel_time.setText("--")

        self.label_buy_time.setText("--")
        self.label_buy_price.setText("--")
        self.label_buy_count.setText("--")
        self.label_buy_amount.setText("--")

        self.label_order_sell_time.setText("--")
        self.label_order_sell_cancel_time.setText("--")

        self.label_sell_time.setText("--")
        self.label_sell_price.setText("--")
        self.label_sell_count.setText("--")
        self.label_sell_amount.setText("--")

        self.label_status.setText("--")
        self.label_trading_income.setText("--")
        self.label_trading_yield.setText("--")

    def update_trading_record(self, trading_record):
        status = trading_record.status
        self.label_name.setText(trading_record.name)
        self.label_code.setText(trading_record.code)

        self.label_order_buy_time.setText(trading_record.pending_order_buy_date_time)
        self.label_order_buy_cancel_time.setText(trading_record.pending_order_buy_cancel_date_time)

        self.label_order_sell_time.setText(trading_record.pending_order_sell_date_time)


        self.label_order_sell_cancel_time.setText(trading_record.pending_order_sell_cancel_date_time)

        self.label_buy_time.setText(trading_record.buy_date_time)
        self.label_buy_price.setText(str(trading_record.buy_price))
        self.label_buy_count.setText(str(trading_record.buy_count))
        self.label_buy_amount.setText(str(trading_record.buy_amount))

        self.label_trading_yield.setText(str(trading_record.trading_yield))

        self.label_sell_time.setText(trading_record.sell_date_time)
        self.label_sell_price.setText(str(trading_record.sell_price))
        self.label_sell_count.setText(str(trading_record.sell_count))
        self.label_sell_amount.setText(str(trading_record.sell_amount))

        self.label_trading_yield.setText(f"{trading_record.trading_yield * 100:.2f}%")

        if status == 6:
            self.label_trading_income.setText(f"{trading_record.sell_amount - trading_record.buy_amount:.2f}")

        self.label_status.setText(trading_record.get_status_text())

    def slot_btn_return_clicked(self):
        self.sig_btn_return_clicked.emit()
