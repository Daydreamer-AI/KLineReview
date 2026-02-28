# base_chart_widget.py
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
import numpy as np

from manager.period_manager import TimePeriod

# 需要发送到外部控件（如BaseIndicatorWidget的父控件或其他子类）时，使用全局信号
# 问题：当存在多个BaseIndicatorWidget（及其子类）对象连接同一个全局信号时，触发全局信号后所有槽函数都会响应。解决方案：传递self，在槽函数中判断，不是当前实例，则不响应。
class SignalManager(QObject):
    # 全局信号管理器
    global_update_labels = pyqtSignal(object, int)
    global_show_overview_label = pyqtSignal(object, int, float, float, float, bool)

    # 若是只需要处理当前视图鼠标移动事件，可放在父类中处理（如：只在触发鼠标事件的视图中显示y轴水平、y轴标签，而所有视图都需显示x轴垂直线，则放在子类中处理）
    global_sig_v_line_moved = pyqtSignal(object, float)

    global_sig_hide_v_line = pyqtSignal()

    global_reset_labels = pyqtSignal(object)

# 创建全局信号管理器实例
signal_manager = SignalManager()

class BaseIndicatorWidget(QWidget):
    # 定义自定义信号。问题：虽然信号属于类，但是连接却是和示例绑定的，因此无法实现父类中触发信号，传递到所有子类槽函数响应。实际上只有触发信号的子类示例的槽函数响应。
    # sig_update_labels = pyqtSignal(int)  # 点击信号

    # sig_v_line_moved = pyqtSignal(float)

    # 类变量，用于存储所有实例的垂直线引用
    # _shared_v_lines = {}
    # _shared_h_lines = {}

    # _shared_x_labels = {}
    # _shared_left_y_labels = {}

    def __init__(self, data, type=0, parent=None):
        super(BaseIndicatorWidget, self).__init__(parent)

        self.item = None
        self.df_data = None
        self.logger = None
        self.plot_widget = None
        self.type = type   # 0：行情，1：策略，2：复盘
        self.period = TimePeriod.DAY
        
        self.init_para(data)    # 注意：若子类中有重写这三个init_函数，必须显示调用父类对应的init_函数，否则会覆盖掉父类的初始化处理。
        self.init_ui()
        self.init_connect()

    # 清理资源
    def __del__(self):
        # 从共享字典中移除
        chart_name = self.get_chart_name()
        self.logger.info(f"开始清理类型为{self.type}的{chart_name}及其资源")
        # if chart_name in BaseIndicatorWidget._shared_v_lines:
        #     del BaseIndicatorWidget._shared_v_lines[chart_name]

        # if chart_name in BaseIndicatorWidget._shared_h_lines:
        #     del BaseIndicatorWidget._shared_h_lines[chart_name]

        # if chart_name in BaseIndicatorWidget._shared_x_labels:
        #     del BaseIndicatorWidget._shared_x_labels[chart_name]
    
    def init_ui(self):
        # 加载UI文件（子类需提供）
        uic.loadUi(self.get_ui_path(), self)
        
        layout = self.layout()
        if layout is None:
            self.logger.info("没有布局，创建一个")
            self.setLayout(QVBoxLayout())
            layout = self.layout()
            
        self.plot_widget = pg.PlotWidget()
        self.setup_plot_widget()
        layout.addWidget(self.plot_widget)
        self.draw()
    
    def setup_plot_widget(self):
        """设置plot widget的基本属性"""
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.getAxis('left').setWidth(60)
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setMouseEnabled(x=True, y=False)

        self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.PanMode)  # 平移模式
        
        # 设置坐标轴颜色
        self.plot_widget.getAxis('left').setPen(QtGui.QColor(110, 110, 110))
        self.plot_widget.getAxis('bottom').setPen(QtGui.QColor(110, 110, 110))
        self.plot_widget.getAxis('left').setTextPen(QtGui.QColor(110, 110, 110))
        self.plot_widget.getAxis('bottom').setTextPen(QtGui.QColor(110, 110, 110))

        # 添加十字线
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#808286', width=2, style=Qt.DashLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#808286', width=2, style=Qt.DashLine))
        self.v_line.setZValue(1000)
        self.h_line.setZValue(1000)

        chart_name = self.get_chart_name()
        # 将垂直线添加到共享列表
        # BaseIndicatorWidget._shared_v_lines[chart_name] = self.v_line
        # BaseIndicatorWidget._shared_h_lines[chart_name] = self.h_line

        main_viewbox = self.plot_widget.getViewBox()
        main_viewbox.addItem(self.v_line, ignoreBounds=True)
        main_viewbox.addItem(self.h_line, ignoreBounds=True)

        # 添加x轴标签
        self.x_label = pg.TextItem("", anchor=(0.5, 1))
        self.x_label.setZValue(1000)
        self.x_label.setFont(pg.QtGui.QFont("Arial", 9))
        self.x_label.setColor(pg.QtGui.QColor(0, 0, 0)) 
        
        # BaseIndicatorWidget._shared_x_labels[chart_name] = self.x_label
        main_viewbox.addItem(self.x_label, ignoreBounds=True)

        # 添加左y轴标签
        self.left_y_label = pg.TextItem("", anchor=(0, 0.5))
        self.left_y_label.setZValue(1000)
        self.left_y_label.setFont(pg.QtGui.QFont("Arial", 9))
        self.left_y_label.setColor(pg.QtGui.QColor(255, 0, 0))
        # BaseIndicatorWidget._shared_left_y_labels[chart_name] = self.left_y_label
        
        main_viewbox.addItem(self.left_y_label, ignoreBounds=True)

        # if self.get_chart_name() == "K线图":
        # self.logger.info(f"添加K线图概览标签")

        # self.label_overview = pg.TextItem("", anchor=(0.5, 0.5))
        # self.label_overview.setZValue(1000)
        
        # font = pg.QtGui.QFont("Arial", 10, pg.QtGui.QFont.Bold)
        # self.label_overview.setFont(font)
        
        # main_viewbox.addItem(self.label_overview, ignoreBounds=True)
        # self.label_overview.hide()

        self.hide_all_labels()

    def zoom_in(self, x_factor=0.8, y_factor=0.8):
        """放大视图"""
        viewbox = self.plot_widget.getViewBox()
        viewbox.scaleBy((x_factor, y_factor))  # 按0.8倍缩放，数值越小越放大

    def zoom_out(self, x_factor=1.2, y_factor=1.2):
        """缩小视图"""
        viewbox = self.plot_widget.getViewBox()
        viewbox.scaleBy((x_factor, y_factor))  # 按1.2倍缩放，数值越大越缩小

    def reset_zoom(self):
        """恢复到原始缩放状态"""
        # 方法1: 重新设置原始范围
        # self.set_axis_ranges()  # 调用您已有的设置轴范围方法
        
        # 方法2: 使用autoRange
        # viewbox = self.plot_widget.getViewBox()
        # viewbox.autoRange()

        # 方法3：使用自定义默认范围
        self.auto_scale_to_latest(120)

    def get_current_range(self):
        """获取当前视图范围"""
        return self.plot_widget.viewRange()  # 返回 [[x_min, x_max], [y_min, y_max]]

    
    def update_data(self, data):
        # self.logger.info(f"更新数据{self.get_chart_name()}, data长度：{len(data)}")
        self.df_data = data
        self.update_widget_labels()
        self.draw()
        self.update()

    def update_widget_labels(self):
        """钩子方法：子类可以重写此方法添加额外的标签更新"""
        pass
    
    def get_data(self):
        return self.df_data
    
    def get_plot_widget(self):
        return self.plot_widget
    
    def get_date_text_with_style(self, index):
        try:
            # 检查索引是否有效
            if index < 0 or index >= len(self.df_data):
                return ""
            
            # 使用 .loc 访问器获取指定行的 时间列数据
            s_col_name = 'date'
            if TimePeriod.is_minute_level(self.period):
                s_col_name = 'time'
                
            date_str = self.df_data.loc[index, s_col_name]
            label_main_x_text_with_style = '<div style="color: black; background-color: white; border: 3px solid black; padding: 2px;">{}</div>'.format(date_str)
            return label_main_x_text_with_style
        except Exception as e:
            self.logger.error(f"获取日期文本时出错: {e}")
            return ""
        
    def get_left_y_text_with_style(self, y_val):
        left_y_label_text = f"{y_val:.2f}"
        left_y_label_text_with_style = '<div style="color: black; background-color: white; border: 3px solid black; padding: 2px;">{}</div>'.format(left_y_label_text)
        return left_y_label_text_with_style
    
    def draw(self):
        if self.df_data is None or self.df_data.empty:
            self.logger.info(f"数据为空，无法绘制{self.get_chart_name()}")
            return
            
        if not self.validate_data():
            self.logger.warning(f"缺少必要的数据列来绘制{self.get_chart_name()}")
            return
        
        self.plot_widget.clear()
        
        self.create_and_add_item()
        self.set_axis_ranges()

        # 调用钩子方法，允许子类添加额外绘制逻辑
        self.additional_draw()

    def additional_draw(self):
        """钩子方法：子类可以重写此方法添加额外的绘制逻辑"""
        pass
    
    def get_ui_path(self):
        """返回UI文件路径"""
        raise NotImplementedError("子类必须实现 get_ui_path 方法")
    
    def validate_data(self):
        """验证数据是否满足要求"""
        raise NotImplementedError("子类必须实现 validate_data 方法")
    
    def create_and_add_item(self):
        """创建并添加图表项"""
        raise NotImplementedError("子类必须实现 create_and_add_item 方法")
    
    def set_axis_ranges(self):
        """设置坐标轴范围"""
        raise NotImplementedError("子类必须实现 set_axis_ranges 方法")
    
    def get_chart_name(self):
        """返回图表名称"""
        raise NotImplementedError("子类必须实现 get_chart_name 方法")
    
    def init_para(self, data):
        """初始化参数"""
        raise NotImplementedError("子类必须实现 init_para 方法")
    
    def init_connect(self):
        """初始化信号连接"""
        # 连接到全局信号
        signal_manager.global_update_labels.connect(self.slot_global_update_labels)
        signal_manager.global_show_overview_label.connect(self.slot_global_show_overview_label)

        signal_manager.global_sig_v_line_moved.connect(self.slot_v_line_mouse_moved)
        signal_manager.global_sig_hide_v_line.connect(self.slot_hide_v_line)

        signal_manager.global_reset_labels.connect(self.slot_global_reset_labels)

        self.addtional_connect()

    def addtional_connect(self):
        # raise NotImplementedError("子类必须实现 addtional_connect 方法")
        pass

    def set_period(self, period):
        self.period = period

    def get_period(self):
        return self.period

    def get_visible_data_range(self):
        '''
        获取当前视图范围内X轴对应的数据索引范围和数据
        返回: (visible_data, x_min, x_max) 或 (None, None, None) 如果无效
        '''
        if self.plot_widget is None or self.df_data is None or self.df_data.empty:
            return None, None, None
        
        # 获取当前X轴的视图范围
        view_range = self.plot_widget.viewRange()
        x_range = view_range[0]  # X轴范围 [min, max]
        
        # 确定可视范围内的数据索引
        x_min, x_max = int(max(0, x_range[0])), int(min(len(self.df_data), x_range[1]))
        
        # 确保范围有效
        if x_min >= len(self.df_data) or x_max <= 0 or x_min >= x_max:
            return None, None, None
            
        # 获取可视范围内的数据
        visible_data = self.df_data.iloc[x_min:x_max]
        
        if visible_data.empty:
            return None, None, None
            
        return visible_data, x_min, x_max

    def slot_range_changed(self):
        '''当视图范围改变时调用'''
        # y轴坐标值同步
        # 获取当前x轴视图范围内的数据


        # 根据当前可视范围内的数据的最大、最小值调整Y轴坐标值范围

        # 重新设置Y轴刻度
        pass

    def set_default_view_range(self, visible_days=None):
        """
        设置默认视图范围，显示最新的数据，最后一个数据显示在视图左边2/3的位置，为右边预留1/3的空白
        :param visible_days: 默认显示的天数
        """
        if self.plot_widget is None or self.df_data is None or self.df_data.empty:
            return
        
        total_days = len(self.df_data)
        if visible_days is None:
            # 显示所有数据，最后一个数据显示在视图左边2/3位置
            display_range = total_days / (2/3)  # 总视图范围，使得total_days占据2/3
            start_index = 0
            end_index = display_range  # 结束位置要给右侧留出1/3空白
            self.plot_widget.setXRange(start_index, end_index, padding=0)
        else:
            # 显示指定天数的数据
            if total_days <= visible_days:
                # 数据量不足指定天数
                display_range = visible_days / (2/3)
                start_index = 0
                end_index = display_range
                self.plot_widget.setXRange(start_index, end_index, padding=0)
            else:
                # 数据量超过指定天数，显示最新的visible_days天数据
                end_index = total_days
                # 计算起始索引，使得最后一天位于视图的2/3位置
                display_range = visible_days / (2/3)
                start_index = end_index - visible_days  # 显示visible_days根K线
                end_index = start_index + display_range  # 但视图范围要给右侧留1/3空白
                self.plot_widget.setXRange(start_index, end_index, padding=0)

    def auto_scale_to_latest(self, visible_days=None):
        """
        自动缩放到最新数据并触发Y轴自适应
        :param visible_days: 默认显示的天数
        """
        self.set_default_view_range(visible_days)
        # 触发Y轴范围调整
        self.slot_range_changed()

    def slot_mouse_moved(self, pos):
        """鼠标移动事件处理"""
        if self.plot_widget is None or self.df_data is None or self.df_data.empty:
            return

        # if widget_source is not None:
        #     # self.logger.info(f"正在处理{self.get_chart_name()}鼠标移动响应，来源：{widget_source.get_chart_name()}")
        #     widget_source_chart_name = widget_source.get_chart_name()
        # else:
        #     # self.logger.info(f"widget_source is not None")
        #     return
        
        # chart_name = self.get_chart_name()

        if self.plot_widget.sceneBoundingRect().contains(pos):
            view_range = self.plot_widget.getViewBox().viewRange()
            mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
            x_val = mouse_point.x()
            y_val = mouse_point.y()

            # self.logger.info(f"鼠标位置：x={x_val}, y={y_val}")

            # 方式一：类变量存储水平线，父类中统一处理。问题：无法复用。当创建多个BaseIndicatorWidget时绘制会有问题。
            # self.logger.info(f"当前存储的水平线：\n{BaseIndicatorWidget._shared_h_lines.keys()}")
            # for chart_name, h_line in BaseIndicatorWidget._shared_h_lines.items():
            #     if chart_name == widget_source_chart_name:
            #         h_line.setPos(y_val)
            #         h_line.show()
            #     else:
            #         h_line.hide()

            # 方式二：使用示例变量存储。问题：无法在示例的移动事件响应中处理其他图表的水平线。
            # if chart_name == widget_source_chart_name:
            self.h_line.setPos(y_val)
            self.h_line.show()
            # else:
            #     self.h_line.hide()

            # 方式三：信号通知。自定义信号，移动响应中触发信号，由子类自行绘制。
            # signal_manager.global_sig_h_line_moved.emit(y_val, widget_source)

            # 只显示鼠标所在图表的左y轴标签
            # for chart_name, left_y_label in BaseIndicatorWidget._shared_left_y_labels.items():
            #     if chart_name == widget_source_chart_name:
            #         # self.logger.info(f"正在显示{chart_name}的左边Y轴标签, y_val={y_val}")
            #         left_y_label.setHtml(self.get_left_y_text_with_style(y_val))
            #         left_y_label.setPos(view_range[0][0], y_val)
            #         left_y_label.show()

            # if chart_name == widget_source_chart_name:
            self.left_y_label.setHtml(self.get_left_y_text_with_style(y_val))
            self.left_y_label.setPos(view_range[0][0], y_val)
            self.left_y_label.show()


            bar_centers = list(range(len(self.df_data)))
            
            closest_index = None
            min_distance = float('inf')
            
            for i, center in enumerate(bar_centers):
                distance = abs(center - x_val)
                if distance <= 0.25 / 2:
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
            
            closest_x = None    # 这里closest_x其实和closest_index一样，都是从0开始
            if closest_index is not None:
                
                closest_x = bar_centers[closest_index]

                # 显示所有图表的垂直线
                # for chart_name, v_line in BaseIndicatorWidget._shared_v_lines.items():
                #     # v_line.hide()
                #     v_line.setPos(closest_x)
                #     v_line.show()
                # self.v_line.setPos(closest_x)
                # self.v_line.show()
                signal_manager.global_sig_v_line_moved.emit(self, closest_x)
                # self.sig_v_line_moved.emit(closest_x)

                # 只显示鼠标所在图表的X轴标签
                # for chart_name, v_line in BaseIndicatorWidget._shared_x_labels.items():
                #     if chart_name == widget_source_chart_name:
                #         x_label = BaseIndicatorWidget._shared_x_labels[chart_name]
                #         x_label.setHtml(self.get_date_text_with_style(closest_index))
                #         x_label.setPos(closest_x, view_range[1][0])
                #         x_label.show()
                # if chart_name == widget_source_chart_name:
                self.x_label.setHtml(self.get_date_text_with_style(closest_index))
                self.x_label.setPos(closest_x, view_range[1][0])
                self.x_label.show()
                        
                # 更新所有图表父控件的指标标签值
                # self.sig_update_labels.emit(closest_index)
                signal_manager.global_update_labels.emit(self, closest_index)

                # 在k线图图表中显示概览标签
                # if chart_name == "K线图":
                # x_pos = view_range[0][1]
                # y_pos = view_range[1][1]
                # if x_pos <= len(self.df_data) - 3:
                #     x_pos = view_range[0][0]

                # k线图中显示标签预览
                signal_manager.global_show_overview_label.emit(self, closest_index, y_val, closest_x, y_val, True)

            else:
                # signal_manager.global_show_overview_label.emit(closest_x, closest_index, y_val, False)
                # self.hide_all_labels()
                pass

        else:
            # self.logger.info(f"鼠标位置超出图表范围")
            self.hide_all_labels()

    def additional_mouse_moved(self, closest_x):
        """钩子方法：子类可以重写此方法添加鼠标移动处理"""
        pass

    def hide_all_labels(self):
        # for chart_name, v_line in BaseIndicatorWidget._shared_v_lines.items():
        #     v_line.hide()
        # self.v_line.hide()
        signal_manager.global_sig_hide_v_line.emit()

        # for chart_name, h_line in BaseIndicatorWidget._shared_h_lines.items():
        #     h_line.hide()
        self.h_line.hide()

        self.x_label.hide()
        self.left_y_label.hide()

        signal_manager.global_show_overview_label.emit(self, 0, 0, 0, 0, False)

        signal_manager.global_reset_labels.emit(self)

        self.plot_widget.prepareGeometryChange()    # 手动刷新避免十字线重影
        self.plot_widget.update()

    def enterEvent(self, event):
        """
        当鼠标进入控件时的处理
        """
        super().enterEvent(event)

    def leaveEvent(self, event):
        """
        当鼠标离开控件时，隐藏所有标签和十字线
        """
        self.hide_all_labels()
        super().leaveEvent(event)

    def slot_global_update_labels(self, sender, closest_index):
        pass

    def slot_global_reset_labels(self, sender):
        pass

    def slot_global_show_overview_label(self, sender, index, y_val, x_pos, y_pos, bool_show=True):
        pass

    def slot_v_line_mouse_moved(self, sender, x_pos):
        pass

    def slot_hide_v_line(self):
        self.v_line.hide()


