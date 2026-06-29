"""
蜡烛图信号定义和识别规则
包含 30+ 种经典蜡烛图形态
"""
from enum import Enum
from typing import List, Dict, Callable, Optional
import pandas as pd
import numpy as np


class SignalType(Enum):
    BULLISH = "bullish"      # 买入信号（看涨）
    BEARISH = "bearish"      # 卖出信号（看跌）
    REVERSAL = "reversal"    # 反转信号（中性）
    CONTINUATION = "continuation"  # 突破信号（延续）


class Pattern:
    """蜡烛图模式定义"""
    def __init__(self,
                 code: str,
                 name: str,
                 signal_type: SignalType,
                 description: str,
                 rule_description: str,
                 detector: Callable[[pd.DataFrame, int], bool]):
        self.code = code
        self.name = name
        self.signal_type = signal_type
        self.description = description
        self.rule_description = rule_description
        self.detector = detector

    def check(self, df: pd.DataFrame, idx: int) -> bool:
        """检查在指定位置是否出现该模式"""
        if idx < self.required_klines() - 1:
            return False
        try:
            return self.detector(df, idx)
        except (IndexError, KeyError):
            return False

    def required_klines(self) -> int:
        """该模式需要几根K线"""
        if self.code in ['hammer', 'inverted_hammer', 'doji', 'spinning_top',
                          'marubozu_up', 'marubozu_down', 'long_body',
                          'shooting_star', 'hanging_man', 'dragonfly_doji',
                          'gravestone_doji', 'long_legged_doji']:
            return 1
        elif self.code in ['engulfing_bullish', 'engulfing_bearish', 'harami_bullish',
                           'harami_bearish', 'tweezer_top', 'tweezer_bottom',
                           'counterattack', 'separating_lines', 'bullish_kicker',
                           'bearish_kicker']:
            return 2
        elif self.code in ['morning_star', 'evening_star', 'three_white_soldiers',
                           'three_black_crows', 'three_mountain_top', 'river_valley',
                           'three_inside_up', 'three_inside_down']:
            return 3
        elif self.code in ['rising_three', 'falling_three']:
            return 5
        else:
            return 2


# ==================== 单K线模式识别函数 ====================

def is_hammer(df: pd.DataFrame, idx: int) -> bool:
    """锤头 - 单K线形态，下跌后出现，看涨反转"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    body = abs(c - o)
    lower_shadow = min(o, c) - l
    upper_shadow = h - max(o, c)
    return lower_shadow >= 2 * body and upper_shadow < 0.1 * body and body > 0

def is_inverted_hammer(df: pd.DataFrame, idx: int) -> bool:
    """倒锤头 - 单K线形态，下跌后出现，看涨反转"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    body = abs(c - o)
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    return upper_shadow >= 2 * body and lower_shadow < 0.1 * body and body > 0

def is_shooting_star(df: pd.DataFrame, idx: int) -> bool:
    """射击之星 - 单K线形态，上涨后出现，看跌反转"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    body = abs(c - o)
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    return upper_shadow >= 2 * body and lower_shadow < 0.1 * body and body > 0

def is_hanging_man(df: pd.DataFrame, idx: int) -> bool:
    """吊颈线 - 单K线形态，上涨后出现，看跌反转"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    body = abs(c - o)
    lower_shadow = min(o, c) - l
    upper_shadow = h - max(o, c)
    return lower_shadow >= 2 * body and upper_shadow < 0.1 * body and body > 0

def is_doji(df: pd.DataFrame, idx: int) -> bool:
    """十字星 - 开盘价≈收盘价，多空博弈，反转信号"""
    o, c = df.iloc[idx][['open', 'close']]
    body = abs(c - o)
    avg_range = (df.iloc[idx]['high'] - df.iloc[idx]['low'])
    return body <= 0.1 * avg_range and avg_range > 0

def is_spinning_top(df: pd.DataFrame, idx: int) -> bool:
    """纺锤线 - 小实体，上下影线较长，多空平衡"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    body = abs(c - o)
    total_range = h - l
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    return body <= 0.25 * total_range and upper_shadow >= body and lower_shadow >= body

def is_marubozu_up(df: pd.DataFrame, idx: int) -> bool:
    """光头光脚大阳线 - 无上下影线，强烈看涨"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    return c > o and abs(h - c) < 0.001 * c and abs(l - o) < 0.001 * o

def is_marubozu_down(df: pd.DataFrame, idx: int) -> bool:
    """光头光脚大阴线 - 无上下影线，强烈看跌"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    return c < o and abs(h - o) < 0.001 * o and abs(l - c) < 0.001 * c

def is_long_body(df: pd.DataFrame, idx: int) -> bool:
    """长实体 - 实体较大，表明方向明确"""
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    body = abs(c - o)
    total_range = h - l
    return body >= 0.7 * total_range and total_range > 0


# ==================== 双K线模式识别函数 ====================

def is_engulfing_bullish(df: pd.DataFrame, idx: int) -> bool:
    """看涨吞没 - 第二根阳线实体完全吞没前一根阴线实体，反转向上"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    # 前阴后阳
    if not (c1 < o1 and c2 > o2):
        return False
    # 完全吞没实体
    return o2 <= c1 and c2 >= o1

def is_engulfing_bearish(df: pd.DataFrame, idx: int) -> bool:
    """看跌吞没 - 第二根阴线实体完全吞没前一根阳线实体，反转向下"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    # 前阳后阴
    if not (c1 > o1 and c2 < o2):
        return False
    # 完全吞没实体
    return o2 >= c1 and c2 <= o1

def is_harami_bullish(df: pd.DataFrame, idx: int) -> bool:
    """孕线看涨 - 大阴线后出现小阳线，实体完全包含在前一根内，反转信号"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    # 前大阴，后小阳
    if not (c1 < o1 and c2 > o2):
        return False
    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)
    # 后一根实体完全被前一根包含
    return max(o2, c2) <= o1 and min(o2, c2) >= c1 and body2 <= 0.5 * body1

def is_harami_bearish(df: pd.DataFrame, idx: int) -> bool:
    """孕线看跌 - 大阳线后出现小阴线，反转信号"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    # 前大阳，后小阴
    if not (c1 > o1 and c2 < o2):
        return False
    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)
    # 后一根实体完全被前一根包含
    return min(o2, c2) >= o1 and max(o2, c2) <= c1 and body2 <= 0.5 * body1

def is_tweezer_top(df: pd.DataFrame, idx: int) -> bool:
    """镊子顶 - 两根K线高点相近，上涨后出现，看跌反转"""
    i1, i2 = idx - 1, idx
    h1, h2 = df.iloc[i1]['high'], df.iloc[i2]['high']
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    # 一阳一阴，高点接近
    return (c1 > o1) != (c2 > o2) and abs(h1 - h2) / h1 < 0.005

def is_tweezer_bottom(df: pd.DataFrame, idx: int) -> bool:
    """镊子底 - 两根K线低点相近，下跌后出现，看涨反转"""
    i1, i2 = idx - 1, idx
    l1, l2 = df.iloc[i1]['low'], df.iloc[i2]['low']
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    # 一阴一阳，低点接近
    return (c1 > o1) != (c2 > o2) and abs(l1 - l2) / l1 < 0.005

def is_counterattack(df: pd.DataFrame, idx: int) -> bool:
    """反击线 - 趋势中次日开盘大幅跳空，收盘回到前收盘价附近"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    if c1 < o1:  # 阴线
        # 次日跳空低开，收盘回到前收盘价附近
        if o2 < c1 and abs(c2 - c1) / c1 < 0.01:
            return True
    else:  # 阳线
        # 次日跳空高开，收盘回到前收盘价附近
        if o2 > c1 and abs(c2 - c1) / c1 < 0.01:
            return True
    return False

def is_separating_lines(df: pd.DataFrame, idx: int) -> bool:
    """分离线 - 延续原有趋势，方向明确后继续前进"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    # 趋势上涨：阴线之后高开阳线
    if c1 < o1 and c2 > o2 and o2 > o1 and abs(c1 - o2) / o2 < 0.001:
        return True
    # 趋势下跌：阳线之后低开阴线
    if c1 > o1 and c2 < o2 and o2 < o1 and abs(c1 - o2) / o2 < 0.001:
        return True
    return False


# ==================== 三K线模式识别函数 ====================

def is_morning_star(df: pd.DataFrame, idx: int) -> bool:
    """启明星（晨星）- 经典三K线底部反转，强烈看涨"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    o3, c3 = df.iloc[i3][['open', 'close']]
    # 第一根大阴线
    if not (c1 < o1 and abs(c1 - o1) > 0.6 * (df.iloc[i1]['high'] - df.iloc[i1]['low'])):
        return False
    # 第二根小实体，跳空向下
    body2 = abs(c2 - o2)
    total_range2 = df.iloc[i2]['high'] - df.iloc[i2]['low']
    if not (body2 <= 0.3 * total_range2 and max(o2, c2) < c1):
        return False
    # 第三根大阳线，收复第一根阴线实体一半以上
    if not (c3 > o3):
        return False
    # 深入第一根阴线实体
    return c3 >= (o1 + c1) / 2

def is_evening_star(df: pd.DataFrame, idx: int) -> bool:
    """黄昏星 - 经典三K线顶部反转，强烈看跌"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    o3, c3 = df.iloc[i3][['open', 'close']]
    # 第一根大阳线
    if not (c1 > o1 and abs(c1 - o1) > 0.6 * (df.iloc[i1]['high'] - df.iloc[i1]['low'])):
        return False
    # 第二根小实体，跳空向上
    body2 = abs(c2 - o2)
    total_range2 = df.iloc[i2]['high'] - df.iloc[i2]['low']
    if not (body2 <= 0.3 * total_range2 and min(o2, c2) > c1):
        return False
    # 第三根大阴线，深入第一根阳线实体一半以上
    if not (c3 < o3):
        return False
    return c3 <= (o1 + c1) / 2

def is_three_white_soldiers(df: pd.DataFrame, idx: int) -> bool:
    """三个白武士 - 三根连续阳线步步升高，强烈看涨"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    for i in [i1, i2, i3]:
        o, c = df.iloc[i][['open', 'close']]
        if c <= o:
            return False
    # 收盘价越来越高，开盘价也越来越高
    c1 = df.iloc[i1]['close']
    c2 = df.iloc[i2]['close']
    c3 = df.iloc[i3]['close']
    o1 = df.iloc[i1]['open']
    o2 = df.iloc[i2]['open']
    o3 = df.iloc[i3]['open']
    return c2 > c1 and c3 > c2 and o2 > o1 and o3 > o2

def is_three_black_crows(df: pd.DataFrame, idx: int) -> bool:
    """三只乌鸦 - 三根连续阴线步步降低，强烈看跌"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    for i in [i1, i2, i3]:
        o, c = df.iloc[i][['open', 'close']]
        if c >= o:
            return False
    c1 = df.iloc[i1]['close']
    c2 = df.iloc[i2]['close']
    c3 = df.iloc[i3]['close']
    o1 = df.iloc[i1]['open']
    o2 = df.iloc[i2]['open']
    o3 = df.iloc[i3]['open']
    return c2 < c1 and c3 < c2 and o2 < o1 and o3 < o2

def is_three_mountain_top(df: pd.DataFrame, idx: int) -> bool:
    """三山顶 - 高点依次抬高后反转，看跌"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    h1, h2, h3 = df.iloc[i1]['high'], df.iloc[i2]['high'], df.iloc[i3]['high']
    c1, c3 = df.iloc[i1]['close'], df.iloc[i3]['close']
    return h2 > h1 and h3 > h2 and c3 < h3 * 0.98

def is_river_valley(df: pd.DataFrame, idx: int) -> bool:
    """河谷 - 低点依次降低后反弹，看涨"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    l1, l2, l3 = df.iloc[i1]['low'], df.iloc[i2]['low'], df.iloc[i3]['low']
    c1, c3 = df.iloc[i1]['close'], df.iloc[i3]['close']
    return l2 < l1 and l3 < l2 and c3 > l3 * 1.02

def is_dragonfly_doji(df: pd.DataFrame, idx: int) -> bool:
    """蜻蜓十字星 - 十字星，下影线极长，上影线极短，看涨反转"""
    if not is_doji(df, idx):
        return False
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    upper = h - max(o, c)
    lower = min(o, c) - l
    return lower >= 3 * upper and upper < 0.1 * (h - l)

def is_gravestone_doji(df: pd.DataFrame, idx: int) -> bool:
    """墓碑十字星 - 十字星，上影线极长，下影线极短，看跌反转"""
    if not is_doji(df, idx):
        return False
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    upper = h - max(o, c)
    lower = min(o, c) - l
    return upper >= 3 * lower and lower < 0.1 * (h - l)

def is_long_legged_doji(df: pd.DataFrame, idx: int) -> bool:
    """长腿十字星 - 上下影线都很长，多空激烈博弈"""
    if not is_doji(df, idx):
        return False
    o, c, h, l = df.iloc[idx][['open', 'close', 'high', 'low']]
    upper = h - max(o, c)
    lower = min(o, c) - l
    total = h - l
    return upper >= 0.3 * total and lower >= 0.3 * total

def is_bullish_kicker(df: pd.DataFrame, idx: int) -> bool:
    """看涨踢出 - 前阴后阳，次日跳空高开且收盘高于前日开盘，强烈反转"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    return c1 < o1 and c2 > o2 and o2 > o1 and c2 > o1

def is_bearish_kicker(df: pd.DataFrame, idx: int) -> bool:
    """看跌踢出 - 前阳后阴，次日跳空低开且收盘低于前日开盘，强烈反转"""
    i1, i2 = idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    return c1 > o1 and c2 < o2 and o2 < o1 and c2 < o1

def is_three_inside_up(df: pd.DataFrame, idx: int) -> bool:
    """三重内升 - 孕线+突破，第三天阳线突破前两日高点，强烈看涨"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    o3, c3 = df.iloc[i3][['open', 'close']]
    h1, h2 = df.iloc[i1]['high'], df.iloc[i2]['high']
    # 前阴后小阳(孕线)，第三根阳线突破
    return c1 < o1 and c2 > o2 and max(o2, c2) <= o1 and min(o2, c2) >= c1 and c3 > o3 and c3 > h2 and c3 > h1

def is_three_inside_down(df: pd.DataFrame, idx: int) -> bool:
    """三重内降 - 孕线+跌破，第三天阴线跌破前两日低点，强烈看跌"""
    i1, i2, i3 = idx - 2, idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o2, c2 = df.iloc[i2][['open', 'close']]
    o3, c3 = df.iloc[i3][['open', 'close']]
    l1, l2 = df.iloc[i1]['low'], df.iloc[i2]['low']
    # 前阳后小阴(孕线)，第三根阴线跌破
    return c1 > o1 and c2 < o2 and min(o2, c2) >= o1 and max(o2, c2) <= c1 and c3 < o3 and c3 < l2 and c3 < l1

def is_rising_three(df: pd.DataFrame, idx: int) -> bool:
    """上升三法 - 大阳线后三根小阴线调整，再一根大阳线突破，上涨中继"""
    if idx < 4:
        return False
    i1, i2, i3, i4, i5 = idx - 4, idx - 3, idx - 2, idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o5, c5 = df.iloc[i5][['open', 'close']]
    # 第一根大阳线
    if not (c1 > o1):
        return False
    body1 = abs(c1 - o1)
    # 中间三根小阴线，在阳线实体范围内
    for j in [i2, i3, i4]:
        o, c = df.iloc[j][['open', 'close']]
        if not (c < o and o <= c1 and c >= o1):
            return False
    # 第五根大阳线突破前高
    return c5 > o5 and c5 > c1

def is_falling_three(df: pd.DataFrame, idx: int) -> bool:
    """下降三法 - 大阴线后三根小阳线反弹，再一根大阴线下破，下跌中继"""
    if idx < 4:
        return False
    i1, i2, i3, i4, i5 = idx - 4, idx - 3, idx - 2, idx - 1, idx
    o1, c1 = df.iloc[i1][['open', 'close']]
    o5, c5 = df.iloc[i5][['open', 'close']]
    # 第一根大阴线
    if not (c1 < o1):
        return False
    body1 = abs(c1 - o1)
    # 中间三根小阳线，在阴线实体范围内
    for j in [i2, i3, i4]:
        o, c = df.iloc[j][['open', 'close']]
        if not (c > o and o >= c1 and c <= o1):
            return False
    # 第五根大阴线跌破前低
    return c5 < o5 and c5 < c1


# ==================== 注册所有模式 ====================

PATTERNS: List[Pattern] = [
    # 单K线 - 买入信号
    Pattern('hammer', '锤头', SignalType.BULLISH,
            '下跌趋势后出现，下影线长度是实体两倍以上，上影线极短，暗示底部支撑较强，看涨反转',
            '1根K线，下影线 ≥ 2×实体，上影线 < 0.1×实体',
            is_hammer),
    Pattern('inverted_hammer', '倒锤头', SignalType.BULLISH,
            '下跌趋势后出现，上影线长度是实体两倍以上，暗示抛压减轻上方开始吸筹，看涨反转',
            '1根K线，上影线 ≥ 2×实体，下影线 < 0.1×实体',
            is_inverted_hammer),
    Pattern('marubozu_up', '光头光脚大阳线', SignalType.BULLISH,
            '无上下影线，开盘价即最低价，收盘价即最高价，多头力量完全释放，强烈看涨',
            '1根K线，收盘 > 开盘，最高价≈收盘，最低价≈开盘',
            is_marubozu_up),
    Pattern('long_body_bull', '长实体阳线', SignalType.BULLISH,
            '实体占K线范围70%以上，方向明确，多头占据优势，看涨',
            '1根K线，阳线，实体 ≥ 0.7×K线范围',
            lambda df, idx: is_long_body(df, idx) and df.iloc[idx]['close'] > df.iloc[idx]['open']),

    # 单K线 - 卖出信号
    Pattern('shooting_star', '射击之星', SignalType.BEARISH,
            '上涨趋势后出现，上影线长度是实体两倍以上，上方抛压沉重，看跌反转',
            '1根K线，上影线 ≥ 2×实体，下影线 < 0.1×实体',
            is_shooting_star),
    Pattern('hanging_man', '吊颈线', SignalType.BEARISH,
            '上涨趋势后出现，下影线很长实体很小，暗示下方获利回吐，看跌反转',
            '1根K线，下影线 ≥ 2×实体，上影线 < 0.1×实体',
            is_hanging_man),
    Pattern('marubozu_down', '光头光脚大阴线', SignalType.BEARISH,
            '无上下影线，开盘价即最高价，收盘价即最低价，空头力量完全释放，强烈看跌',
            '1根K线，收盘 < 开盘，最高价≈开盘，最低价≈收盘',
            is_marubozu_down),
    Pattern('long_body_bear', '长实体阴线', SignalType.BEARISH,
            '实体占K线范围70%以上，方向明确，空头占据优势，看跌',
            '1根K线，阴线，实体 ≥ 0.7×K线范围',
            lambda df, idx: is_long_body(df, idx) and df.iloc[idx]['close'] < df.iloc[idx]['open']),

    # 单K线 - 反转信号
    Pattern('doji', '十字星', SignalType.REVERSAL,
            '开盘价≈收盘价，实体极小，多空力量达到平衡，原有趋势可能反转',
            '1根K线，实体 ≤ 0.1×K线范围',
            is_doji),
    Pattern('dragonfly_doji', '蜻蜓十字星', SignalType.BULLISH,
            '十字星变体，下影线极长上影线极短，底部出现看涨，是强烈的买入信号',
            '1根K线，实体 ≤ 0.1×范围，下影线 ≥ 3×上影线',
            is_dragonfly_doji),
    Pattern('gravestone_doji', '墓碑十字星', SignalType.BEARISH,
            '十字星变体，上影线极长下影线极短，顶部出现看跌，是强烈的卖出信号',
            '1根K线，实体 ≤ 0.1×范围，上影线 ≥ 3×下影线',
            is_gravestone_doji),
    Pattern('long_legged_doji', '长腿十字星', SignalType.REVERSAL,
            '上下影线都极长，多空激烈博弈达到平衡，预示剧烈反转',
            '1根K线，实体 ≤ 0.1×范围，上影线 ≥ 0.3×范围，下影线 ≥ 0.3×范围',
            is_long_legged_doji),
    Pattern('spinning_top', '纺锤线', SignalType.REVERSAL,
            '小实体，上下影线都很长，多空拉锯，原有趋势可能改变',
            '1根K线，实体 ≤ 0.25×范围，上下影线 ≥ 实体',
            is_spinning_top),

    # 双K线 - 买入信号
    Pattern('engulfing_bullish', '看涨吞没', SignalType.BULLISH,
            '阴线之后被一根阳线完全吞没，说明多方力量反转，看涨',
            '2根K线，前阴后阳，阳线实体完全吞没阴线实体：o2 ≤ c1, c2 ≥ o1',
            is_engulfing_bullish),
    Pattern('harami_bullish', '看涨孕线', SignalType.BULLISH,
            '大阴线后孕育一根小阳线，反转信号，跌幅放缓开始酝酿上涨',
            '2根K线，前大阴后小阳，小阳线实体完全在阴线实体内部',
            is_harami_bullish),
    Pattern('tweezer_bottom', '镊子底', SignalType.BULLISH,
            '两根K线低点价格几乎相同，一阴一阳，底部支撑确认，看涨反转',
            '2根K线，低点价差 < 0.5%，一阴一阳',
            is_tweezer_bottom),

    # 双K线 - 卖出信号
    Pattern('engulfing_bearish', '看跌吞没', SignalType.BEARISH,
            '阳线之后被一根阴线完全吞没，说明空方力量反转，看跌',
            '2根K线，前阳后阴，阴线实体完全吞没阳线实体：o2 ≥ c1, c2 ≤ o1',
            is_engulfing_bearish),
    Pattern('harami_bearish', '看跌孕线', SignalType.BEARISH,
            '大阳线后孕育一根小阴线，反转信号，涨幅见顶开始酝酿下跌',
            '2根K线，前大阳后小阴，小阴线实体完全在阳线实体内部',
            is_harami_bearish),
    Pattern('tweezer_top', '镊子顶', SignalType.BEARISH,
            '两根K线高点价格几乎相同，一阳一阴，顶部压力确认，看跌反转',
            '2根K线，高点价差 < 0.5%，一阳一阴',
            is_tweezer_top),

    # 双K线 - 反转/突破
    Pattern('counterattack', '反击线', SignalType.REVERSAL,
            '趋势中次日大幅跳空后收盘回到前收盘价，对抗原有趋势，准备反转',
            '2根K线，次日跳空后收盘回到前收盘价附近',
            is_counterattack),
    Pattern('separating_lines', '分离线', SignalType.CONTINUATION,
            '原有趋势中，开盘跳空分离，继续沿着原有方向前进，趋势延续信号',
            '2根K线，阴线后高开阳线，阳线后低开阴线，趋势延续',
            is_separating_lines),
    Pattern('bullish_kicker', '看涨踢出', SignalType.BULLISH,
            '阴线后次日跳空高开阳线且收盘高于前日开盘，多方强势反转，强烈看涨',
            '2根K线，前阴后阳，跳空高开，收盘 > 前日开盘',
            is_bullish_kicker),
    Pattern('bearish_kicker', '看跌踢出', SignalType.BEARISH,
            '阳线后次日跳空低开阴线且收盘低于前日开盘，空方强势反转，强烈看跌',
            '2根K线，前阳后阴，跳空低开，收盘 < 前日开盘',
            is_bearish_kicker),

    # 三K线 - 买入信号
    Pattern('morning_star', '启明星', SignalType.BULLISH,
            '经典底部反转：大阴线 + 小实体 + 大阳线，深入阴线实体一半以上，强烈看涨',
            '3根K线，大阴→小实体跳空→大阳线收复失地',
            is_morning_star),
    Pattern('three_white_soldiers', '三个白武士', SignalType.BULLISH,
            '三根连续阳线，收盘价和开盘价步步升高，多方稳步推进，强烈看涨',
            '3根K线，三根阳线，收盘价越来越高，开盘价越来越高',
            is_three_white_soldiers),
    Pattern('river_valley', '河谷', SignalType.BULLISH,
            '低点依次降低后最终反弹上涨，下跌动能耗尽，看涨反转',
            '3根K线，低点依次降低，第三根收盘上涨',
            is_river_valley),

    # 三K线 - 卖出信号
    Pattern('evening_star', '黄昏星', SignalType.BEARISH,
            '经典顶部反转：大阳线 + 小实体 + 大阴线，深入阳线实体一半以上，强烈看跌',
            '3根K线，大阳→小实体跳空→大阴线吞噬涨幅',
            is_evening_star),
    Pattern('three_black_crows', '三只乌鸦', SignalType.BEARISH,
            '三根连续阴线，收盘价和开盘价步步降低，空方稳步下压，强烈看跌',
            '3根K线，三根阴线，收盘价越来越低，开盘价越来越低',
            is_three_black_crows),
    Pattern('three_mountain_top', '三山顶', SignalType.BEARISH,
            '高点依次抬高后最终收盘下跌，上涨动能耗尽，看跌反转',
            '3根K线，高点依次升高，第三根收盘下跌',
            is_three_mountain_top),
    Pattern('three_inside_up', '三重内升', SignalType.BULLISH,
            '孕线后阳线突破前两日高点，反复确认后向上突破，强烈看涨',
            '3根K线，前阴后小阳（孕线），第三根阳线突破前两日高点',
            is_three_inside_up),
    Pattern('three_inside_down', '三重内降', SignalType.BEARISH,
            '孕线后阴线跌破前两日低点，反复确认后向下突破，强烈看跌',
            '3根K线，前阳后小阴（孕线），第三根阴线跌破前两日低点',
            is_three_inside_down),

    # 五K线 - 延续形态
    Pattern('rising_three', '上升三法', SignalType.CONTINUATION,
            '大阳线+三根小阴线调整+大阳线创新高，上涨中继形态，趋势继续看涨',
            '5根K线，大阳→三小阴调整→大阳突破',
            is_rising_three),
    Pattern('falling_three', '下降三法', SignalType.CONTINUATION,
            '大阴线+三根小阳线反弹+大阴线创新低，下跌中继形态，趋势继续看跌',
            '5根K线，大阴→三小阳反弹→大阴跌破',
            is_falling_three),
]


def get_all_patterns() -> List[Pattern]:
    """获取所有注册的蜡烛图模式"""
    return PATTERNS


def get_pattern_by_code(code: str) -> Optional[Pattern]:
    """根据代码获取模式"""
    for p in PATTERNS:
        if p.code == code:
            return p
    return None


def get_patterns_by_type(signal_type: SignalType) -> List[Pattern]:
    """按类型筛选模式"""
    return [p for p in PATTERNS if p.signal_type == signal_type]


def detect_all_signals(df: pd.DataFrame) -> pd.DataFrame:
    """在整个K线序列上检测所有信号，返回每个位置检测到的信号列表"""
    signals = [[] for _ in range(len(df))]

    for pattern in PATTERNS:
        n = len(df)
        req = pattern.required_klines()
        for i in range(req - 1, n):
            if pattern.check(df, i):
                signals[i].append(pattern.code)

    # 添加为新列
    df_result = df.copy()
    df_result['signals'] = signals
    return df_result


def get_patterns_info() -> List[Dict]:
    """获取所有模式的信息列表（用于前端展示）"""
    return [{
        'code': p.code,
        'name': p.name,
        'type': p.signal_type.value,
        'description': p.description,
        'rule_description': p.rule_description
    } for p in PATTERNS]
