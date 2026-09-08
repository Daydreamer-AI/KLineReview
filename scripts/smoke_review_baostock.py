# -*- coding: utf-8 -*-
"""复盘周期切换·真实数据冒烟脚本（可选，依赖网络与 Baostock）。

与 tests/ 的合成数据测试不同，本脚本从 Baostock 拉取真实日线 + 5 分钟数据，
走完整复盘链路验证：11 周期注入与加载锚定、日/分钟全矩阵位置保持、
盘中边界（10:05 不锚到 10:10）、分钟盘中切回日线为进行中、时间跨周期传播。

运行（项目根目录，Windows 下激活 .venv）：
    python scripts/smoke_review_baostock.py
    python scripts/smoke_review_baostock.py --code sz.000615 --date 2026-03-10

注意：
    - 需要网络；Baostock 分钟数据历史范围有限（部分股票自当年 1 月起）；
    - 若 --date 早于分钟数据起点，会自动回退到分钟数据最后日期并提示；
    - 不写库，不影响本地数据。
"""

import argparse
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..',
                                'src', 'gui', 'qt_widgets', 'MComponents'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt5.QtWidgets import QApplication

from manager.period_manager import TimePeriod
from indicators import stock_data_indicators as sdi
from processor.baostock_processor import BaoStockProcessor
from gui.qt_widgets.MComponents.review.review_widget import ReviewWidget


_APP = None


def get_app():
    """模块级持有 QApplication，避免被 GC 后控件树整体销毁。"""
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication(sys.argv)
    return _APP


def _prepare(df, code):
    df = df.copy()
    df['name'] = code
    if 'date' in df.columns:
        df['date'] = df['date'].astype(str)
    if 'time' in df.columns:
        df['time'] = df['time'].astype(str)
    sdi.default_indicators_auto_calculate(df)
    return df


def fetch_real_data(code, review_date):
    proc = BaoStockProcessor()
    proc.init_baostock_login()
    try:
        day_df = proc.process_daily_stock_data(code, None, None, '2')
        m5 = proc.process_minute_level_stock_data(code, TimePeriod.MINUTE_5, None, None, '2')
    finally:
        if hasattr(proc, 'logout'):
            try:
                proc.logout()
            except Exception:
                pass
    if m5 is None or m5.empty:
        raise RuntimeError('Baostock 5 分钟数据为空（可能是非交易时段或该股票无分钟数据）')
    m5_dates = set(m5['date'].astype(str))
    if review_date is None:
        review_date = str(m5['date'].max())
    elif review_date not in m5_dates:
        print(f'[warn] {review_date} 不在 5 分钟数据范围内，回退到最后交易日 '
              f'{str(m5["date"].max())}')
        review_date = str(m5['date'].max())
    return _prepare(day_df, code), _prepare(m5, code), review_date


def make_view(day_df, m5, code, review_date):
    get_app()
    w = ReviewWidget()
    w._fetched_period_data = {TimePeriod.DAY: day_df, TimePeriod.MINUTE_5: m5}
    w._fetch_failed_periods = []
    w._on_all_periods_loaded(code, review_date, TimePeriod.DAY)
    return w, w.indicators_view_widget


def cur(view):
    if 'time' in view.df_data.columns:
        return view.df_data['time'].iloc[view.current_animation_index]
    return view.df_data['date'].iloc[view.current_animation_index]


def switch(view, btn_id, period):
    current = cur(view)
    btn = view.period_button_group.button(btn_id)
    btn.setChecked(True)
    view.set_period(period)
    view._refresh_derived_period_data(period, current)
    view.init_animation(view.df_data.iloc[0], current, False)
    view.last_period_btn_checked_id = btn_id


def goto(view, t):
    df = view.get_stock_data()
    col = 'time' if 'time' in df.columns else 'date'
    idx = df.index[df[col] == t][0]
    view.go_to_target_index(idx)


def run_checks(view, review_date):
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        print(f'  [{"PASS" if cond else "FAIL"}] {name}  (cur={cur(view)})')

    print('1) 加载锚定（日线 → 分钟）')
    switch(view, 4, TimePeriod.MINUTE_30)
    check('日线→30m 锚定当日 15:00', cur(view) == f'{review_date} 15:00:00')

    print('2) 日/分钟全矩阵位置保持')
    seq = [
        (1, TimePeriod.MINUTE_5), (2, TimePeriod.MINUTE_10), (3, TimePeriod.MINUTE_15),
        (4, TimePeriod.MINUTE_30), (10, TimePeriod.MINUTE_45), (5, TimePeriod.MINUTE_60),
        (11, TimePeriod.MINUTE_90), (6, TimePeriod.MINUTE_120), (7, TimePeriod.DAY),
        (8, TimePeriod.WEEK), (9, TimePeriod.MONTH), (7, TimePeriod.DAY),
        (1, TimePeriod.MINUTE_5),
    ]
    ok = True
    for btn_id, period in seq:
        switch(view, btn_id, period)
        if cur(view) != f'{review_date} 15:00:00':
            ok = False
            break
    check('全矩阵位置保持', ok)

    print('3) 盘中边界（10:05 不锚到 10:10）')
    switch(view, 1, TimePeriod.MINUTE_5)
    goto(view, f'{review_date} 10:05:00')
    for btn_id, period in [(2, TimePeriod.MINUTE_10), (6, TimePeriod.MINUTE_120),
                           (1, TimePeriod.MINUTE_5)]:
        switch(view, btn_id, period)
        if cur(view) != f'{review_date} 10:05:00':
            ok = False
            break
    check('盘中边界位置保持', ok)

    print('4) 分钟盘中切日线为进行中 + 时间跨周期传播')
    switch(view, 7, TimePeriod.DAY)
    check('30m→日线当日 is_complete=False',
          not view.df_data.iloc[view.current_animation_index]['is_complete'])
    switch(view, 8, TimePeriod.WEEK)
    switch(view, 4, TimePeriod.MINUTE_30)
    check('周线→30m 仍锚定盘中时刻（10:05，不跳 15:00）',
          cur(view) == f'{review_date} 10:05:00')

    failed = [name for name, ok in results if not ok]
    print(f'\n结果：{len(results) - len(failed)}/{len(results)} 通过')
    return not failed


def main():
    parser = argparse.ArgumentParser(description='复盘周期切换真实数据冒烟')
    parser.add_argument('--code', default='sz.000615', help='股票代码，如 sh.600000')
    parser.add_argument('--date', default=None, help='复盘日期 YYYY-MM-DD（默认取分钟数据最后日期）')
    args = parser.parse_args()

    print(f'拉取真实数据：{args.code} ...')
    day_df, m5, review_date = fetch_real_data(args.code, args.date)
    print(f'日线 {day_df["date"].iloc[0]} ~ {day_df["date"].iloc[-1]}（{len(day_df)} 行）；'
          f'5 分钟 {m5["date"].iloc[0]} ~ {m5["date"].iloc[-1]}（{len(m5)} 行）')
    print(f'复盘日期：{review_date}')

    widget, view = make_view(day_df, m5, args.code, review_date)
    ok = run_checks(view, review_date)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
