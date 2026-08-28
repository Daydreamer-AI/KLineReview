# coding: utf-8
"""
qfluentwidgets 提升控件（promoted widget）共享注册辅助模块。

背景
----
PyQt5 的 uic 在解析 .ui 中"提升的"自定义控件时，是按 <header> 声明的**裸模块名**
直接 __import__ 的（见 objcreator 的 header2module：把 '/' 换成 '.'、去掉 '.h'）。

qfluentwidgets 是标准的包布局（common/components/window 等子包），内部大量使用
相对导入，例如 calendar_picker.py 里的 "from ...common.style_sheet import FluentStyleSheet"。
这些相对导入只有在模块**作为包的一部分**被加载时才有效。

如果某个控件所在的子目录（比如 .../components/date_time）被裸加进 sys.path，
uic 就会把该 .py 当**顶层模块**加载（没有父包），其内部相对导入随即报错：

    ImportError: attempted relative import with no known parent package

解决办法
--------
1) 保证 qfluentwidgets 以完整包路径加载（使 __package__ 正确）；
2) 把已按包路径加载好的模块对象，再注册到 sys.modules 的同名"裸键"上，
   这样 uic 的裸名 __import__ 会命中同一个（包内）模块对象。

使用方式
--------
在调用 uic.loadUi(...) 之前（模块导入期即可），调用

    ensure_promoted_widgets()

它内部会遍历 PROMOTED_WIDGET_MODULES，对每个 (裸名, 完整包路径) 执行上面的两步。
以后要提升新的 qfluentwidgets 控件，只需在 PROMOTED_WIDGET_MODULES 里加一行：
    ("<裸名，与 .ui 的 <header> 完全一致>", "<完整包路径>")
例如提升 ComboBox：("combo_box", "gui.qt_widgets.MComponents.qfluentwidgets.components.widgets.combo_box")

注意：sys.modules 里的"裸名"必须和 .ui 文件 <header> 里写的名字**完全一致**，
uic 才会用这个键查找到正确的模块。
"""

import importlib
import sys

# 项目内 qfluentwidgets 包的根导入路径（去掉最后一个模块段）。
_QFW_PKG = "gui.qt_widgets.MComponents.qfluentwidgets"

# 需要为 uic 提升控件注册的"裸名 -> 完整包路径"映射。
# 裸名 = .ui 中 <header> 声明的名字；完整包路径 = 该控件的真实包内模块。
PROMOTED_WIDGET_MODULES = {
    "calendar_picker": _QFW_PKG + ".components.date_time.calendar_picker",
    "calendar_view":  _QFW_PKG + ".components.date_time.calendar_view",
    "date_picker":     _QFW_PKG + ".components.date_time.date_picker",
    "fast_calendar_view": _QFW_PKG + ".components.date_time.fast_calendar_view",
    "picker_base":     _QFW_PKG + ".components.date_time.picker_base",
    "time_picker":     _QFW_PKG + ".components.date_time.time_picker",

    "color_dialog":     _QFW_PKG + ".components.dialog_box.color_dialog",
    "dialog":          _QFW_PKG + ".components.dialog_box.dialog",
    "folder_list_dialog": _QFW_PKG + ".components.dialog_box.folder_list_dialog",
    "mask_dialog_base": _QFW_PKG + ".components.dialog_box.mask_dialog_base",
    "message_box_base": _QFW_PKG + ".components.dialog_box.message_box_base",
    "message_dialog":  _QFW_PKG + ".components.dialog_box.message_dialog",

    "expand_layout":   _QFW_PKG + ".components.layout.expand_layout",
    "flow_layout":     _QFW_PKG + ".components.layout.flow_layout",
    "v_box_layout":     _QFW_PKG + ".components.layout.v_box_layout",

    "acrylic_combo_box": _QFW_PKG + ".components.material.acrylic_combo_box",
    "acrylic_flyout":    _QFW_PKG + ".components.material.acrylic_flyout",
    "acrylic_line_edit": _QFW_PKG + ".components.material.acrylic_line_edit",
    "acrylic_menu":      _QFW_PKG + ".components.material.acrylic_menu",
    "acrylic_tool_tip":  _QFW_PKG + ".components.material.acrylic_tool_tip",
    "acrylic_widget":    _QFW_PKG + ".components.material.acrylic_widget",

    "breadcrumb":       _QFW_PKG + ".components.navigation.breadcrumb",
    "navigation_bar":   _QFW_PKG + ".components.navigation.navigation_bar",
    "navigation_interface": _QFW_PKG + ".components.navigation.navigation_interface",
    "navigation_panel": _QFW_PKG + ".components.navigation.navigation_panel",
    "navigation_widget": _QFW_PKG + ".components.navigation.navigation_widget",
    "pivot":             _QFW_PKG + ".components.navigation.pivot",
    "segmented_widget":  _QFW_PKG + ".components.navigation.segmented_widget",

    "custom_color_setting_card": _QFW_PKG + ".components.settings.custom_color_setting_card",
    "expand_setting_card":     _QFW_PKG + ".components.settings.expand_setting_card",
    "folder_list_setting_card": _QFW_PKG + ".components.settings.folder_list_setting_card",
    "options_setting_card": _QFW_PKG + ".components.settings.options_setting_card",
    "setting_card":     _QFW_PKG + ".components.settings.setting_card",
    "setting_card_group": _QFW_PKG + ".components.settings.setting_card_group",

    "acrylic_label": _QFW_PKG + ".components.widgets.acrylic_label",
    "button":         _QFW_PKG + ".components.widgets.button",
    "card_widget":     _QFW_PKG + ".components.widgets.card_widget",
    "check_box":       _QFW_PKG + ".components.widgets.check_box",
    "combo_box":       _QFW_PKG + ".components.widgets.combo_box",
    "command_bar":     _QFW_PKG + ".components.widgets.command_bar",
    "cycle_list_widget": _QFW_PKG + ".components.widgets.cycle_list_widget",
    "flip_view":       _QFW_PKG + ".components.widgets.flip_view",
    "flyout":           _QFW_PKG + ".components.widgets.flyout",
    "frameless_window": _QFW_PKG + ".components.widgets.frameless_window",
    "icon_widget":       _QFW_PKG + ".components.widgets.icon_widget",
    "info_badge":       _QFW_PKG + ".components.widgets.info_badge",
    "info_bar":         _QFW_PKG + ".components.widgets.info_bar",
    "label":          _QFW_PKG + ".components.widgets.label",
    "line_edit":       _QFW_PKG + ".components.widgets.line_edit",
    "list_view":         _QFW_PKG + ".components.widgets.list_view",
    "menu":             _QFW_PKG + ".components.widgets.menu",
    "model_combo_box":   _QFW_PKG + ".components.widgets.model_combo_box",
    "pips_pager":         _QFW_PKG + ".components.widgets.pips_pager",
    "progress_bar":       _QFW_PKG + ".components.widgets.progress_bar",
    "progress_ring":       _QFW_PKG + ".components.widgets.progress_ring",
    "scroll_area":         _QFW_PKG + ".components.widgets.scroll_area",
    "scroll_bar":         _QFW_PKG + ".components.widgets.scroll_bar",
    "separator":         _QFW_PKG + ".components.widgets.separator",
    "slider":           _QFW_PKG + ".components.widgets.slider",
    "spin_box":          _QFW_PKG + ".components.widgets.spin_box",
    "stacked_widget":     _QFW_PKG + ".components.widgets.stacked_widget",
    "state_tool_tip":     _QFW_PKG + ".components.widgets.state_tool_tip",
    "switch_button":      _QFW_PKG + ".components.widgets.switch_button",
    "tab_view":          _QFW_PKG + ".components.widgets.tab_view",
    "table_view":         _QFW_PKG + ".components.widgets.table_view",
    "teaching_tip":       _QFW_PKG + ".components.widgets.teaching_tip",
    "tool_tip":           _QFW_PKG + ".components.widgets.tool_tip",
    "tree_view":          _QFW_PKG + ".components.widgets.tree_view",
    # ---- 后续要提升新的 qfluentwidgets 控件时，在这里按同样的键值对加一行 ----
    # "switch_button":   _QFW_PKG + ".components.widgets.switch_button",
    # "line_edit":       _QFW_PKG + ".components.widgets.line_edit",
}


def make_promoted_widget_module(ui_header):
    """把 .ui 里 <header> 的裸名转换成对应的完整包路径。

    目前按约定映射到 qfluentwidgets 包内；具体键值见 PROMOTED_WIDGET_MODULES。
    若在映射中找不到则抛出 KeyError，提示用户先在 PROMOTED_WIDGET_MODULES 登记。
    """
    module_path = PROMOTED_WIDGET_MODULES.get(ui_header)
    if module_path is None:
        raise KeyError(
            f"未在 PROMOTED_WIDGET_MODULES 中登记提升控件“{ui_header}”。"
            f"请先补充一行：(\"{ui_header}\", \"<完整包路径>\")，"
            f"例如：(\"{ui_header}\", \"{_QFW_PKG}.components.widgets.{ui_header.replace('/', '.')}\")"
        )
    return module_path


def _register(ui_header, module_path):
    """按完整包路径加载模块并注册到 sys.modules 的裸名键上。"""
    module = importlib.import_module(module_path)  # 作为包的一部分加载，相对导入可用
    sys.modules.setdefault(ui_header, module)      # 让 uic 的裸名 __import__ 命中它


def ensure_promoted_widgets():
    """一次性注册全部已登记的提升控件。幂等、可重复调用。"""
    for ui_header, module_path in PROMOTED_WIDGET_MODULES.items():
        _register(ui_header, module_path)


# 模块被导入时即完成注册，供 uic.loadUi 使用。
ensure_promoted_widgets()