# coding: utf-8
from enum import Enum

from gui.qt_widgets.MComponents.qfluentwidgets import FluentIconBase, getIconColor, Theme


class Icon(FluentIconBase, Enum):

    REVIEW = "Review"

    def path(self, theme=Theme.AUTO):
        return f":/images/icons/{self.value}_{getIconColor(theme)}.svg"
