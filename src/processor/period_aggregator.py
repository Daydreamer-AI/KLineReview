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


def period_start_key(period, ts):
    """计算 bar（以其结束时刻 ts 标注）所属周期的开始时刻。

    通用锚定与周期聚合共用此规则：
    - 分钟级：开始 = 结束 - 周期时长（baostock 分钟 bar 以结束时刻标注）；
    - 日线：开始 = 当日；
    - 周线：开始 = 当周周一（ISO 周）；
    - 月线：开始 = 当月 1 日；季线/年线同理取季度/年度首日。
    """
    ts = pd.Timestamp(ts)
    if TimePeriod.is_minute_level(period):
        return ts - pd.Timedelta(minutes=get_period_interval_minutes(period))
    if period == TimePeriod.DAY:
        return ts.normalize()
    if period == TimePeriod.WEEK:
        return (ts - pd.Timedelta(days=ts.weekday())).normalize()
    if period == TimePeriod.MONTH:
        return pd.Timestamp(ts.year, ts.month, 1)
    if period == TimePeriod.QUARTER:
        q_start_month = ((ts.month - 1) // 3) * 3 + 1
        return pd.Timestamp(ts.year, q_start_month, 1)
    if period == TimePeriod.YEAR:
        return pd.Timestamp(ts.year, 1, 1)
    return ts.normalize()


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
        nominal_end = grp['_t'].max()
        complete = True
        if as_of is not None and key <= as_of and as_of < nominal_end:
            # 包含 as_of 且未走完的周期：只取 as_of 之前的基周期数据，标记为进行中
            grp = grp[grp['_t'] <= as_of]
            if grp.empty:
                continue
            complete = False
        label_t = grp['_t'].max()
        rows.append(_aggregate_group(grp, label_t, complete, period))

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    result['date'] = pd.to_datetime(result['_label']).dt.strftime('%Y-%m-%d')
    if TimePeriod.is_minute_level(period):
        result['time'] = pd.to_datetime(result['_label']).dt.strftime('%H:%M:%S')
    result = result.drop(columns=['_label'])

    result['change_percent'] = result['close'].pct_change() * 100
    result['change_percent'] = result['change_percent'].fillna(0)

    cols = ['date', 'code', 'name', 'open', 'high', 'low', 'close', 'volume', 'amount',
            'change_percent', 'turnover_rate', 'adjustflag', 'is_complete']
    if TimePeriod.is_minute_level(period):
        cols.insert(1, 'time')
    result = result[[col for col in cols if col in result.columns]]

    sdi.default_indicators_auto_calculate(result)
    return result
