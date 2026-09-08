# -*- coding: utf-8 -*-
"""周期聚合器单元测试（纯逻辑，无 GUI/网络依赖，全部使用合成数据）。

当前只覆盖日/周/月与多日/多周/多月倍数聚合；分钟级链路暂不纳入测试。

运行（项目根目录）：
    python -m unittest tests.test_period_aggregator -v
或批量：
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pandas as pd

from manager.period_manager import TimePeriod
from processor.period_aggregator import aggregate_period, period_start_key


def make_day_df(start='2026-06-01', end='2026-08-24'):
    """构造自然日（交易日）日线 K 线。"""
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


class TestDayWeekMonthAggregation(unittest.TestCase):
    """日线基周期 → 周线/月线聚合（完整与进行中 bar）。"""

    @classmethod
    def setUpClass(cls):
        cls.day = make_day_df('2026-06-01', '2026-06-30')

    @staticmethod
    def _day_volume(date_str):
        sub = TestDayWeekMonthAggregation.day
        return sub[sub['date'] == date_str]['volume'].sum()

    def test_week_partial_at_wednesday(self):
        """周三 as_of：当周 bar 只聚合周一~周三，is_complete=False。"""
        out = aggregate_period(self.day, TimePeriod.WEEK, as_of='2026-06-03')
        row = out.iloc[0]
        expected = sum(self._day_volume(d) for d in ('2026-06-01', '2026-06-02', '2026-06-03'))
        self.assertEqual(row['volume'], expected)
        self.assertFalse(row['is_complete'])

    def test_week_complete_at_friday(self):
        """周五 as_of：当周 bar 完整，is_complete=True。"""
        out = aggregate_period(self.day, TimePeriod.WEEK, as_of='2026-06-05')
        row = out.iloc[0]
        expected = sum(self._day_volume(d) for d in
                       ('2026-06-01', '2026-06-02', '2026-06-03', '2026-06-04', '2026-06-05'))
        self.assertEqual(row['volume'], expected)
        self.assertTrue(row['is_complete'])

    def test_month_partial(self):
        """月中 as_of：当月 bar 只聚合已发生日线，is_complete=False。"""
        out = aggregate_period(self.day, TimePeriod.MONTH, as_of='2026-06-03')
        self.assertEqual(len(out), 1)
        row = out.iloc[0]
        expected = sum(self._day_volume(d) for d in ('2026-06-01', '2026-06-02', '2026-06-03'))
        self.assertEqual(row['volume'], expected)
        self.assertFalse(row['is_complete'])

    def test_month_complete_at_month_end(self):
        """月末 as_of：当月 bar 完整，is_complete=True。"""
        out = aggregate_period(self.day, TimePeriod.MONTH, as_of='2026-06-30')
        row = out.iloc[0]
        month_days = self.day['date'].str.startswith('2026-06')
        self.assertEqual(row['volume'], self.day.loc[month_days, 'volume'].sum())
        self.assertTrue(row['is_complete'])


class TestMultiPeriods(unittest.TestCase):
    """多日/多周/多月倍数聚合。"""

    @classmethod
    def setUpClass(cls):
        cls.day = make_day_df()

    def _group_volume(self, period, label):
        key = period_start_key(period, pd.Timestamp(label))
        keys = pd.to_datetime(self.day['date']).apply(lambda d: period_start_key(period, d))
        return self.day[keys == key]['volume'].sum()

    def test_2day_2week_2month(self):
        for period in (TimePeriod.DAY_2, TimePeriod.WEEK_2,
                       TimePeriod.MONTH_2, TimePeriod.MONTH_3):
            out = aggregate_period(self.day, period, as_of='2026-08-24')
            last = out.iloc[-1]
            self.assertEqual(last['volume'], self._group_volume(period, last['date']),
                             TimePeriod.get_chinese_label(period))

    def test_2week_starts_monday(self):
        self.assertEqual(
            period_start_key(TimePeriod.WEEK_2, pd.Timestamp('2026-08-24')).day_name(),
            'Monday')


if __name__ == '__main__':
    unittest.main()
