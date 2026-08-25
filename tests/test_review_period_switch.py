# -*- coding: utf-8 -*-
"""复盘周期切换集成测试（离屏 Qt + 合成数据，无网络依赖）。

覆盖场景：
- 加载后 11 个周期注入、分钟显示周期锚定；
- 日线→5m→…→120m→日线→周线→月线→日线→5m 全矩阵位置保持；
- 分钟内部切换边界（10:05 不锚到 10:10）；
- 分钟盘中切回日线为“进行中当日”，日线内前进自动走完；
- 进行中时间跨周期传播（30m 10:30 → 日线 → 周线 → 30m 仍 10:30）；
- 分钟数据未覆盖复盘日期时切换回退保持原周期。

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
from gui.qt_widgets.MComponents.review_widget import ReviewWidget


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


def make_consistent_day_df(minute_df, start='2026-06-01', end='2026-08-24'):
    """日线：分钟覆盖日（08-20/21/24）与分钟聚合一致，便于比较成交量/收盘。"""
    day = make_day_df(start, end).copy()
    for d in sorted(set(minute_df['date'])):
        sub = minute_df[minute_df['date'] == d]
        mask = day['date'] == d
        if not mask.any():
            continue
        day.loc[mask, 'open'] = sub['open'].iloc[0]
        day.loc[mask, 'high'] = sub['high'].max()
        day.loc[mask, 'low'] = sub['low'].min()
        day.loc[mask, 'close'] = sub['close'].iloc[-1]
        day.loc[mask, 'volume'] = sub['volume'].sum()
        day.loc[mask, 'amount'] = sub['amount'].sum()
    return day


def make_minute_df(days=('2026-08-20', '2026-08-21', '2026-08-24')):
    times = []
    for day in days:
        t = pd.Timestamp(day + ' 09:30')
        while t < pd.Timestamp(day + ' 11:30'):
            t = t + pd.Timedelta(minutes=5)
            times.append(t)
        t = pd.Timestamp(day + ' 13:00')
        while t < pd.Timestamp(day + ' 15:00'):
            t = t + pd.Timedelta(minutes=5)
            times.append(t)
    n = len(times)
    return pd.DataFrame({
        'date': [x.strftime('%Y-%m-%d') for x in times],
        'time': [x.strftime('%Y-%m-%d %H:%M:%S') for x in times],
        'code': ['sh.600000'] * n,
        'name': ['test'] * n,
        'open': np.arange(n) + 10.0,
        'high': np.arange(n) + 11.0,
        'low': np.arange(n) + 9.0,
        'close': np.arange(n) + 10.5,
        'volume': np.arange(n) + 1000,
        'amount': np.arange(n) * 1e5 + 1e7,
        'change_percent': np.zeros(n),
        'turnover_rate': np.full(n, 0.5),
        'adjustflag': [2] * n,
    })


def make_widget(day_df, minute_df, review_date, display_period):
    """注入合成基周期并完成加载，返回 (widget, view)。"""
    w = ReviewWidget()
    w._fetched_period_data = {TimePeriod.DAY: day_df, TimePeriod.MINUTE_5: minute_df}
    w._fetch_failed_periods = []
    w._on_all_periods_loaded('sh.600000', review_date, display_period)
    return w, w.indicators_view_widget


class ReviewSwitchTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.day_df = make_day_df()
        cls.minute_df = make_minute_df()
        sdi.default_indicators_auto_calculate(cls.day_df)
        sdi.default_indicators_auto_calculate(cls.minute_df)

    def make_view(self, review_date='2026-08-21', display=TimePeriod.DAY):
        w, view = make_widget(self.day_df.copy(), self.minute_df.copy(),
                              review_date, display)
        self._widget = w
        return view

    @staticmethod
    def _cur(view):
        if 'time' in view.df_data.columns:
            return view.df_data['time'].iloc[view.current_animation_index]
        return view.df_data['date'].iloc[view.current_animation_index]

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
    def _goto(view, t):
        df = view.get_stock_data()
        col = 'time' if 'time' in df.columns else 'date'
        idx = df.index[df[col] == t][0]
        view.go_to_target_index(idx)
        assert ReviewSwitchTestBase._cur(view) == t


class TestLoadAndMatrix(ReviewSwitchTestBase):
    def test_load_minute_display_anchor(self):
        view = self.make_view(display=TimePeriod.MINUTE_10)
        self.assertIn(TimePeriod.MINUTE_10, view.dict_stock_data)
        self.assertIn(TimePeriod.MINUTE_120, view.dict_stock_data)
        self.assertEqual(view.get_current_period(), TimePeriod.MINUTE_10)
        self.assertEqual(self._cur(view), '2026-08-21 15:00:00')

    def test_full_switch_matrix_position_preserved(self):
        view = self.make_view(display=TimePeriod.DAY)
        self.assertEqual(self._cur(view), '2026-08-21 15:00:00')
        for btn_id, period, expect in [
            (1, TimePeriod.MINUTE_5, '2026-08-21 15:00:00'),
            (2, TimePeriod.MINUTE_10, '2026-08-21 15:00:00'),
            (3, TimePeriod.MINUTE_15, '2026-08-21 15:00:00'),
            (4, TimePeriod.MINUTE_30, '2026-08-21 15:00:00'),
            (10, TimePeriod.MINUTE_45, '2026-08-21 15:00:00'),
            (5, TimePeriod.MINUTE_60, '2026-08-21 15:00:00'),
            (11, TimePeriod.MINUTE_90, '2026-08-21 15:00:00'),
            (6, TimePeriod.MINUTE_120, '2026-08-21 15:00:00'),
            (7, TimePeriod.DAY, '2026-08-21 15:00:00'),
            (8, TimePeriod.WEEK, '2026-08-21 15:00:00'),
            (9, TimePeriod.MONTH, '2026-08-21 15:00:00'),
            (7, TimePeriod.DAY, '2026-08-21 15:00:00'),
            (1, TimePeriod.MINUTE_5, '2026-08-21 15:00:00'),
        ]:
            dr = self._switch(view, btn_id, period)
            self.assertTrue(dr, TimePeriod.get_chinese_label(period))
            self.assertEqual(self._cur(view), expect, TimePeriod.get_chinese_label(period))


class TestMinuteInternal(ReviewSwitchTestBase):
    def test_midday_boundary(self):
        """as_of 恰为 bar 起始时刻时归属上一根（10:05 不锚到 10:10）。"""
        view = self.make_view(display=TimePeriod.DAY)
        self._switch(view, 1, TimePeriod.MINUTE_5)
        self._goto(view, '2026-08-21 10:05:00')
        for btn_id, period, expect in [
            (2, TimePeriod.MINUTE_10, '2026-08-21 10:05:00'),
            (10, TimePeriod.MINUTE_45, '2026-08-21 10:05:00'),
            (11, TimePeriod.MINUTE_90, '2026-08-21 10:05:00'),
            (6, TimePeriod.MINUTE_120, '2026-08-21 10:05:00'),
            (1, TimePeriod.MINUTE_5, '2026-08-21 10:05:00'),
        ]:
            self._switch(view, btn_id, period)
            self.assertEqual(self._cur(view), expect, TimePeriod.get_chinese_label(period))


class TestPartialAndAutoComplete(ReviewSwitchTestBase):
    def test_day_partial_and_auto_complete(self):
        """30m 11:00 → 日线为进行中当日；日线前进后自动走完（成交量恢复全天）。"""
        day_df = make_consistent_day_df(self.minute_df)
        sdi.default_indicators_auto_calculate(day_df)
        w = ReviewWidget()
        w._fetched_period_data = {TimePeriod.DAY: day_df, TimePeriod.MINUTE_5: self.minute_df.copy()}
        w._fetch_failed_periods = []
        w._on_all_periods_loaded('sh.600000', '2026-08-21', TimePeriod.DAY)
        view = w.indicators_view_widget
        self._widget = w
        self._switch(view, 4, TimePeriod.MINUTE_30)
        self._goto(view, '2026-08-21 11:00:00')
        self._switch(view, 7, TimePeriod.DAY)
        row = view.df_data.iloc[view.current_animation_index]
        self.assertEqual(row['date'], '2026-08-21')
        self.assertFalse(row['is_complete'])
        full_vol = float(day_df[day_df['date'] == '2026-08-21']['volume'].iloc[0])
        self.assertLess(row['volume'], full_vol)
        view.step_forward()
        self.assertEqual(self._cur(view), '2026-08-24 15:00:00')
        row = view.df_data[view.df_data['date'] == '2026-08-21'].iloc[-1]
        self.assertTrue(row['is_complete'])
        self.assertAlmostEqual(float(row['volume']), full_vol)

    def test_time_propagation_week_chain(self):
        """30m 10:30 → 日线(partial) → 周线 → 30m 仍锚定 10:30。"""
        view = self.make_view(display=TimePeriod.DAY)
        self._switch(view, 4, TimePeriod.MINUTE_30)
        self._goto(view, '2026-08-21 10:30:00')
        self._switch(view, 7, TimePeriod.DAY)
        self._switch(view, 8, TimePeriod.WEEK)
        week_row = view.dict_stock_data[TimePeriod.WEEK].iloc[view.current_animation_index]
        self.assertEqual(week_row['time'], '2026-08-21 10:30:00')
        self.assertFalse(week_row['is_complete'])
        self._switch(view, 4, TimePeriod.MINUTE_30)
        self.assertEqual(self._cur(view), '2026-08-21 10:30:00')


class TestUncoveredRevert(ReviewSwitchTestBase):
    def test_revert_when_minute_not_cover(self):
        """分钟数据未覆盖复盘日期（2026-06 早于 5m 起点 08-20）时点击 5 分回退保持日线。"""
        day_old = make_day_df('2026-06-01', '2026-06-30')
        sdi.default_indicators_auto_calculate(day_old)
        w, view = make_widget(day_old, self.minute_df, '2026-06-15', TimePeriod.DAY)
        self.assertEqual(view.df_data['date'].iloc[view.current_animation_index], '2026-06-15')
        view.period_button_group.button(1).click()
        self.assertEqual(view.get_current_period(), TimePeriod.DAY)
        self.assertEqual(view.df_data['date'].iloc[view.current_animation_index], '2026-06-15')


if __name__ == '__main__':
    unittest.main()
