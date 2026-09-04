# -*- coding: utf-8 -*-
"""周期聚合器单元测试（纯逻辑，无 GUI/网络依赖，全部使用合成数据）。

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
from processor.period_aggregator import (
    aggregate_period,
    get_minute_slot_intervals,
    period_start_key,
)


def make_minute_df(days=('2026-08-20', '2026-08-21', '2026-08-24')):
    """构造 A 股完整交易日 5 分钟 K 线（每交易日 48 根：上午 24 + 下午 24）。"""
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


class TestMinuteSlotIntervals(unittest.TestCase):
    """交易时段切槽的槽数（每交易日：上午 + 下午）。"""

    def test_slot_counts(self):
        self.assertEqual(len(get_minute_slot_intervals(10)), 24)
        self.assertEqual(len(get_minute_slot_intervals(15)), 16)
        self.assertEqual(len(get_minute_slot_intervals(30)), 8)
        self.assertEqual(len(get_minute_slot_intervals(45)), 6)
        self.assertEqual(len(get_minute_slot_intervals(60)), 4)
        self.assertEqual(len(get_minute_slot_intervals(90)), 4)
        self.assertEqual(len(get_minute_slot_intervals(120)), 2)


class TestMinuteAggregation(unittest.TestCase):
    """5 分钟基周期 → 各分钟级别聚合。"""

    @classmethod
    def setUpClass(cls):
        cls.base = make_minute_df()

    def test_per_day_counts(self):
        for period, expected in [
            (TimePeriod.MINUTE_10, 24),
            (TimePeriod.MINUTE_15, 16),
            (TimePeriod.MINUTE_30, 8),
            (TimePeriod.MINUTE_45, 6),
            (TimePeriod.MINUTE_60, 4),
            (TimePeriod.MINUTE_90, 4),
            (TimePeriod.MINUTE_120, 2),
        ]:
            out = aggregate_period(self.base, period, as_of='2026-08-24 15:00:00')
            per_day = out[out['date'] == '2026-08-24']
            self.assertEqual(len(per_day), expected, TimePeriod.get_label(period))

    def test_120m_cross_lunch(self):
        """跨午休不分组错误：上午 24 根 5m → 一根 11:30，下午 → 一根 15:00。"""
        out = aggregate_period(self.base, TimePeriod.MINUTE_120, as_of='2026-08-24 15:00:00')
        day = out[out['date'] == '2026-08-24']
        self.assertEqual(day['time'].tolist(),
                         ['2026-08-24 11:30:00', '2026-08-24 15:00:00'])
        day_base = self.base[self.base['date'] == '2026-08-24']
        self.assertEqual(day['volume'].iloc[0], day_base['volume'].iloc[:24].sum())
        self.assertEqual(day['volume'].iloc[1], day_base['volume'].iloc[24:].sum())

    def test_partial_slot(self):
        """盘中 as_of=10:07：10:00-10:10 槽只含 10:05 一根，is_complete=False。"""
        out = aggregate_period(self.base, TimePeriod.MINUTE_10, as_of='2026-08-24 10:07:00')
        partial = out[out['is_complete'] == False]
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial.iloc[0]['time'], '2026-08-24 10:05:00')
        sub = self.base[
            (self.base['date'] == '2026-08-24')
            & (self.base['time'] > '2026-08-24 10:00:00')
            & (self.base['time'] <= '2026-08-24 10:07:00')
        ]
        self.assertEqual(partial.iloc[0]['volume'], sub['volume'].sum())

    def test_custom_minutes(self):
        """非 5 倍数自定义分钟：25m=10 槽/日、7m=36 槽/日（含尾段）。"""
        out25 = aggregate_period(self.base, TimePeriod.MINUTE_25, as_of='2026-08-24 15:00:00')
        self.assertEqual(len(out25[out25['date'] == '2026-08-24']), 10)
        out7 = aggregate_period(self.base, TimePeriod.MINUTE_7, as_of='2026-08-24 15:00:00')
        self.assertEqual(len(out7[out7['date'] == '2026-08-24']), 36)

    def test_output_columns(self):
        out = aggregate_period(self.base, TimePeriod.MINUTE_30, as_of='2026-08-24 15:00:00')
        for col in ['date', 'time', 'open', 'high', 'low', 'close', 'volume', 'amount',
                    'is_complete', 'ma5', 'macd', 'change_percent']:
            self.assertIn(col, out.columns)


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
                             TimePeriod.get_label(period))

    def test_2week_starts_monday(self):
        self.assertEqual(
            period_start_key(TimePeriod.WEEK_2, pd.Timestamp('2026-08-24')).day_name(),
            'Monday')


if __name__ == '__main__':
    unittest.main()
