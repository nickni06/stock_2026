"""
市场阶段识别引擎
基于趋势（MA20 vs MA60）和波动率（ATR%）判断当前市场阶段
"""
import pandas as pd
import numpy as np


def detect_market_phase(df: pd.DataFrame) -> dict:
    """
    识别当前市场阶段
    阶段 1：趋势 + 高波动 (trend_high_vol)
    阶段 2：趋势 + 低波动 (trend_low_vol)
    阶段 3：横盘 + 高波动 (range_high_vol)
    阶段 4：横盘 + 低波动 (range_low_vol)
    """
    if len(df) < 60:
        return {'phase': 'unknown', 'label': '数据不足', 'ma20': 0, 'ma60': 0, 'atr_pct': 0}

    # 计算均线
    df = df.copy()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()

    # 趋势判断：MA20 与 MA60 的关系
    ma20 = df['ma20'].iloc[-1]
    ma60 = df['ma60'].iloc[-1]

    if pd.isna(ma20) or pd.isna(ma60):
        return {'phase': 'unknown', 'label': '数据不足', 'ma20': 0, 'ma60': 0, 'atr_pct': 0}

    # 趋势强度：MA20偏离MA60的百分比
    trend_deviation = abs(ma20 - ma60) / ma60 * 100 if ma60 > 0 else 0

    # 判断趋势还是横盘（偏离超过2%视为趋势）
    is_trend = trend_deviation > 2.0
    trend_direction = 'up' if ma20 > ma60 else 'down'

    # 计算 ATR（平均真实波幅）
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(window=14).mean()
    atr = df['atr'].iloc[-1]
    current_price = df['close'].iloc[-1]

    atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

    # 波动率判断：ATR%超过2%视为高波动
    is_high_vol = atr_pct > 2.0

    # 确定阶段
    if is_trend:
        if is_high_vol:
            phase = 'trend_high_vol'
            label = f'趋势({trend_direction}) + 高波动'
        else:
            phase = 'trend_low_vol'
            label = f'趋势({trend_direction}) + 低波动'
    else:
        if is_high_vol:
            phase = 'range_high_vol'
            label = '横盘 + 高波动'
        else:
            phase = 'range_low_vol'
            label = '横盘 + 低波动'

    return {
        'phase': phase,
        'label': label,
        'ma20': round(ma20, 2),
        'ma60': round(ma60, 2),
        'atr_pct': round(atr_pct, 2),
        'trend_deviation': round(trend_deviation, 2),
        'trend_direction': trend_direction,
        'current_price': round(current_price, 2)
    }


def get_phase_mask(df: pd.DataFrame, phase: str) -> pd.Series:
    """
    返回一个布尔序列，标记哪些K线位置属于指定的市场阶段
    用于阶段匹配回测
    """
    n = len(df)
    mask = pd.Series([False] * n, index=df.index)

    if len(df) < 60:
        return mask

    df = df.copy()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(window=14).mean()

    for i in range(60, n):
        ma20_i = df['ma20'].iloc[i]
        ma60_i = df['ma60'].iloc[i]
        atr_i = df['atr'].iloc[i]
        price_i = df['close'].iloc[i]

        if pd.isna(ma20_i) or pd.isna(ma60_i) or pd.isna(atr_i) or price_i == 0:
            continue

        trend_dev = abs(ma20_i - ma60_i) / ma60_i * 100
        is_trend = trend_dev > 2.0
        atr_pct = (atr_i / price_i) * 100
        is_high_vol = atr_pct > 2.0

        phase_i = ''
        if is_trend:
            phase_i = 'trend_high_vol' if is_high_vol else 'trend_low_vol'
        else:
            phase_i = 'range_high_vol' if is_high_vol else 'range_low_vol'

        if phase_i == phase:
            mask.iloc[i] = True

    return mask