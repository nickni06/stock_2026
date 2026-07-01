"""
数据获取模块
通过 akshare 获取 A 股、ETF、板块指数的日K线数据
"""
import os

import akshare as ak
import pandas as pd
import traceback
from typing import Dict, Optional, List
import json


WATCHLIST_FILE = '/workspace/candlestick-signal/data/watchlist.json'

# 保存一些常用标的的索引，用于快速搜索
SYMBOLS_CACHE = '/workspace/candlestick-signal/data/symbols_cache.json'

# 新浪 HTTP API 获取K线（环境代理不支持HTTPS连接金融数据源，但HTTP可以）
SINA_KLINE_URL = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'


def _fetch_kline_sina(symbol: str, is_etf: bool = False) -> Optional[pd.DataFrame]:
    """通过新浪 HTTP API 获取日K线数据"""
    try:
        # 确定交易所前缀
        if is_etf:
            prefix = 'sh' if symbol.startswith('51') else 'sz'
        elif symbol.startswith('6') or symbol.startswith('9'):
            prefix = 'sh'
        else:
            prefix = 'sz'

        import requests
        params = {
            'symbol': f'{prefix}{symbol}',
            'datalen': 1024,
            'scale': 240,   # 日线
            'ma': 'no',
        }
        resp = requests.get(SINA_KLINE_URL, params=params, timeout=15,
                            headers={'Referer': 'https://finance.sina.com.cn'})
        resp.raise_for_status()
        data = resp.json()
        if not data or not isinstance(data, list) or 'day' not in data[0]:
            return None

        rows = []
        for item in data:
            rows.append({
                'date': item['day'],
                'open': float(item['open']),
                'high': float(item['high']),
                'low': float(item['low']),
                'close': float(item['close']),
                'volume': int(float(item['volume'])),
            })

        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.sort_index()
        return df
    except Exception as e:
        print(f"Error fetching sina kline for {symbol}: {type(e).__name__}: {e}")
        return None


def get_kline(symbol: str, symbol_type: str = 'stock') -> Optional[pd.DataFrame]:
    """
    获取日K线数据
    symbol: 股票代码/名称
    symbol_type: stock (个股) | etf | sector (板块指数)
    """
    try:
        print(f"[data_fetcher] get_kline: symbol={symbol}, type={symbol_type}", flush=True)
        if symbol_type == 'stock':
            # 使用新浪 HTTP API 获取K线（环境代理不支持HTTPS连接金融数据源）
            df = _fetch_kline_sina(symbol)
        elif symbol_type == 'etf':
            df = _fetch_kline_sina(symbol, is_etf=True)
        elif symbol_type == 'sector':
            # 板块指数使用东财数据（通过代理HTTP）
            df = ak.stock_board_ths_hist_data(index=symbol)
        else:
            df = _fetch_kline_sina(symbol)

        if df is None or len(df) < 60:
            return None

        # _fetch_kline_sina 返回的 df 已经标准化（date为index, open/high/low/close/volume为列）
        # 而 akshare 返回的 df 需要转换
        if '日期' in df.columns:
            # akshare 中文列名 → 标准化
            df.rename(columns={'日期': 'date', '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close', '成交量': 'volume'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

        # 确保所有需要的列都存在且是数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                print(f"[data_fetcher] missing column: {col}, columns={list(df.columns)}")
                return None
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 移除空值
        df = df.dropna()

        # 保留最近 5 年数据
        if len(df) > 252 * 5:
            df = df.iloc[-(252 * 5):]

        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None


def get_recent_kline(symbol: str, symbol_type: str = 'stock', days: int = 120) -> Optional[pd.DataFrame]:
    """获取最近N天的K线数据"""
    df = get_kline(symbol, symbol_type)
    if df is None:
        return None
    if len(df) > days:
        return df.iloc[-days:]
    return df


def _load_local_cache() -> List[Dict]:
    """加载本地标的缓存"""
    try:
        if os.path.exists(SYMBOLS_CACHE):
            with open(SYMBOLS_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []


def _search_from_cache(keyword: str) -> List[Dict]:
    """从本地缓存中搜索标的"""
    cache = _load_local_cache()
    if not cache:
        return []

    keyword_lower = keyword.lower()
    results = []
    for item in cache:
        code = item['code']
        name = item.get('name', code)
        if (keyword_lower in code.lower() or
            keyword_lower in name.lower() or
            is_pinyin_match(name, keyword_lower)):
            results.append({
                'code': code,
                'name': name,
                'type': 'stock',
                'last_price': 0,
                'change_pct': 0
            })
            if len(results) >= 20:
                break
    return results


_network_available = None


def _check_network() -> bool:
    """检测网络是否可用（缓存结果，避免每次都检测）"""
    global _network_available
    if _network_available is not None:
        return _network_available
    try:
        import socket
        socket.setdefaulttimeout(2)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("www.baidu.com", 80))
        _network_available = True
    except Exception:
        _network_available = False
    return _network_available


def search_symbols(keyword: str) -> List[Dict]:
    """
    模糊搜索标的（股票、ETF、板块）
    支持：代码、名称、拼音首字母
    网络不可用时使用本地缓存
    """
    cache_result = _search_from_cache(keyword)

    if not _check_network():
        return cache_result[:20]

    try:
        keyword_lower = keyword.lower()
        stock_info = ak.stock_info_a_code_name()

        result = []
        for _, row in stock_info.iterrows():
            code = str(row['code'])
            name = str(row['name'])
            if (keyword_lower in code.lower() or
                keyword_lower in name.lower() or
                is_pinyin_match(name, keyword_lower)):
                result.append({
                    'code': code,
                    'name': name,
                    'type': 'stock',
                    'last_price': 0,
                    'change_pct': 0
                })
                if len(result) >= 20:
                    break

        if len(result) > 0:
            return result[:20]
    except Exception as e:
        print(f"Network search failed, using local cache: {e}")

    return cache_result[:20]


def is_pinyin_match(name: str, keyword: str) -> bool:
    """简单拼音首字母匹配，只针对常见声母做近似匹配"""
    if len(keyword) > len(name):
        return False

    import re
    pinyin_initial_map = {
        '一': 'y', '二': 'e', '三': 's', '四': 's', '五': 'w', '六': 'l', '七': 'q', '八': 'b', '九': 'j', '十': 's',
        '百': 'b', '千': 'q', '万': 'w', '亿': 'y',
        '中': 'z', '国': 'g', '上': 's', '海': 'h', '北': 'b', '京': 'j', '深': 's', '圳': 'z',
        '银': 'y', '行': 'h', '证': 'z', '券': 'q', '保': 'b', '险': 'x', '基': 'j', '金': 'j',
        '科': 'k', '技': 'j', '信': 'x', '息': 'x', '互': 'h', '联': 'l', '网': 'w',
        '医': 'y', '药': 'y', '生': 's', '物': 'w', '环': 'h', '保': 'b',
        '能': 'n', '源': 'y', '石': 's', '油': 'y', '煤': 'm', '炭': 't',
        '汽': 'q', '车': 'c', '房': 'f', '地': 'd', '产': 'c',
        '食': 's', '品': 'p', '饮': 'y', '料': 'l',
        '电': 'd', '子': 'z', '半': 'b', '导': 'd', '体': 't', '芯': 'x', '片': 'p',
        '五': 'g', '粮': 'l', '液': 'y', '晶': 'j', '光': 'g',
        '航': 'h', '空': 'k', '航': 'h', '天': 't', '军': 'j', '工': 'g',
        '金': 'j', '融': 'r', '证': 'z', '券': 'q',
        '酒': 'j', '店': 'd', '旅': 'l', '游': 'y',
        '建': 'j', '筑': 'z', '材': 'c', '料': 'l',
        '钢': 'g', '铁': 't', '有': 'y', '色': 's', '有': 'y', '机': 'j',
        '农': 'n', '林': 'l', '牧': 'm', '渔': 'y',
        '商': 's', '贸': 'm', '零': 'l', '售': 's',
        '运': 'y', '输': 's', '物': 'w', '流': 'l',
        '传': 'c', '媒': 'm', '文': 'w', '化': 'h',
        '电': 'd', '力': 'l', '水': 's', '电': 'd', '热': 'r', '力': 'l',
        '水': 'n', '泥': 'n', '玻': 'b', '璃': 'l',
        '家': 'j', '电': 'd', '家': 'j', '居': 'j',
        '服': 'f', '装': 'z', '纺': 'f', '织': 'z',
        '化': 'h', '工': 'g', '化': 'h', '学': 'x',
        '机': 'j', '械': 'x', '设': 's', '备': 'b',
        '交': 'j', '通': 't', '运': 'y', '输': 's',
        '娱': 'y', '乐': 'l', '文': 'w', '体': 't', '育': 'y',
        '长': 'c', '城': 'c', '平': 'p', '安': 'a',
        '招': 'z', '商': 's', '发': 'f', '展': 'z',
        '兴': 'x', '业': 'y', '民': 'm', '生': 's',
        '浦': 'p', '东': 'd', '发': 'f', '展': 'z',
        '工': 'g', '商': 's', '银': 'y', '行': 'h',
        '建': 'j', '设': 's', '银': 'y', '行': 'h',
        '农': 'n', '业': 'y', '银': 'y', '行': 'h',
        '交': 'j', '通': 't', '银': 'y', '行': 'h',
        '光': 'g', '大': 'd', '证': 'z', '券': 'q',
        '华': 'h', '泰': 't', '信': 'x', '业': 'y',
        '广': 'g', '发': 'f', '证': 'z', '券': 'q',
    }

    # 提取汉字，尝试匹配首字母
    name_clean = re.sub(r'[a-zA-Z0-9\s]+', '', name)
    collected_initials = []
    for char in name_clean:
        if char in pinyin_initial_map:
            collected_initials.append(pinyin_initial_map[char])

    if not collected_initials:
        return False

    # 完整首字母匹配
    collected = ''.join(collected_initials)
    return keyword in collected.lower()


def load_watchlist() -> List[Dict]:
    """加载关注列表"""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    try:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_watchlist(watchlist: List[Dict]) -> bool:
    """保存关注列表"""
    try:
        os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def add_to_watchlist(symbol_info: Dict) -> bool:
    """添加标的到关注列表"""
    watchlist = load_watchlist()
    # 去重
    watchlist = [item for item in watchlist if item['code'] != symbol_info['code']]
    watchlist.append(symbol_info)
    return save_watchlist(watchlist)


def remove_from_watchlist(code: str) -> bool:
    """从关注列表移除标的"""
    watchlist = load_watchlist()
    watchlist = [item for item in watchlist if item['code'] != code]
    return save_watchlist(watchlist)


def format_kline_for_frontend(df: pd.DataFrame) -> List[Dict]:
    """将K线DataFrame转换为前端可用的JSON格式"""
    result = []
    df = df.reset_index()
    for _, row in df.iterrows():
        result.append({
            'date': str(row['date'])[:10],
            'open': round(float(row['open']), 2),
            'high': round(float(row['high']), 2),
            'low': round(float(row['low']), 2),
            'close': round(float(row['close']), 2),
            'volume': int(row['volume']) if 'volume' in row else 0
        })
    return result