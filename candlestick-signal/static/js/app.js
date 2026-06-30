/**
 * 蜡烛图信号系统 - 前端主应用
 */
class CandlestickApp {
  constructor() {
    this.currentPage = 'optimize';
    this.apiBase = '/api';
    this.init();
  }

  init() {
    this.bindNavigation();
    this.initKlineChart();
    this.bindEvents();
    this.switchPage('optimize');
  }

  bindNavigation() {
    // 侧边栏导航
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', () => {
        const page = item.dataset.page;
        this.switchPage(page);
      });
    });

    // 底部导航
    document.querySelectorAll('.bottom-nav-item').forEach(item => {
      item.addEventListener('click', () => {
        const page = item.dataset.page;
        this.switchPage(page);
      });
    });
  }

  switchPage(pageId) {
    // 更新导航激活状态
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.page === pageId);
    });
    document.querySelectorAll('.bottom-nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.page === pageId);
    });

    // 显示对应页面
    document.querySelectorAll('.page').forEach(page => {
      page.classList.toggle('active', page.id === pageId);
    });

    this.currentPage = pageId;
  }

  initKlineChart() {
    if (document.getElementById('kline-chart-container')) {
      this.klineChart = new KlineChart('kline-chart-container');
    }
    if (document.getElementById('equity-chart-container')) {
      this.equityChart = new EquityChart('equity-chart-container');
    }
    if (document.getElementById('backtest-kline-chart-container')) {
      this.backtestKlineChart = new KlineChart('backtest-kline-chart-container');
    }
  }

  bindEvents() {
    // 最优信号挖掘 - 搜索标的
    this.bindSearch('optimize-symbol', 'optimize-search-results', (result) => {
      document.getElementById('optimize-symbol').value = `${result.name} (${result.code})`;
      this.selectedSymbol = result;
    });

    // 信号回测 - 搜索标的
    this.bindSearch('backtest-symbol', 'backtest-search-results', (result) => {
      document.getElementById('backtest-symbol').value = `${result.name} (${result.code})`;
      this.selectedBacktestSymbol = result;
    });

    // 信号回测 - 加载信号库
    this.loadPatternChips();

    // 最优信号挖掘表单提交
    document.getElementById('optimize-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.runOptimize();
    });

    // 信号回测表单提交
    document.getElementById('backtest-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.runBacktest();
    });

    // 全量扫描
    document.getElementById('scan-btn').addEventListener('click', () => {
      this.runScan();
    });

    // 关注列表
    document.getElementById('add-to-watchlist-btn').addEventListener('click', () => {
      this.addToWatchlist();
    });

    // 刷新提醒
    document.getElementById('refresh-alerts-btn').addEventListener('click', () => {
      this.loadAlerts();
    });

    // 加载信号库
    this.loadPatternLibrary();

    // 加载关注列表
    this.loadWatchlist();

    // 加载提醒
    this.loadAlerts();
  }

  bindSearch(inputId, resultsId, onSelect) {
    const input = document.getElementById(inputId);
    const resultsDiv = document.getElementById(resultsId);
    let timer = null;

    input.addEventListener('input', () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) {
        resultsDiv.innerHTML = '';
        resultsDiv.classList.remove('show');
        return;
      }

      timer = setTimeout(async () => {
        const result = await this.apiPost('/symbols/search', q);
        if (!result || !result.results || result.results.length === 0) {
          resultsDiv.innerHTML = '<div style="padding:0.7rem;color:#8b949e;text-align:center;font-size:0.8rem">未找到匹配结果</div>';
          resultsDiv.classList.add('show');
          return;
        }

        resultsDiv.innerHTML = result.results.map(r => {
          return `<div class="search-result-item" data-code="${r.code}" data-type="${r.type}" data-name="${r.name}">
            <span class="sym-name">${r.name}</span>
            <span class="sym-code"> ${r.code}</span>
          </div>`;
        }).join('');
        resultsDiv.classList.add('show');

        resultsDiv.querySelectorAll('.search-result-item').forEach(item => {
          item.addEventListener('click', () => {
            const code = item.dataset.code;
            const type = item.dataset.type;
            const name = item.dataset.name;
            onSelect({code, name, type});
            resultsDiv.classList.remove('show');
          });
        });
      }, 300);
    });

    // 点击外部关闭
    document.addEventListener('click', (e) => {
      if (!resultsDiv.contains(e.target) && e.target !== input) {
        resultsDiv.classList.remove('show');
      }
    });
  }

  async apiGet(path) {
    try {
      const res = await fetch(`${this.apiBase}${path}`);
      return await res.json();
    } catch (e) {
      console.error(e);
      this.showError('网络错误');
      return null;
    }
  }

  async apiPost(path, data) {
    try {
      // 字符串作为 form-urlencoded 发送（搜索请求）
      // 对象作为 JSON 发送（其他 API）
      const isForm = typeof data === 'string';
      const opts = {
        method: 'POST',
        body: isForm ? new URLSearchParams({ q: data }) : JSON.stringify(data)
      };
      if (!isForm) {
        opts.headers = { 'Content-Type': 'application/json' };
      }
      const res = await fetch(`${this.apiBase}${path}`, opts);
      return await res.json();
    } catch (e) {
      console.error(e);
      this.showError('网络错误');
      return null;
    }
  }

  showLoading(containerId) {
    document.getElementById(containerId).querySelector('.loading').classList.add('show');
  }

  hideLoading(containerId) {
    document.getElementById(containerId).querySelector('.loading').classList.remove('show');
  }

  showError(msg) {
    alert(msg);
  }

  // ==================== 加载信号芯片 ====================
  async loadPatternChips() {
    const result = await this.apiGet('/patterns');
    if (!result || !result.patterns) return;

    const container = document.getElementById('pattern-chips');
    container.innerHTML = '';
    result.patterns.forEach(p => {
      const chip = document.createElement('div');
      chip.className = 'chip';
      chip.textContent = p.name;
      chip.dataset.code = p.code;
      chip.addEventListener('click', () => {
        chip.classList.toggle('selected');
      });
      container.appendChild(chip);
    });
  }

  // ==================== 最优信号挖掘 ====================
  async runOptimize() {
    if (!this.selectedSymbol) {
      this.showError('请先选择标的');
      return;
    }

    this.showLoading('optimize-loading');
    const topN = parseInt(document.getElementById('optimize-topn').value) || 5;
    const startDate = document.getElementById('optimize-start').value;
    const endDate = document.getElementById('optimize-end').value;

    let url = `/optimize?symbol=${encodeURIComponent(this.selectedSymbol.code)}` +
              `&type=${encodeURIComponent(this.selectedSymbol.type)}&top_n=${topN}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    const result = await this.apiGet(url);
    this.hideLoading('optimize-loading');

    if (!result || result.error) {
      this.showError(result?.error || '挖掘失败');
      return;
    }

    this.renderOptimizeResult(result);
  }

  renderOptimizeResult(result) {
    // 显示市场阶段信息
    const container = document.getElementById('optimize-result');
    container.style.display = 'block';

    // 市场阶段卡片
    const p = result.phase;
    document.getElementById('phase-label').textContent = p.label;
    document.getElementById('phase-ma20').textContent = p.ma20;
    document.getElementById('phase-ma60').textContent = p.ma60;
    document.getElementById('phase-atrpct').textContent = p.atr_pct + '%';

    // 渲染最优买点表格
    const buyData = result.phase_matched.sample_count >= 5
      ? result.phase_matched.buy_signals
      : result.all_history.buy_signals;

    const sellData = result.phase_matched.sample_count >= 5
      ? result.phase_matched.sell_signals
      : result.all_history.sell_signals;

    const sampleUsed = result.phase_matched.sample_count >= 5
      ? `阶段匹配匹配到 ${result.phase_matched.sample_count} 个K线样本`
      : '阶段匹配样本不足(<5)，使用全量历史数据';

    document.getElementById('optimize-note').textContent = sampleUsed;
    document.getElementById('optimize-note').style.display = 'block';

    this.renderSignalTable('optimize-buy-table', buyData);
    this.renderSignalTable('optimize-sell-table', sellData);

    // 获取最近K线并绘制
    this.loadKlineAndRender(this.selectedSymbol.code, this.selectedSymbol.type, 'kline-chart-container', this.klineChart);
  }

  renderSignalTable(tableId, signals) {
    const tbody = document.getElementById(tableId);
    if (!signals || signals.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#8b949e">无数据</td></tr>';
      return;
    }

    tbody.innerHTML = signals.map(s => {
      const pf = s.profit_factor === Infinity || s.profit_factor > 999 ? '∞' : s.profit_factor.toFixed(2);
      return `
        <tr class="trade-row" data-signal-code="${s.signal_code}">
          <td><b>${s.signal_name}</b></td>
          <td>${s.total_trades}</td>
          <td>${s.win_rate}%</td>
          <td>${s.avg_return}%</td>
          <td>${pf}</td>
          <td>${s.max_drawdown}%</td>
          <td><b>${s.score}</b></td>
        </tr>
        <tr class="detail-row" data-detail-row="${s.signal_code}">
          <td colspan="8">
            <div class="table-wrap">
              <table class="detail-table">
                <thead>
                  <tr><th>信号日期</th><th>买入价</th><th>1日收益</th><th>3日收益</th><th>5日收益</th><th>10日收益</th><th>盈亏</th></tr>
                </thead>
                <tbody>
                  ${(s.trades || []).slice(0, 20).map(t => {
                    const tagCls = t.is_win ? 'tag-win' : 'tag-loss';
                    const tagText = t.is_win ? '盈利' : '亏损';
                    return `<tr>
                      <td>${t.signal_date}</td>
                      <td>${t.buy_price}</td>
                      <td>${this.formatPct(t.return_1d)}</td>
                      <td>${this.formatPct(t.return_3d)}</td>
                      <td>${this.formatPct(t.return_5d)}</td>
                      <td>${this.formatPct(t.return_10d)}</td>
                      <td><span class="tag ${tagCls}">${tagText} (${t.return_pct}%)</span></td>
                    </tr>`;
                  }).join('')}
                </tbody>
              </table>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // 绑定展开/收起事件
    tbody.querySelectorAll('.trade-row').forEach(row => {
      row.addEventListener('click', () => {
        const code = row.dataset.signalCode;
        const detailRow = tbody.querySelector(`.detail-row[data-detail-row="${code}"]`);
        if (detailRow) {
          detailRow.classList.toggle('show');
          row.classList.toggle('expanded');
        }
      });
    });
  }

  formatPct(v) {
    if (v == null || isNaN(v)) return '-';
    const sign = v > 0 ? '+' : '';
    return `${sign}${v}%`;
  }

  // ==================== 加载K线 ====================
  async loadKlineAndRender(symbol, symbolType, containerId, chartInstance, days = 120) {
    const result = await this.apiGet(`/kline?symbol=${encodeURIComponent(symbol)}&type=${encodeURIComponent(symbolType || 'stock')}&days=${days}`);
    if (!result || !result.kline) return;

    // 检测信号位置
    const signalPositions = this.detectSignalsInKline(result.kline);
    chartInstance.setData(result.kline, signalPositions);
  }

  detectSignalsInKline(kline) {
    // 这里后端已经检测过信号，在回测结果中返回，所以返回空
    return [];
  }

  // ==================== 信号回测 ====================
  async runBacktest() {
    if (!this.selectedBacktestSymbol) {
      this.showError('请先选择标的');
      return;
    }

    this.showLoading('backtest-loading');

    const startDate = document.getElementById('backtest-start').value;
    const endDate = document.getElementById('backtest-end').value;
    const holdDays = parseInt(document.getElementById('backtest-hold').value) || 5;

    // 获取选中的信号
    const selectedPatterns = [];
    document.querySelectorAll('#pattern-chips .chip.selected').forEach(el => {
      selectedPatterns.push(el.dataset.code);
    });

    const body = {
      symbol: this.selectedBacktestSymbol.code,
      type: this.selectedBacktestSymbol.type,
      patterns: selectedPatterns,
      hold_days: holdDays
    };
    if (startDate) body.start_date = startDate;
    if (endDate) body.end_date = endDate;

    const result = await this.apiPost('/backtest', body);
    this.hideLoading('backtest-loading');

    if (!result || result.error) {
      this.showError(result?.error || '回测失败');
      return;
    }

    this.renderBacktestResult(result);
  }

  renderBacktestResult(result) {
    const container = document.getElementById('backtest-result');
    container.style.display = 'block';

    // 渲染统计卡片
    const st = result.statistics;
    document.getElementById('bt-total-trades').textContent = st.total_trades;
    document.getElementById('bt-win-rate').textContent = st.win_rate + '%';
    document.getElementById('bt-avg-return').textContent = st.avg_return + '%';
    document.getElementById('bt-profit-factor').textContent = st.profit_factor;
    document.getElementById('bt-max-dd').textContent = st.max_drawdown + '%';
    document.getElementById('bt-total-return').textContent = st.total_return + '%';

    // 绘制K线并标注信号
    this.backtestKlineChart.setData(result.kline, result.signal_positions);

    // 绘制收益曲线
    this.equityChart.setData(result.equity_curve, result.benchmark_curve);

    // 渲染交易明细表格
    this.renderTradesTable('backtest-trades-table', result.trades);
  }

  renderTradesTable(tableId, trades) {
    const tbody = document.getElementById(tableId);
    if (!trades || trades.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#8b949e">无交易</td></tr>';
      return;
    }

    tbody.innerHTML = trades.map(t => {
      const tagCls = t.is_win ? 'tag-win' : 'tag-loss';
      const tagText = t.is_win ? '盈利' : '亏损';
      return `
        <tr>
          <td>${t.signal_name}</td>
          <td>${t.signal_date}</td>
          <td>${t.buy_price}</td>
          <td>${this.formatPct(t.return_3d)}</td>
          <td>${this.formatPct(t.return_5d)}</td>
          <td>${this.formatPct(t.return_10d)}</td>
          <td><span class="tag ${tagCls}">${tagText}</span></td>
        </tr>
      `;
    }).join('');
  }

  // ==================== 信号库 ====================
  async loadPatternLibrary() {
    this.renderPatternLibrary('all');
    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('selected'));
        tab.classList.add('selected');
        this.renderPatternLibrary(tab.dataset.type);
      });
    });
  }

  async renderPatternLibrary(filterType) {
    const result = await this.apiGet(`/patterns${filterType !== 'all' ? `?type=${filterType}` : ''}`);
    if (!result || !result.patterns) return;

    const tbody = document.getElementById('patterns-table-body');
    tbody.innerHTML = result.patterns.map(p => {
      return `
        <tr>
          <td><b>${p.name}</b></td>
          <td><span class="tag tag-${p.type}">${this.typeLabel(p.type)}</span></td>
          <td>${p.description}</td>
          <td>${p.rule_description}</td>
        </tr>
      `;
    }).join('');
  }

  typeLabel(type) {
    const map = {
      'bullish': '买入看涨',
      'bearish': '卖出看跌',
      'reversal': '反转',
      'continuation': '突破延续'
    };
    return map[type] || type;
  }

  // ==================== 关注列表 ====================
  async loadWatchlist() {
    const result = await this.apiGet('/watchlist');
    const container = document.getElementById('watchlist-container');
    if (!result || !result.watchlist || result.watchlist.length === 0) {
      container.innerHTML = '<div class="empty-state"><div class="icon">📝</div><p>关注列表为空，通过搜索添加标的</p></div>';
      return;
    }

    container.innerHTML = result.watchlist.map(item => {
      const changeSign = item.change_pct > 0 ? '+' : '';
      const changeCls = item.change_pct > 0 ? 'red' : 'green';
      return `
        <div class="watchlist-item">
          <div class="wl-info">
            <div style="display:flex;align-items:center;gap:0.5rem">
              <span class="wl-name">${item.name}</span>
              <span class="wl-code">${item.code}</span>
            </div>
            <div class="wl-price">${item.last_price} <span class="wl-change ${changeCls}">${changeSign}${item.change_pct}%</span></div>
            <div class="wl-signals" id="wl-signals-${item.code}"></div>
          </div>
          <div>
            <button class="btn btn-sm btn-danger" onclick="app.removeFromWatchlist('${item.code}')">删除</button>
          </div>
        </div>
      `;
    }).join('');

    // 加载每个标的最近信号
    result.watchlist.forEach(async item => {
      const recent = await this.apiGet(`/kline?symbol=${item.code}&type=${item.type || 'stock'}&days=30`);
      if (!recent || !recent.kline) return;

      // 检测信号
      // 在前端简单获取后端扫描
      const scanResult = await this.apiGet('/scan');
      if (scanResult && scanResult.results) {
        const signals = scanResult.results.filter(r => r.symbol_code === item.code);
        if (signals.length > 0) {
          const container = document.getElementById(`wl-signals-${item.code}`);
          container.textContent = `最近信号: ${signals.map(s => s.signal_name).join(', ')}`;
        }
      }
    });
  }

  async addToWatchlist() {
    if (!this.selectedSymbol) {
      this.showError('请先搜索并选择一个标的');
      return;
    }

    const result = await this.apiPost('/watchlist/add', this.selectedSymbol);
    if (result && result.success) {
      alert('添加成功');
      this.loadWatchlist();
    } else {
      this.showError('添加失败');
    }
  }

  async removeFromWatchlist(code) {
    if (!confirm('确认删除？')) return;
    const result = await this.apiPost('/watchlist/remove', { code });
    if (result && result.success) {
      this.loadWatchlist();
    } else {
      this.showError('删除失败');
    }
  }

  // ==================== 全量扫描 ====================
  async runScan() {
    this.showLoading('scan-loading');
    const typeFilter = document.querySelector('input[name="scan-type-filter"]:checked').value;
    const phaseOnly = document.getElementById('scan-phase-only').checked;

    let url = '/scan';
    const params = [];
    if (typeFilter !== 'all') params.push(`signal_type=${typeFilter}`);
    if (phaseOnly) params.push(`phase_only=true`);

    if (params.length > 0) url += '?' + params.join('&');

    const result = await this.apiGet(url);
    this.hideLoading('scan-loading');

    const tbody = document.getElementById('scan-result-table');
    if (!result || !result.results || result.results.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#8b949e">当前没有发现信号</td></tr>';
      return;
    }

    tbody.innerHTML = result.results.map(r => {
      const badge = r.phase_matched ? '✓' : '✗';
      return `
        <tr>
          <td><b>${r.symbol_name}</b> <span style="color:#8b949e">${r.symbol_code}</span></td>
          <td><span class="tag tag-${r.signal_type}">${r.signal_name}</span></td>
          <td>${r.signal_date}</td>
          <td>${r.last_price}</td>
          <td>${r.phase_label || '-'}</td>
          <td>${badge}</td>
        </tr>
      `;
    }).join('');
  }

  // ==================== 信号提醒 ====================
  async loadAlerts() {
    const container = document.getElementById('alerts-container');
    const result = await this.apiGet('/alerts');
    if (!result || !result.alerts || result.alerts.length === 0) {
      container.innerHTML = '<div style="text-align:center;padding:2rem;color:#8b949e">当前无信号提醒</div>';
      return;
    }

    container.innerHTML = result.alerts.map(a => {
      const typeCls = a.signal_type === 'bullish' ? 'tag-bullish' : 'tag-bearish';
      return `
        <div class="alert-banner">
          <div>
            <span class="tag ${typeCls}">${a.signal_name}</span>
            <b style="margin:0 0.5rem">${a.symbol_name} (${a.symbol_code})</b>
            价格: ${a.last_price} | 阶段: ${a.phase_label || '未知'}
          </div>
          <div class="alert-close" onclick="this.parentElement.remove()">✕</div>
        </div>
      `;
    }).join('');
  }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new CandlestickApp();
});
