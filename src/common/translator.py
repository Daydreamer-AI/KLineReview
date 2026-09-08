# coding: utf-8
import os
from PyQt5.QtCore import QObject, QTranslator, QLocale
from common.common_api import get_resource_path

class Translator(QObject):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.review = self.tr("Review")

class KLineReviewTranslator(QTranslator):
    """ Translator of KLineReview App """

    def __init__(self, locale: QLocale = None, parent=None):
        super().__init__(parent=parent)
        self.load(locale or QLocale())

    def load(self, locale: QLocale):
        """ load translation file """
        i18n_dir = get_resource_path(os.path.join("resources", "i18n"))
        print(f"i18n_dir: {i18n_dir}")
        return super().load(f"klinereview_{locale.name()}.qm", i18n_dir)