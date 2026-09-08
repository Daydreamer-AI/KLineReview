# coding:utf-8
import sys
from enum import Enum

from PyQt5.QtCore import QLocale
from gui.qt_widgets.MComponents.qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, RangeConfigItem, RangeValidator,
                            FolderListValidator, Theme, FolderValidator, ConfigSerializer, __version__)

from common.paths import get_config_file


class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()


class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000


class Config(QConfig):
    """ Config of application """

    # folders
    musicFolders = ConfigItem(
        "Folders", "LocalMusic", [], FolderListValidator())
    downloadFolder = ConfigItem(
        "Folders", "Download", "app/download", FolderValidator())

    # main window
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart=True)

    # Material
    blurRadius  = RangeConfigItem("Material", "AcrylicBlurRadius", 15, RangeValidator(0, 40))

    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "CheckUpdateAtStartUp", True, BoolValidator())

    def get_theme_color(self):
        '''获取主题色'''
        return self.get(self.themeColor)

    plot_widget_background = {
            Theme.AUTO: 'w',
            Theme.LIGHT: 'w',
            Theme.DARK: '#20201E',
        }

    def get_plot_widget_background_color(self, theme):
        return self.plot_widget_background[theme]


YEAR = 2026
AUTHOR = "牛马不是马"
VERSION = "1.0.0"
HELP_URL = "https://github.com/Daydreamer-AI/KLineReview"
REPO_URL = "https://github.com/Daydreamer-AI/KLineReview"
EXAMPLE_URL = "https://github.com/Daydreamer-AI/KLineReview"
FEEDBACK_URL = "https://github.com/Daydreamer-AI/KLineReview"
RELEASE_URL = "https://github.com/Daydreamer-AI/KLineReview"
ZH_SUPPORT_URL = "https://github.com/Daydreamer-AI/KLineReview"
EN_SUPPORT_URL = "https://github.com/Daydreamer-AI/KLineReview"


cfg = Config()
cfg.themeMode.value = Theme.AUTO
qconfig.load(str(get_config_file()), cfg)
