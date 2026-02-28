from pathlib import Path
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt

import pyqtgraph as pg

class IncomeChartWidget(QWidget):
    def __init__(self, parent=None):
        super(IncomeChartWidget, self).__init__(parent)

        self.init_para()
        self.init_ui()
        self.init_connect()
    
    def init_para(self):
        self.list_data = None       # 图表数据
        self.chart_x_data = None    # 图表x轴坐标值
        self.chart_y_data = None    # 图表y轴坐标值
        self.chart_info = []        # 存储每个点的详细信息

    def init_ui(self):
        self.setup_ui()

        # self.label_total_yield.setStyleSheet("color: #E5403C; font-weight: bold;")

        self.plot_widget = pg.PlotWidget()
        # 设置尺寸策略
        # self.plot_widget.setSizePolicy(
        #     QSizePolicy.Preferred,  # 水平策略
        #     QSizePolicy.Expanding   # 垂直策略
        # )
        self.verticalLayout_chart.addWidget(self.plot_widget)
        self.setup_plot_style()

        self.update_chart([])

    def init_connect(self):
        self.plot_widget.scene().sigMouseMoved.connect(self.slot_mouse_moved)

    def setup_ui(self):
        ui_file = Path(__file__).parent / "IncomeChartWidget.ui"
        
        # 检查文件是否存在
        if not ui_file.exists():
            raise FileNotFoundError(
                f"找不到UI文件: {ui_file.absolute()}\n"
                f"当前工作目录: {Path.cwd()}"
            )
        
        uic.loadUi(str(ui_file), self)

    def setup_plot_style(self):
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.plot_widget.setMouseEnabled(x=True, y=False)

        self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.PanMode)  # 平移模式

        # 初始化主图表十字线
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#808286', width=2, style=Qt.DashLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#808286', width=2, style=Qt.DashLine))
        self.v_line.setZValue(1000)
        self.h_line.setZValue(1000)
        
        main_viewbox = self.plot_widget.getViewBox()
        # 明确添加到主视图
        main_viewbox.addItem(self.v_line, ignoreBounds=True)
        main_viewbox.addItem(self.h_line, ignoreBounds=True)

        # 添加左y轴标签
        self.left_y_label = pg.TextItem("", anchor=(0, 0.5))
        self.left_y_label.setZValue(1000)
        self.left_y_label.setFont(pg.QtGui.QFont("Arial", 9))
        self.left_y_label.setColor(pg.QtGui.QColor(255, 0, 0))
    
        main_viewbox.addItem(self.left_y_label, ignoreBounds=True)

        # 初始化主图表标签（优化样式）
        self.label_main = pg.TextItem("", anchor=(0, 1))
        self.label_main.setZValue(1000)
        
        # 预设标签样式
        font = pg.QtGui.QFont("Arial", 10, pg.QtGui.QFont.Bold)
        self.label_main.setFont(font)
        
        main_viewbox.addItem(self.label_main, ignoreBounds=True)

        self.hide_all_plot_widget_labels()

    def hide_all_plot_widget_labels(self):
        # 隐藏主图表的十字线和标签
        self.v_line.hide()
        self.h_line.hide()

        # 隐藏左y轴标签
        self.left_y_label.hide()

        self.label_main.hide()

    def get_left_y_text_with_style(self, y_val):
        left_y_label_text = f"{y_val:.2f}"
        left_y_label_text_with_style = '<div style="color: black; background-color: white; border: 3px solid black; padding: 2px;">{}</div>'.format(left_y_label_text)
        return left_y_label_text_with_style

    def update_data(self, list_data):
        self.list_data = list_data

        # 计算总收益率
        total_yield = 0.0
        win_count = 0  # 获胜交易次数
        total_completed_trades = 0  # 完成的交易总数

        for record in list_data:
            if record.status == 6 and record.sell_date_time is not None:  # 交易完成
                single_yield = record.trading_yield * 100  # 转换为百分比
                total_yield += single_yield
                
                # 统计获胜次数（收益率大于0）
                if single_yield > 0:
                    win_count += 1
                
                total_completed_trades += 1

        # 计算胜率
        win_rate = 0.0
        if total_completed_trades > 0:
            win_rate = (win_count / total_completed_trades) * 100  # 转换为百分比

        # 更新标签显示
        if total_yield > 0:
            self.label_total_yield.setStyleSheet("color: #E5403C; font-weight: bold;")
        elif total_yield < 0:
            self.label_total_yield.setStyleSheet("color: #1BCB34; font-weight: bold;")
        else:
            self.label_total_yield.setStyleSheet("color: black;")

        self.label_total_yield.setText(f"{total_yield:.2f}%")

        self.label_win_rate.setText(f"{win_rate:.2f}%")
        self.label_win_rate.setStyleSheet("color: purple;")

        self.update_chart(list_data)

    def update_chart(self, list_data):
        # 清除之前的图表数据
        self.plot_widget.clear()
        
        # 准备绘制数据
        x_data = []  # X轴数据（序号）
        y_data = []  # Y轴数据（累计总收益率百分比）
        
        # 存储额外信息用于鼠标交互
        self.chart_info = []  # 存储每个点的详细信息
        
        # 添加起始点（初始收益为0）
        x_data.append(0)  # X轴从0开始
        y_data.append(0.0)  # 初始总收益为0%
        
        # 存储起始点信息
        start_info = {
            'x': 0,
            'single_yield': 0.0,  # 单次收益率
            'cumulative_yield': 0.0,  # 累计总收益率
            'win_rate': 0.0,  # 当前胜率
            'trade_index': -1,  # 交易索引（-1表示起始点）
            'record': None  # 交易记录对象
        }
        self.chart_info.append(start_info)
        
        # 计算累计总收益率和胜率
        cumulative_yield = 0.0
        win_count = 0  # 获胜交易次数
        total_trades = 0  # 总交易次数
        
        # 按交易顺序处理记录
        for record in list_data:
            # 只有交易完成的记录才计算收益
            if record.status == 6 and record.sell_date_time is not None:
                # 获取单次交易的收益率
                single_yield = record.trading_yield * 100
                
                # 累计总收益率（简单累加，实际应用中可能需要考虑复利）
                cumulative_yield += single_yield
                
                # 更新胜率统计
                total_trades += 1
                if single_yield > 0:
                    win_count += 1
                
                # 计算当前胜率
                current_win_rate = 0.0
                if total_trades > 0:
                    current_win_rate = (win_count / total_trades) * 100
                
                # 添加当前点的数据
                x_value = len(x_data)  # 当前点的序号
                x_data.append(x_value)
                y_data.append(cumulative_yield)
                
                # 存储当前点的详细信息
                point_info = {
                    'x': x_value,
                    'single_yield': single_yield,  # 单次收益率
                    'cumulative_yield': cumulative_yield,  # 累计总收益率
                    'win_rate': current_win_rate,  # 当前胜率
                    'trade_index': total_trades - 1,  # 交易索引
                    'record': record  # 交易记录对象
                }
                self.chart_info.append(point_info)

        # 保存X轴和Y轴数据用于鼠标交互
        self.chart_x_data = x_data
        self.chart_y_data = y_data
        
        # 绘制收益曲线
        if x_data and y_data:
            pen = pg.mkPen(color='b', width=2)
            self.plot_widget.plot(x=x_data, y=y_data, pen=pen, symbol='o', symbolSize=6, symbolBrush='b')
            
            # 设置坐标轴标签
            self.plot_widget.setLabel('left', '总收益率', units='%')
            # self.plot_widget.setLabel('bottom', '交易序号')
            
            # 添加标题
            self.plot_widget.setTitle('总收益率曲线')
            
            # 动态设置Y轴范围，包含负值
            y_min = min(y_data)
            y_max = max(y_data)
            
            # 设置适当的裕量
            if y_min == y_max:  # 只有一个数据点的情况
                if y_min == 0:
                    y_min, y_max = -1, 1  # 默认范围
                else:
                    padding = abs(y_min) * 0.1
                    y_min -= padding
                    y_max += padding
            else:
                padding = abs(y_max - y_min) * 0.1
                y_min -= padding
                y_max += padding
            
            # 确保Y轴范围合理
            if y_min > 0:
                y_min = min(0, y_min)  # 保证包含0
            elif y_max < 0:
                y_max = max(0, y_max)  # 保证包含0
                
            self.plot_widget.setYRange(y_min, y_max)
            
            # 设置X轴范围
            x_min = min(x_data)
            x_max = max(x_data)
            
            if x_min == x_max:  # 只有一个数据点的情况
                x_min = 0  # X轴最小值不能小于0
                x_max = x_max + 1  # 保证有合适的范围
            else:
                x_padding = abs(x_max - x_min) * 0.1
                x_min = 0  # X轴最小值不能小于0
                x_max += x_padding  # 只增加上边界
                
            self.plot_widget.setXRange(x_min, x_max)

    def slot_mouse_moved(self, pos):
        if self.plot_widget is None or not hasattr(self, 'chart_x_data') or not self.chart_x_data:
            return
        
        if self.plot_widget.sceneBoundingRect().contains(pos):
            view_range = self.plot_widget.getViewBox().viewRange()
            mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
            x_val = mouse_point.x()
            y_val = mouse_point.y()

            self.h_line.setPos(y_val)
            self.h_line.show()

            self.left_y_label.setHtml(self.get_left_y_text_with_style(y_val))
            self.left_y_label.setPos(view_range[0][0], y_val)
            self.left_y_label.show()

            # 寻找最接近的X轴坐标
            closest_x = None
            closest_info = None
            min_distance = float('inf')

            for x_point in self.chart_x_data:
                distance = abs(x_point - x_val)
                tolerance = 0.5  # 可以根据需要调整容差
                if distance < min_distance and distance <= tolerance:
                    min_distance = distance
                    closest_x = x_point
                    # 找到对应的信息
                    for info in self.chart_info:
                        if info['x'] == x_point:
                            closest_info = info
                            break
            
            if closest_x is not None:
                self.v_line.setPos(closest_x)
                self.v_line.show()
                
                # 更新主标签显示详细信息
                if closest_info is not None:
                    # 构建详细信息文本，使用HTML格式设置样式
                    info_text = (
                        '<div style="background-color: white; border: 2px solid black; padding: 5px; border-radius: 5px;">'
                        f'<span style="color: black; font-weight: bold;">交易序号:</span> <span style="color: blue;">{closest_info["trade_index"] if closest_info["trade_index"] >= 0 else "起始点"}</span><br>'
                        f'<span style="color: black; font-weight: bold;">单次收益率:</span> <span style="color: {"#1BCB34" if closest_info["single_yield"] < 0 else "#E5403C"}; font-weight: bold;">{closest_info["single_yield"]:.2f}%</span><br>'
                        f'<span style="color: black; font-weight: bold;">累计总收益率:</span> <span style="color: {"#1BCB34" if closest_info["cumulative_yield"] < 0 else "#E5403C"}; font-weight: bold;">{closest_info["cumulative_yield"]:.2f}%</span><br>'
                        f'<span style="color: black; font-weight: bold;">当前胜率:</span> <span style="color: purple; font-weight: bold;">{closest_info["win_rate"]:.2f}%</span>'
                        '</div>'
                    )
                    
                    # 设置标签文本
                    self.label_main.setHtml(info_text)
                    self.label_main.setPos(closest_x, y_val)  # 位置在十字线交叉点
                    self.label_main.show()
            else:
                # 鼠标不在有效数据点附近时隐藏十字线和标签
                self.v_line.hide()
                self.label_main.hide()

        else:
            self.hide_all_plot_widget_labels()

    def leaveEvent(self, event):
        """
        当鼠标离开控件时，隐藏所有标签和十字线
        """
        self.hide_all_plot_widget_labels()
        super().leaveEvent(event)