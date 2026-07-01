"""
蜡烛图信号系统 - Flask 后端 API
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import pandas as pd
from patterns import get_all_patterns, get_patterns_info, SignalType
from backtest_engine import backtest_signal, backtest_all_signals, compute_benchmark_curve
from market_phase import detect_market_phase, get_phase_mask


def _convert_np(obj):
    """递归转换 numpy 类型为原生 Python 类型"""
    if isinstance(obj, dict):
        return {k: _convert_np(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_np(v) for v in obj]
    if hasattr(obj, 'item'):
        return obj.item()
    if isinstance(obj, float):
        return round(obj, 4)
    return obj


from data_fetcher import (
    get_kline, get_recent_kline, search_symbols,
    format_kline_for_frontend, load_watchlist, save_watchlist,
    add_to_watchlist, remove_from_watchlist
)

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)


# ==================== 首页 ====================
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ==================== 标的搜索 ====================
@app.route('/api/symbols/search', methods=['GET', 'POST'])
def api_symbols_search():
    """模糊搜索标的（支持 GET query 和 POST form/JSON body）"""
    if request.method == 'POST':
        keyword = request.form.get('q', '').strip()
        if not keyword:
            data = request.get_json(silent=True) or {}
            keyword = data.get('q', '').strip()
    else:
        keyword = request.args.get('q', '').strip()
    if len(keyword) < 1:
        return jsonify({'results': []})
    results = search_symbols(keyword)
    return jsonify({'results': results})


# ==================== K线数据 ====================
@app.route('/api/kline')
def api_kline():
    """获取K线数据"""
    symbol = request.args.get('symbol', '').strip()
    symbol_type = request.args.get('type', 'stock')
    days = request.args.get('days', 120, type=int)

    if not symbol:
        return jsonify({'error': '缺少标的代码'}), 400

    df = get_recent_kline(symbol, symbol_type, days)
    if df is None:
        return jsonify({'error': '获取数据失败'}), 404

    kline_data = format_kline_for_frontend(df)
    return jsonify({'kline': kline_data, 'symbol': symbol, 'total': len(kline_data)})


# ==================== 信号库 ====================
@app.route('/api/patterns')
def api_patterns():
    """获取所有蜡烛图信号定义"""
    signal_type = request.args.get('type', '')
    patterns = get_patterns_info()
    if signal_type:
        patterns = [p for p in patterns if p['type'] == signal_type]
    return jsonify({'patterns': patterns, 'total': len(patterns)})


# ==================== 最优信号挖掘 ====================
@app.route('/api/optimize')
def api_optimize():
    """挖掘最优信号"""
    symbol = request.args.get('symbol', '').strip()
    symbol_type = request.args.get('type', 'stock')
    top_n = request.args.get('top_n', 5, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    if not symbol:
        return jsonify({'error': '缺少标的代码'}), 400

    # 获取全量K线数据
    df = get_kline(symbol, symbol_type)
    if df is None:
        return jsonify({'error': '获取数据失败'}), 404

    # 按日期范围过滤
    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    if len(df) < 60:
        return jsonify({'error': '数据不足，至少需要60根K线'}), 400

    # 检测市场阶段
    phase_info = detect_market_phase(df)
    phase_mask = get_phase_mask(df, phase_info['phase'])

    # 全量回测所有信号
    all_results = backtest_all_signals(df, hold_days=5)

    # 阶段匹配回测
    phase_results = backtest_all_signals(df, hold_days=5, phase_mask=phase_mask)

    # 计算综合评分
    for r in all_results:
        total = r['total_trades']
        if total > 0:
            score = (r['win_rate'] / 100 * 0.4) + (r['avg_return'] * 0.3) + (min(total, 50) / 50 * 0.2) + (min(r['profit_factor'], 10) / 10 * 0.1)
            score = round(score * 100, 2)
        else:
            score = 0
        r['score'] = score

    for r in phase_results:
        total = r['total_trades']
        if total > 0:
            score = (r['win_rate'] / 100 * 0.4) + (r['avg_return'] * 0.3) + (min(total, 50) / 50 * 0.2) + (min(r['profit_factor'], 10) / 10 * 0.1)
            score = round(score * 100, 2)
        else:
            score = 0
        r['score'] = score

    # 按评分排序，取 Top N
    all_sorted = sorted(all_results, key=lambda x: x['score'], reverse=True)
    phase_sorted = sorted(phase_results, key=lambda x: x['score'], reverse=True)

    # 分离买点和卖点
    def split_by_type(results):
        buy = [r for r in results if r['signal_type'] == 'bullish']
        sell = [r for r in results if r['signal_type'] == 'bearish']
        return buy, sell

    all_buy, all_sell = split_by_type(all_sorted)
    phase_buy, phase_sell = split_by_type(phase_sorted)

    # 转换 numpy 类型为原生 Python 类型以支持 JSON 序列化
    return jsonify({
        'symbol': symbol,
        'phase': phase_info,
        'top_n': top_n,
        'all_history': {
            'buy_signals': _convert_np(all_buy[:top_n]),
            'sell_signals': _convert_np(all_sell[:top_n])
        },
        'phase_matched': {
            'buy_signals': _convert_np(phase_buy[:top_n]),
            'sell_signals': _convert_np(phase_sell[:top_n]),
            'sample_count': int(phase_mask.sum())
        }
    })


# ==================== 信号回测 ====================
@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """执行信号回测"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '缺少请求体'}), 400

    symbol = data.get('symbol', '').strip()
    symbol_type = data.get('type', 'stock')
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')
    pattern_codes = data.get('patterns', [])  # 选中的信号列表
    hold_days = data.get('hold_days', 5)

    if not symbol:
        return jsonify({'error': '缺少标的代码'}), 400

    df = get_kline(symbol, symbol_type)
    if df is None:
        return jsonify({'error': '获取数据失败'}), 404

    # 按日期范围过滤
    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    if len(df) < 60:
        return jsonify({'error': '数据不足'}), 400

    # 如果未指定信号，使用全部
    if not pattern_codes:
        pattern_codes = [p.code for p in get_all_patterns()]

    # 执行回测
    result = backtest_signal(df, pattern_codes, hold_days)

    # 基准曲线
    benchmark_curve = compute_benchmark_curve(df)

    # K线数据
    kline_data = format_kline_for_frontend(df)

    # 检测所有信号位置
    signal_positions = []
    from patterns import detect_all_signals
    df_with_signals = detect_all_signals(df)
    for i in range(len(df_with_signals)):
        row = df_with_signals.iloc[i]
        if row['signals']:
            for code in row['signals']:
                if code in pattern_codes or not pattern_codes:
                    from patterns import get_pattern_by_code
                    p = get_pattern_by_code(code)
                    if p:
                        signal_positions.append({
                            'date': str(df_with_signals.index[i])[:10],
                            'index': i,
                            'signal_code': code,
                            'signal_name': p.name,
                            'signal_type': p.signal_type.value
                        })

    return jsonify({
        'symbol': symbol,
        'statistics': _convert_np({
            'total_trades': result['total_trades'],
            'win_count': result['win_count'],
            'loss_count': result['loss_count'],
            'win_rate': result['win_rate'],
            'avg_return': result['avg_return'],
            'median_return': result['median_return'],
            'total_return': result['total_return'],
            'profit_factor': str(result['profit_factor']),
            'max_drawdown': result['max_drawdown']
        }),
        'equity_curve': _convert_np(result['equity_curve']),
        'benchmark_curve': benchmark_curve,
        'kline': kline_data,
        'signal_positions': signal_positions,
        'trades': _convert_np(result['trades'])
    })


# ==================== 关注列表 ====================
@app.route('/api/watchlist')
def api_watchlist():
    """获取关注列表"""
    watchlist = load_watchlist()
    return jsonify({'watchlist': watchlist, 'total': len(watchlist)})


@app.route('/api/watchlist/add', methods=['POST'])
def api_watchlist_add():
    """添加标的到关注列表"""
    data = request.get_json()
    if not data or not data.get('code'):
        return jsonify({'error': '缺少标的信息'}), 400
    success = add_to_watchlist(data)
    return jsonify({'success': success})


@app.route('/api/watchlist/remove', methods=['POST'])
def api_watchlist_remove():
    """从关注列表移除标的"""
    data = request.get_json()
    if not data or not data.get('code'):
        return jsonify({'error': '缺少标的代码'}), 400
    success = remove_from_watchlist(data['code'])
    return jsonify({'success': success})


# ==================== 全量扫描 ====================
@app.route('/api/scan')
def api_scan():
    """扫描关注列表中所有标的，筛选当前出现信号的标的"""
    signal_type_filter = request.args.get('signal_type', '')  # bullish/bearish/continuation
    phase_only = request.args.get('phase_only', 'false') == 'true'

    watchlist = load_watchlist()
    if not watchlist:
        return jsonify({'results': [], 'total': 0})

    results = []
    from patterns import detect_all_signals, get_pattern_by_code

    for item in watchlist:
        try:
            df = get_recent_kline(item['code'], item.get('type', 'stock'), 30)
            if df is None or len(df) < 5:
                continue

            df_with = detect_all_signals(df)
            latest_signals = df_with['signals'].iloc[-1]

            if not latest_signals:
                continue

            latest_price = df_with['close'].iloc[-1]

            # 市场阶段信息
            phase_info = detect_market_phase(df)

            for code in latest_signals:
                p = get_pattern_by_code(code)
                if not p:
                    continue

                # 按信号类型过滤
                if signal_type_filter and p.signal_type.value != signal_type_filter:
                    continue

                # 阶段匹配检查
                phase_matched = False
                if phase_only and phase_info.get('phase'):
                    phase_mask = get_phase_mask(df, phase_info['phase'])
                    # 最新K线是否在阶段匹配区间内
                    if phase_mask.iloc[-1]:
                        phase_matched = True
                else:
                    phase_matched = True

                if phase_only and not phase_matched:
                    continue

                results.append({
                    'symbol_code': item['code'],
                    'symbol_name': item.get('name', item['code']),
                    'symbol_type': item.get('type', 'stock'),
                    'signal_code': code,
                    'signal_name': p.name,
                    'signal_type': p.signal_type.value,
                    'signal_date': str(df_with.index[-1])[:10],
                    'last_price': round(latest_price, 2),
                    'phase_matched': phase_matched,
                    'phase_label': phase_info.get('label', '')
                })
        except:
            continue

    return jsonify({'results': results, 'total': len(results)})


# ==================== 信号提醒 ====================
@app.route('/api/alerts')
def api_alerts():
    """获取关注列表中最新出现的信号提醒"""
    watchlist = load_watchlist()
    if not watchlist:
        return jsonify({'alerts': [], 'total': 0})

    alerts = []
    from patterns import detect_all_signals, get_pattern_by_code

    for item in watchlist:
        try:
            df = get_recent_kline(item['code'], item.get('type', 'stock'), 5)
            if df is None or len(df) < 3:
                continue

            df_with = detect_all_signals(df)
            latest_signals = df_with['signals'].iloc[-1]

            if not latest_signals:
                continue

            latest_price = df_with['close'].iloc[-1]
            phase_info = detect_market_phase(df)

            for code in latest_signals:
                p = get_pattern_by_code(code)
                if not p:
                    continue
                alerts.append({
                    'symbol_code': item['code'],
                    'symbol_name': item.get('name', item['code']),
                    'signal_name': p.name,
                    'signal_type': p.signal_type.value,
                    'last_price': round(latest_price, 2),
                    'phase_label': phase_info.get('label', ''),
                    'detected_at': str(df_with.index[-1])[:10]
                })
        except:
            continue

    # 按检测时间倒序
    alerts.sort(key=lambda x: x['detected_at'], reverse=True)
    return jsonify({'alerts': alerts, 'total': len(alerts)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)