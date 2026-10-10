# -*- coding: utf-8 -*-
"""复盘周期切换集成测试（离屏 Qt + 合成数据，无网络依赖）。

覆盖场景（当前只做日/周/月）：
- 加载后注入日/周/月周期，日线显示锚定复盘日；
- 日线→周线→月线→日线切换位置保持；
- 周中复盘：切周/月显示进行中 bar（is_complete=False）；
- 直接以周线加载与日线切周线锚点一致。

分钟级链路保留但默认注释，相关测试暂不纳入。

运行（项目根目录）：
    python -m unittest tests.test_review_period_switch -v
"""

import os
import sys
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..',
                                'src', 'gui', 'qt_widgets', 'MComponents'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt5.QtWidgets import QApplication

import numpy as np
import pandas as pd

from manager.period_manager import TimePeriod
from indicators import stock_data_indicators as sdi
from common.config import cfg
from gui.qt_widgets.MComponents.review.review_widget import ReviewWidget


def make_day_df(start='2026-06-01', end='2026-08-24'):
    dates = pd.date_range(start, end, freq='B')
    m = len(dates)
    return pd.DataFrame({
        'date': dates.strftime('%Y-%m-%d'),
        'code': ['sh.600000'] * m,
        'name': ['test'] * m,
        'open': np.arange(m) + 10.0,
        'high': np.arange(m) + 11.0,
        'low': np.arange(m) + 9.0,
        'close': np.arange(m) + 10.5,
        'volume': np.arange(m) + 1000,
        'amount': np.arange(m) * 1e5 + 1e7,
        'change_percent': np.zeros(m),
        'turnover_rate': np.full(m, 0.5),
        'adjustflag': [2] * m,
    })


def make_widget(day_df, review_date, display_period):
    """注入合成日线基周期并完成加载，返回 (widget, view)。"""
    w = ReviewWidget()
    w._fetched_period_data = {TimePeriod.DAY: day_df}
    w._fetch_failed_periods = []
    w._on_all_periods_loaded('sh.600000', review_date, display_period)
    return w, w.indicators_view_widget


class ReviewSwitchTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.day_df = make_day_df()
        sdi.default_indicators_auto_calculate(cls.day_df)

    def make_view(self, review_date='2026-08-21', display=TimePeriod.DAY):
        w, view = make_widget(self.day_df.copy(), review_date, display)
        self._widget = w
        return view

    @staticmethod
    def _cur(view):
        col = 'time' if 'time' in view.df_data.columns else 'date'
        return view.df_data[col].iloc[view.current_animation_index]

    @staticmethod
    def _switch(view, btn_id, target_period):
        """等价于 slot_period_button_clicked 的切换步骤。"""
        current = ReviewSwitchTestBase._cur(view)
        btn = view.period_button_group.button(btn_id)
        btn.setChecked(True)
        view.set_period(target_period)
        view._refresh_derived_period_data(target_period, current)
        dr = view.init_animation(view.df_data.iloc[0], current, False)
        view.last_period_btn_checked_id = btn_id
        return dr

    @staticmethod
    def _current_row(view):
        return view.df_data.iloc[view.current_animation_index]


class TestLoadAndMatrix(ReviewSwitchTestBase):
    def test_load_day_display_anchor(self):
        """加载后注入日/周/月；日线显示锚定复盘日（结束时刻）。"""
        view = self.make_view(display=TimePeriod.DAY)
        self.assertIn(TimePeriod.DAY, view.dict_stock_data)
        self.assertIn(TimePeriod.WEEK, view.dict_stock_data)
        self.assertIn(TimePeriod.MONTH, view.dict_stock_data)
        self.assertEqual(view.get_current_period(), TimePeriod.DAY)
        self.assertEqual(self._cur(view), '2026-08-21 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])

    def test_load_week_display_anchor(self):
        """直接以周线加载：周五复盘锚定完整周。"""
        view = self.make_view(display=TimePeriod.WEEK)
        self.assertEqual(view.get_current_period(), TimePeriod.WEEK)
        self.assertEqual(self._cur(view), '2026-08-21 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])

    def test_day_week_month_switch_position_preserved(self):
        """日→周→月→日全切换矩阵：位置保持不漂移。"""
        view = self.make_view(display=TimePeriod.DAY)
        self.assertEqual(self._cur(view), '2026-08-21 15:00:00')
        for btn_id, period in [
            (8, TimePeriod.WEEK),
            (9, TimePeriod.MONTH),
            (7, TimePeriod.DAY),
            (9, TimePeriod.MONTH),
            (8, TimePeriod.WEEK),
            (7, TimePeriod.DAY),
        ]:
            dr = self._switch(view, btn_id, period)
            self.assertTrue(dr, TimePeriod.get_chinese_label(period))
            self.assertEqual(self._cur(view), '2026-08-21 15:00:00',
                             TimePeriod.get_chinese_label(period))


class TestPartialPeriods(ReviewSwitchTestBase):
    def test_week_month_partial_anchor_at_mid_week(self):
        """周三复盘：切周/月显示进行中 bar，位置保持不漂移。"""
        view = self.make_view(review_date='2026-06-03', display=TimePeriod.DAY)
        self.assertEqual(self._cur(view), '2026-06-03 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])

        self._switch(view, 8, TimePeriod.WEEK)
        self.assertEqual(self._cur(view), '2026-06-03 15:00:00')
        self.assertFalse(self._current_row(view)['is_complete'])

        self._switch(view, 9, TimePeriod.MONTH)
        self.assertEqual(self._cur(view), '2026-06-03 15:00:00')
        self.assertFalse(self._current_row(view)['is_complete'])

        self._switch(view, 7, TimePeriod.DAY)
        self.assertEqual(self._cur(view), '2026-06-03 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])

    def test_week_load_and_switch_same_anchor(self):
        """直接周线加载与日线切周线，同一复盘日期锚定一致。"""
        view_switch = self.make_view(review_date='2026-06-03', display=TimePeriod.DAY)
        self._switch(view_switch, 8, TimePeriod.WEEK)
        view_load = self.make_view(review_date='2026-06-03', display=TimePeriod.WEEK)
        self.assertEqual(self._cur(view_switch), self._cur(view_load))
        self.assertFalse(self._current_row(view_load)['is_complete'])


class TestForwardOnUnfinishedBar(ReviewSwitchTestBase):
    """未走完 K 线的前进处理：由 cfg.ctfEnabled 决定补全后是否自动前进。"""

    def setUp(self):
        self._ctf_enabled = cfg.ctfEnabled.value

    def tearDown(self):
        cfg.ctfEnabled.value = self._ctf_enabled

    def _day_close(self, date):
        return self.day_df.loc[self.day_df['date'] == date, 'close'].iloc[0]

    def test_forward_only_completes_when_ctf_disabled(self):
        """ctfEnabled=False（默认）：前进只补全当前未走完 K 线，位置不动。"""
        cfg.ctfEnabled.value = False
        view = self.make_view(review_date='2026-06-03', display=TimePeriod.WEEK)

        start_index = view.current_animation_index
        self.assertEqual(self._cur(view), '2026-06-03 15:00:00')
        self.assertFalse(self._current_row(view)['is_complete'])
        self.assertAlmostEqual(self._current_row(view)['close'], self._day_close('2026-06-03'))

        view.step_forward()

        # 复盘位置不变，当前 K 线补全为完整周（周一~周五）
        self.assertEqual(view.current_animation_index, start_index)
        self.assertEqual(self._cur(view), '2026-06-05 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])
        self.assertAlmostEqual(self._current_row(view)['close'], self._day_close('2026-06-05'))

        # 用户再次点击前进，才显示下一根完整 K 线
        view.step_forward()

        self.assertEqual(view.current_animation_index, start_index + 1)
        self.assertEqual(self._cur(view), '2026-06-12 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])

    def test_forward_completes_and_moves_on_when_ctf_enabled(self):
        """ctfEnabled=True：补全当前未走完 K 线并自动前进到下一根完整 K 线。"""
        cfg.ctfEnabled.value = True
        view = self.make_view(review_date='2026-06-03', display=TimePeriod.WEEK)

        start_index = view.current_animation_index
        self.assertFalse(self._current_row(view)['is_complete'])

        view.step_forward()

        self.assertEqual(view.current_animation_index, start_index + 1)
        self.assertEqual(self._cur(view), '2026-06-12 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])
        # 原来的进行中周已补全为完整周
        self.assertTrue(view.df_data.iloc[start_index]['is_complete'])
        self.assertAlmostEqual(view.df_data.iloc[start_index]['close'], self._day_close('2026-06-05'))

    def test_forward_completes_partial_month(self):
        """月线未走完时同样按 ctfEnabled=False 只补全当月。"""
        cfg.ctfEnabled.value = False
        view = self.make_view(review_date='2026-06-03', display=TimePeriod.MONTH)

        start_index = view.current_animation_index
        self.assertEqual(self._cur(view), '2026-06-03 15:00:00')
        self.assertFalse(self._current_row(view)['is_complete'])

        view.step_forward()

        self.assertEqual(view.current_animation_index, start_index)
        self.assertEqual(self._cur(view), '2026-06-30 15:00:00')
        self.assertTrue(self._current_row(view)['is_complete'])

    def test_forward_moves_on_when_bar_already_complete(self):
        """当前 K 线已走完时，前进行为不受 ctfEnabled 影响。"""
        cfg.ctfEnabled.value = False
        view = self.make_view(review_date='2026-06-05', display=TimePeriod.WEEK)

        start_index = view.current_animation_index
        self.assertTrue(self._current_row(view)['is_complete'])

        view.step_forward()

        self.assertEqual(view.current_animation_index, start_index + 1)
        self.assertTrue(self._current_row(view)['is_complete'])


if __name__ == '__main__':
    unittest.main()
