# -*- coding: utf-8 -*-
"""通用周期聚合器：以基周期 K 线为输入，按目标周期聚合生成上级周期 K 线。

设计背景：
    Baostock 各周期接口只返回“完整周期”bar（工作日 18:00 后更新当天日线、
    每周最后交易日更新当周周线、月线以上同理），未走完的周期在远程数据中不存在。
    复盘需要“截至复盘基准时刻 as_of”的部分周期 bar（如周一~周三的部分周线），
    因此上级周期一律由基周期（日线/分钟线）本地聚合生成，不依赖远程对应周期接口。

核心概念：
    - period_start：bar 所属周期的开始时刻（周=周一、月=1 日、日=当日、分钟=bar 开始时刻）。
    - bar 日期标签：取“该周期内最后一根基周期 bar 的时刻”（未走完时即 as_of 所在
      基周期 bar 的时刻，走完后即周期最后一个交易日）。
    - as_of：复盘基准时刻。包含 as_of 且未走完的周期 bar 只聚合 as_of 之前的数据，
      并标记 is_complete=False；其余周期 bar 保持完整，保证复盘无未来数据泄漏。
    - 聚合后复用 default_indicators_auto_calculate 计算指标列，列结构与现有周期数据一致。
"""

import pandas as pd

from manager.period_manager import TimePeriod
from indicators import stock_data_indicators as sdi


def get_period_interval_minutes(period):
    """分钟级周期的单根 bar 时长（分钟）；非分钟级返回 0。"""
    if not TimePeriod.is_minute_level(period):
        return 0
    return int(TimePeriod.get_number_label(period))


_A_SHARE_SESSIONS = [
    (pd.Timestamp('09:30').time(), pd.Timestamp('11:30').time()),
    (pd.Timestamp('13:00').time(), pd.Timestamp('15:00').time()),
]


def _period_multiplier(period):
    """返回 (基准类型, 倍数)：minute/day/week/month/quarter/year 及其倍数。"""
    value = period.value
    if TimePeriod.is_minute_level(period):
        return 'minute', int(value[:-1])
    if value.endswith('d'):
        return 'day', int(value[:-1])
    if value.endswith('w'):
        return 'week', int(value[:-1])
    if value.endswith('M'):
        return 'month', int(value[:-1])
    if value.endswith('Q'):
        return 'quarter', 1
    if value.endswith('Y'):
        return 'year', 1
    return 'day', 1


def minute_slot_bounds(ts, minutes):
    """返回 bar（以结束时刻 ts 标注）所属 A 股交易时段槽位的 [start, end)。

    09:30-11:30、13:00-15:00 两段连续竞价时段内各自按 minutes 分钟切槽，
    槽位从时段起点开始，最后一槽可能不足 minutes（尾段）。
    """
    ts = pd.Timestamp(ts)
    for session_start, session_end in _A_SHARE_SESSIONS:
        if session_start <= ts.time() <= session_end:
            day_start = pd.Timestamp.combine(ts.date(), session_start)
            day_end = pd.Timestamp.combine(ts.date(), session_end)
            elapsed_min = (ts - day_start).total_seconds() / 60.0
            idx = max(0, (int(elapsed_min) - 1) // minutes)
            slot_start = day_start + pd.Timedelta(minutes=idx * minutes)
            slot_end = min(slot_start + pd.Timedelta(minutes=minutes), day_end)
            return slot_start, slot_end
    return ts.normalize(), ts.normalize() + pd.Timedelta(days=1)


def get_minute_slot_intervals(minutes):
    """返回给定分钟数在 A 股两个交易时段内的槽位 (开始时刻, 结束时刻) 列表。"""
    intervals = []
    dummy_date = pd.Timestamp('2020-01-01')
    for session_start, session_end in _A_SHARE_SESSIONS:
        current = session_start
        while current < session_end:
            next_time = (pd.Timestamp.combine(dummy_date, current)
                         + pd.Timedelta(minutes=minutes)).time()
            if next_time > session_end:
                next_time = session_end
            intervals.append((current, next_time))
            current = next_time
    return intervals


def period_start_key(period, ts):
    """计算 bar（以其结束时刻 ts 标注）所属目标周期的开始时刻。

    通用锚定与周期聚合共用此规则：
    - 分钟级：按 A 股交易时段切槽（跨午休不分组错误）；
    - 日线：开始 = 当日；2/3 日线按自然日倍数分组；
    - 周线：开始 = 当周周一（ISO 周）；2 周线按 14 日网格分组；
    - 月线：开始 = 当月 1 日；2/3/6/12 月线按月份倍数分组；季线/年线同理。
    """
    ts = pd.Timestamp(ts)
    kind, count = _period_multiplier(period)
    if kind == 'minute':
        slot_start, _ = minute_slot_bounds(ts, count)
        return slot_start
    if kind == 'day':
        if count == 1:
            return ts.normalize()
        start_ordinal = ((ts.toordinal() - 1) // count) * count + 1
        return pd.Timestamp.fromordinal(start_ordinal)
    if kind == 'week':
        monday = (ts - pd.Timedelta(days=ts.weekday())).normalize()
        if count == 1:
            return monday
        start_ordinal = ((monday.toordinal() - 1) // (7 * count)) * (7 * count) + 1
        return pd.Timestamp.fromordinal(start_ordinal)
    if kind == 'month':
        month_index = ts.year * 12 + (ts.month - 1)
        start_index = (month_index // count) * count
        return pd.Timestamp(start_index // 12, start_index % 12 + 1, 1)
    if kind == 'quarter':
        return pd.Timestamp(ts.year, ((ts.month - 1) // 3) * 3 + 1, 1)
    if kind == 'year':
        return pd.Timestamp(ts.year, 1, 1)
    return ts.normalize()


def period_end_key(period, ts):
    """计算 bar 的名义结束时刻：分钟级为槽位结束时刻，日线及以上沿用 ts（组内最后交易日）。"""
    ts = pd.Timestamp(ts)
    kind, count = _period_multiplier(period)
    if kind == 'minute':
        _, slot_end = minute_slot_bounds(ts, count)
        return slot_end
    return ts


def _get_base_timestamps(base_df):
    """基周期每根 bar 的时间戳：日线及以上取日期，分钟级取 date+time。"""
    dates = pd.to_datetime(base_df['date'])
    if 'time' not in base_df.columns:
        return dates
    time_str = base_df['time'].astype(str).str.strip()
    if time_str.str.match(r'^\d{2}:\d{2}:\d{2}$').all():
        return pd.to_datetime(base_df['date'].astype(str) + ' ' + time_str)
    return pd.to_datetime(time_str, errors='coerce')


def _aggregate_group(grp, label_t, complete, period):
    """将同一周期内的基周期 bar 聚合为一行上级周期 bar。"""
    row = {
        '_label': label_t,
        'open': grp['open'].iloc[0],
        'high': grp['high'].max(),
        'low': grp['low'].min(),
        'close': grp['close'].iloc[-1],
        'volume': grp['volume'].sum(),
        'amount': grp['amount'].sum() if 'amount' in grp.columns else 0.0,
        'turnover_rate': grp['turnover_rate'].sum() if 'turnover_rate' in grp.columns else 0.0,
        'adjustflag': grp['adjustflag'].iloc[-1] if 'adjustflag' in grp.columns else 2,
        'code': grp['code'].iloc[0] if 'code' in grp.columns else '',
        'name': grp['name'].iloc[-1] if 'name' in grp.columns else '',
        'is_complete': complete,
    }
    return row


def aggregate_period(base_df, period, as_of=None):
    """将基周期 K 线聚合为目标周期的 K 线。

    Args:
        base_df: 基周期 K 线 DataFrame（需含 date/open/high/low/close/volume，
            建议含 amount/code/name/adjustflag/turnover_rate），按时间升序。
        period: 目标周期（TimePeriod）。
        as_of: 复盘基准时刻（str/date/datetime）。包含 as_of 且未走完的周期 bar
            只聚合 as_of 之前的数据，并标记 is_complete=False；其余 bar 保持完整。
            为 None 时全部按完整周期聚合。

    Returns:
        与现有周期数据同构的 DataFrame：date 为 ISO 字符串（分钟级含 time 列），
        额外含 is_complete 列，并已计算指标列。
    """
    if base_df is None or base_df.empty:
        return base_df

    required = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing = [col for col in required if col not in base_df.columns]
    if missing:
        raise ValueError(f"基周期数据缺少列: {missing}")

    base = base_df.copy()
    base['_t'] = _get_base_timestamps(base)
    base = base.sort_values('_t').reset_index(drop=True)
    base['_key'] = base['_t'].apply(lambda ts: period_start_key(period, ts))

    if as_of is not None:
        as_of = pd.Timestamp(as_of)

    rows = []
    for key, grp in base.groupby('_key', sort=True):
        nominal_end = period_end_key(period, grp['_t'].max())
        complete = True
        if as_of is not None:
            if TimePeriod.is_minute_level(period):
                cmp_key, cmp_as_of, cmp_end = key, as_of, nominal_end
                cmp_t = grp['_t']
                last_incomplete = False
            else:
                # 日线及以上以日期粒度判断（基周期 bar 可能带 time 列，如进行中当日）
                cmp_key, cmp_as_of, cmp_end = key.normalize(), as_of.normalize(), nominal_end.normalize()
                cmp_t = grp['_t'].dt.normalize()
                # 周期最后一日若本身未走完（如周五盘中），该周期也应视为进行中
                last_incomplete = bool(
                    'is_complete' in grp.columns
                    and not grp.loc[grp['_t'].idxmax(), 'is_complete']
                )
            if cmp_key <= cmp_as_of and (cmp_as_of < cmp_end or last_incomplete):
                # 包含 as_of 且未走完的周期：只取 as_of 之前的基周期数据，标记为进行中
                grp = grp[cmp_t <= cmp_as_of]
                if grp.empty:
                    continue
                complete = False
        label_t = grp['_t'].max()
        rows.append(_aggregate_group(grp, label_t, complete, period))

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    result['date'] = pd.to_datetime(result['_label']).dt.strftime('%Y-%m-%d')
    result['time'] = pd.to_datetime(result['_label']).dt.strftime('%Y-%m-%d %H:%M:%S')
    result = result.drop(columns=['_label'])

    result['change_percent'] = result['close'].pct_change() * 100
    result['change_percent'] = result['change_percent'].fillna(0)

    cols = ['date', 'time', 'code', 'name', 'open', 'high', 'low', 'close', 'volume', 'amount',
            'change_percent', 'turnover_rate', 'adjustflag', 'is_complete']
    result = result[[col for col in cols if col in result.columns]]

    sdi.default_indicators_auto_calculate(result)
    return result
