import efinance as ef

# 股票代码
stock_code = '600519'
stock_data = ef.stock.get_quote_history(stock_code)
