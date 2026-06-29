"""
回测引擎
模拟信号出现后的交易表现，计算胜率、收益、盈亏比等指标
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from patterns import PATTERNS, get_pattern_by_code, SignalType


def backtest_signal(df: pd.DataFrame,
                    pattern_codes: List[str],
                    hold_days: int = 5,
                    phase_mask: Optional[pd.Series] = None) -> Dict:
    """
    对指定的蜡烛图信号进行回测
    - 信号出现日 T，T+1 日买入，持有 hold_days 天后卖出
    - 计算每笔交易的收益率和统计指标
    """
    if len(df) < hold_days + 5:
        return _empty_result()

    # 确保所有模式存在
    patterns = []
    for code in pattern_codes:
        p = get_pattern_by_code(code)
        if p:
            patterns.append(p)

    if not patterns:
        return _empty_result()

    trades = []
    n = len(df)

    for i in range(3, n - hold_days - 1):
        # 检查是否在阶段匹配范围内
        if phase_mask is not None and not phase_mask.iloc[i]:
            continue

        # 检查该位置是否出现指定信号
        for pattern in patterns:
            if pattern.check(df, i):
                # 模拟交易：T+1买入，持有hold_days天后卖出
                buy_idx = i + 1  # T+1 买入
                sell_idx = min(buy_idx + hold_days, n - 1)

                buy_price = df.iloc[buy_idx]['close']
                sell_price = df.iloc[sell_idx]['close']

                if buy_price <= 0:
                    continue

                returns = {}
                for d in [1, 3, 5, 10, 20]:
                    s_idx = min(buy_idx + d, n - 1)
                    s_price = df.iloc[s_idx]['close']
                    returns[f'return_{d}d'] = round((s_price - buy_price) / buy_price * 100, 2)

                profit = sell_price - buy_price
                return_pct = round(profit / buy_price * 100, 2)

                # 计算最大回撤（持有期内）
                prices_in_period = [df.iloc[j]['close'] for j in range(buy_idx, sell_idx + 1)]
                peak = prices_in_period[0]
                max_dd = 0
                for p in prices_in_period:
                    if p > peak:
                        peak = p
                    dd = (peak - p) / peak * 100
                    if dd > max_dd:
                        max_dd = dd

                trades.append({
                    'signal_date': str(df.index[i])[:10],
                    'signal_name': pattern.name,
                    'signal_code': pattern.code,
                    'signal_type': pattern.signal_type.value,
                    'buy_date': str(df.index[buy_idx])[:10],
                    'buy_price': round(buy_price, 2),
                    'sell_date': str(df.index[sell_idx])[:10],
                    'sell_price': round(sell_price, 2),
                    'return_pct': return_pct,
                    'is_win': profit > 0,
                    'profit': round(profit, 2),
                    'max_drawdown': round(max_dd, 2),
                    **returns
                })
                break  # 同一位置只取第一个匹配的信号

    return _compute_statistics(trades, df)


def backtest_all_signals(df: pd.DataFrame,
                         hold_days: int = 5,
                         phase_mask: Optional[pd.Series] = None) -> List[Dict]:
    """
    对全部30+种信号进行回测，返回每个信号的统计结果
    """
    results = []
    for pattern in PATTERNS:
        result = backtest_signal(df, [pattern.code], hold_days, phase_mask)
        if result['total_trades'] > 0:
            results.append({
                'signal_code': pattern.code,
                'signal_name': pattern.name,
                'signal_type': pattern.signal_type.value,
                'total_trades': result['total_trades'],
                'win_count': result['win_count'],
                'loss_count': result['loss_count'],
                'win_rate': result['win_rate'],
                'avg_return': result['avg_return'],
                'median_return': result['median_return'],
                'profit_factor': result['profit_factor'],
                'max_drawdown': result['max_drawdown'],
                'total_return': result['total_return'],
                'trades': result['trades']
            })
    return results


def compute_equity_curve(trades: List[Dict], initial_value: float = 1.0) -> List[Dict]:
    """
    计算策略净值曲线
    """
    if not trades:
        return [{'date': 'initial', 'value': initial_value}]

    curve = [{'date': 'initial', 'value': initial_value}]
    value = initial_value

    for t in sorted(trades, key=lambda x: x['buy_date']):
        ret = t['return_pct'] / 100
        value *= (1 + ret)
        curve.append({
            'date': t['buy_date'],
            'value': round(value, 4),
            'return_pct': t['return_pct']
        })

    return curve


def compute_benchmark_curve(df: pd.DataFrame) -> List[Dict]:
    """
    计算买入持有策略的基准净值曲线
    """
    if len(df) < 2:
        return []

    first_close = df.iloc[0]['close']
    curve = []
    for i in range(len(df)):
        curve.append({
            'date': str(df.index[i])[:10],
            'value': round(df.iloc[i]['close'] / first_close, 4)
        })
    return curve


def _compute_statistics(trades: List[Dict], df: pd.DataFrame) -> Dict:
    """计算交易统计汇总"""
    if not trades:
        return _empty_result()

    # 盈亏分类
    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]

    total_trades = len(trades)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = round(win_count / total_trades * 100, 2) if total_trades > 0 else 0

    returns_list = [t['return_pct'] for t in trades]
    avg_return = round(np.mean(returns_list), 2)
    median_return = round(np.median(returns_list), 2)

    total_return = round(sum(returns_list), 2)

    # 盈亏比
    total_profit = sum(t['return_pct'] for t in wins) if wins else 0
    total_loss = abs(sum(t['return_pct'] for t in losses)) if losses else 0
    profit_factor = round(total_profit / total_loss, 2) if total_loss > 0 else float('inf')

    # 最大回撤（策略层面）
    strategy_max_dd = round(max(t['max_drawdown'] for t in trades), 2) if trades else 0

    # 策略净值曲线
    equity_curve = compute_equity_curve(trades)

    return {
        'total_trades': total_trades,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'median_return': median_return,
        'total_return': total_return,
        'profit_factor': profit_factor,
        'max_drawdown': strategy_max_dd,
        'equity_curve': equity_curve,
        'trades': trades
    }


def _empty_result() -> Dict:
    return {
        'total_trades': 0,
        'win_count': 0,
        'loss_count': 0,
        'win_rate': 0,
        'avg_return': 0,
        'median_return': 0,
        'total_return': 0,
        'profit_factor': 0,
        'max_drawdown': 0,
        'equity_curve': [],
        'trades': []
    }