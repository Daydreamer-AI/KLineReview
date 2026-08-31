# coding: utf-8
from enum import Enum

from gui.qt_widgets.MComponents.qfluentwidgets import FluentIconBase, getIconColor, Theme


class Icon(FluentIconBase, Enum):

    REVIEW = "Review"
    DICE = "dice"
    PLAY = "play_with_border"
    PAUSE = "pause_with_border"
    BACKWARD = "backward"
    FAST_BACKWARD = "fast_backward"
    FAST_BACKWARD_TO_HEAD = "fast_backward_to_the_head"
    FORWARD = "forward"
    FAST_FORWARD = "fast_forward"
    FAST_FORWARD_TO_END = "fast_forward_to_the_end"


    def path(self, theme=Theme.AUTO):
        return f":/images/icons/{self.value}_{getIconColor(theme)}.svg"
