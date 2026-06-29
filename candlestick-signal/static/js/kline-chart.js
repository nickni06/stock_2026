/**
 * Canvas K线图组件
 * 支持红绿蜡烛体、信号三角标注、鼠标悬停交互
 */
class KlineChart {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.canvas = this.container.querySelector('canvas');
    this.tooltip = this.container.querySelector('.chart-tooltip');
    this.ctx = this.canvas.getContext('2d');
    this.data = [];
    this.signals = [];
    this.options = Object.assign({
      height: 350,
      padding: { top: 30, right: 30, bottom: 50, left: 60 },
      candleWidth: 6,
      candleGap: 1,
      maxCandles: 200,
      bullColor: '#ef4444',
      bearColor: '#22c55e',
      signalBuyColor: '#ef4444',
      signalSellColor: '#22c55e',
      bgColor: '#0d1117',
      gridColor: '#21262d',
      textColor: '#8b949e',
      wickColor: '#8b949e'
    }, options);

    this.init();
  }

  init() {
    this.resize();
    this.bindEvents();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = rect.width - 10;
    const height = this.options.height;

    this.width = width;
    this.height = height;
    this.canvas.style.width = width + 'px';
    this.canvas.style.height = height + 'px';
    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.scale(dpr, dpr);
    this.dpr = dpr;

    if (this.data.length > 0) {
      this.render();
    }
  }

  setData(data, signals = []) {
    this.data = data;
    this.signals = signals;
    this.render();
  }

  getVisibleData() {
    if (this.data.length <= this.options.maxCandles) {
      return this.data;
    }
    return this.data.slice(-this.options.maxCandles);
  }

  getChartArea() {
    const p = this.options.padding;
    return {
      x: p.left,
      y: p.top,
      w: this.width - p.left - p.right,
      h: this.height - p.top - p.bottom
    };
  }

  render() {
    const ctx = this.ctx;
    const area = this.getChartArea();
    const visible = this.getVisibleData();

    ctx.clearRect(0, 0, this.width, this.height);

    if (visible.length < 2) return;

    // 计算价格范围
    let minPrice = Infinity, maxPrice = -Infinity;
    visible.forEach(d => {
      if (d.high > maxPrice) maxPrice = d.high;
      if (d.low < minPrice) minPrice = d.low;
    });
    const priceRange = maxPrice - minPrice;
    const pricePadding = priceRange * 0.05;
    minPrice -= pricePadding;
    maxPrice += pricePadding;

    this.priceRange = { min: minPrice, max: maxPrice };
    this.visibleData = visible;
    this.chartArea = area;

    const candleW = (area.w / visible.length) * 0.7;
    const candleG = (area.w / visible.length) * 0.3;
    this.candleW = Math.max(candleW, 1);
    this.candleG = Math.max(candleG, 0.5);

    // 绘制网格
    this.drawGrid();

    // 绘制K线
    visible.forEach((d, i) => {
      this.drawCandle(d, i, visible.length);
    });

    // 绘制信号标记
    this.drawSignals();

    // 绘制Y轴标签
    this.drawYAxis();

    // 绘制X轴标签
    this.drawXAxis();
  }

  drawGrid() {
    const ctx = this.ctx;
    const area = this.getChartArea();
    ctx.strokeStyle = this.options.gridColor;
    ctx.lineWidth = 0.5;

    // 水平网格线
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = area.y + (area.h / gridLines) * i;
      ctx.beginPath();
      ctx.moveTo(area.x, y);
      ctx.lineTo(area.x + area.w, y);
      ctx.stroke();
    }
  }

  drawCandle(d, idx, total) {
    const ctx = this.ctx;
    const area = this.getChartArea();
    const { min, max } = this.priceRange;
    const priceToY = (price) => area.y + area.h * (1 - (price - min) / (max - min));

    const x = area.x + (area.w / total) * (idx + 0.5);
    const oy = priceToY(d.open);
    const cy = priceToY(d.close);
    const hy = priceToY(d.high);
    const ly = priceToY(d.low);

    const isBull = d.close >= d.open;
    const color = isBull ? this.options.bullColor : this.options.bearColor;

    // 影线
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, hy);
    ctx.lineTo(x, Math.max(oy, cy));
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, Math.min(oy, cy));
    ctx.lineTo(x, ly);
    ctx.stroke();

    // 实体
    const bodyH = Math.max(Math.abs(cy - oy), 1);
    const bodyY = Math.min(oy, cy);
    ctx.fillStyle = isBull ? this.options.bullColor : this.options.bearColor;
    ctx.fillRect(x - this.candleW / 2, bodyY, this.candleW, bodyH);

    // 存储位置信息用于悬停检测
    d._x = x;
    d._w = this.candleW + this.candleG;
    d._oy = oy;
    d._cy = cy;
    d._hy = hy;
    d._ly = ly;
  }

  drawSignals() {
    const ctx = this.ctx;
    const visible = this.visibleData;
    const total = visible.length;
    const area = this.getChartArea();
    const { min, max } = this.priceRange;

    // 构建信号日期索引
    const signalMap = {};
    this.signals.forEach(s => {
      signalMap[s.date] = s;
    });

    visible.forEach((d, i) => {
      const sig = signalMap[d.date];
      if (!sig) return;

      const x = area.x + (area.w / total) * (i + 0.5);
      const priceToY = (price) => area.y + area.h * (1 - (price - min) / (max - min));
      const y = priceToY(d.high) - 12;

      const isBuy = sig.signal_type === 'bullish';
      ctx.fillStyle = isBuy ? this.options.signalBuyColor : this.options.signalSellColor;

      // 绘制三角
      ctx.beginPath();
      if (isBuy) {
        ctx.moveTo(x, y);
        ctx.lineTo(x - 6, y - 10);
        ctx.lineTo(x + 6, y - 10);
      } else {
        ctx.moveTo(x, y - 10);
        ctx.lineTo(x - 6, y);
        ctx.lineTo(x + 6, y);
      }
      ctx.closePath();
      ctx.fill();

      d._signal = sig;
      d._signalY = y - 10;
    });
  }

  drawYAxis() {
    const ctx = this.ctx;
    const area = this.getChartArea();
    const { min, max } = this.priceRange;
    const gridLines = 5;

    ctx.fillStyle = this.options.textColor;
    ctx.font = '11px ' + getComputedStyle(document.body).fontFamily;
    ctx.textAlign = 'right';

    for (let i = 0; i <= gridLines; i++) {
      const y = area.y + (area.h / gridLines) * i;
      const price = max - (max - min) / gridLines * i;
      ctx.fillText(price.toFixed(2), area.x - 6, y + 4);
    }
  }

  drawXAxis() {
    const ctx = this.ctx;
    const area = this.getChartArea();
    const visible = this.visibleData;
    const total = visible.length;

    ctx.fillStyle = this.options.textColor;
    ctx.font = '11px ' + getComputedStyle(document.body).fontFamily;
    ctx.textAlign = 'center';

    const step = Math.max(1, Math.floor(total / 8));
    for (let i = 0; i < total; i += step) {
      const x = area.x + (area.w / total) * (i + 0.5);
      const date = visible[i].date.substring(5); // MM-DD
      ctx.fillText(date, x, area.y + area.h + 18);
    }
  }

  bindEvents() {
    this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    this.canvas.addEventListener('mouseleave', () => {
      this.tooltip.classList.remove('show');
    });
  }

  handleMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const visible = this.visibleData;

    if (!visible) return;

    let found = null;
    for (let i = visible.length - 1; i >= 0; i--) {
      const d = visible[i];
      if (d._x && Math.abs(mx - d._x) < d._w / 2 + 2) {
        found = d;
        break;
      }
    }

    if (found) {
      const change = found.close - found.open;
      const changePct = found.open > 0 ? (change / found.open * 100).toFixed(2) : 0;
      const sign = change >= 0 ? '+' : '';

      let html = `<div><b>${found.date}</b></div>`;
      html += `<div>开: ${found.open} 高: ${found.high} 低: ${found.low} 收: ${found.close}</div>`;
      html += `<div>涨跌: ${sign}${change.toFixed(2)} (${sign}${changePct}%)</div>`;

      if (found._signal) {
        html += `<div style="color:${found._signal.signal_type === 'bullish' ? '#ef4444' : '#22c55e'};margin-top:4px">
          信号: ${found._signal.signal_name}
        </div>`;
      }

      this.tooltip.innerHTML = html;
      this.tooltip.classList.add('show');

      // 定位tooltip
      const containerRect = this.container.getBoundingClientRect();
      let tx = mx + 15;
      let ty = my - 10;

      if (tx + 200 > containerRect.width) tx = mx - 200;
      if (ty < 0) ty = 5;

      this.tooltip.style.left = tx + 'px';
      this.tooltip.style.top = ty + 'px';
    } else {
      this.tooltip.classList.remove('show');
    }
  }
}

/**
 * 收益曲线图表
 */
class EquityChart {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.canvas = this.container.querySelector('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.options = Object.assign({
      height: 250,
      padding: { top: 20, right: 20, bottom: 40, left: 60 },
      strategyColor: '#58a6ff',
      benchmarkColor: '#8b949e',
      bgColor: '#0d1117',
      gridColor: '#21262d',
      textColor: '#8b949e'
    }, options);

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = rect.width - 10;
    const height = this.options.height;

    this.width = width;
    this.height = height;
    this.canvas.style.width = width + 'px';
    this.canvas.style.height = height + 'px';
    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.scale(dpr, dpr);

    if (this.strategyData) {
      this.render();
    }
  }

  setData(strategyData, benchmarkData) {
    this.strategyData = strategyData;
    this.benchmarkData = benchmarkData;
    this.render();
  }

  getChartArea() {
    const p = this.options.padding;
    return {
      x: p.left,
      y: p.top,
      w: this.width - p.left - p.right,
      h: this.height - p.top - p.bottom
    };
  }

  render() {
    const ctx = this.ctx;
    const area = this.getChartArea();

    ctx.clearRect(0, 0, this.width, this.height);

    if (!this.strategyData || this.strategyData.length < 2) return;

    // 合并数据计算范围
    const allValues = [];
    this.strategyData.forEach(d => allValues.push(d.value));
    this.benchmarkData.forEach(d => allValues.push(d.value));

    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues);
    const range = maxVal - minVal || 1;
    const valMin = minVal - range * 0.05;
    const valMax = maxVal + range * 0.05;

    const valToY = (v) => area.y + area.h * (1 - (v - valMin) / (valMax - valMin));

    // 网格
    ctx.strokeStyle = this.options.gridColor;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 5; i++) {
      const y = area.y + (area.h / 5) * i;
      ctx.beginPath();
      ctx.moveTo(area.x, y);
      ctx.lineTo(area.x + area.w, y);
      ctx.stroke();
    }

    // 绘制基准曲线
    this.drawLine(ctx, this.benchmarkData, area, valMin, valMax, this.options.benchmarkColor, true);

    // 绘制策略曲线
    this.drawLine(ctx, this.strategyData, area, valMin, valMax, this.options.strategyColor, false);

    // Y轴标签
    ctx.fillStyle = this.options.textColor;
    ctx.font = '10px ' + getComputedStyle(document.body).fontFamily;
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
      const y = area.y + (area.h / 5) * i;
      const v = valMax - (valMax - valMin) / 5 * i;
      ctx.fillText(v.toFixed(2), area.x - 6, y + 4);
    }

    // 图例
    const legendY = area.y + area.h + 25;
    ctx.fillStyle = this.options.strategyColor;
    ctx.fillRect(area.x, legendY - 8, 14, 8);
    ctx.fillStyle = this.options.textColor;
    ctx.textAlign = 'left';
    ctx.fillText('策略净值', area.x + 18, legendY);

    ctx.fillStyle = this.options.benchmarkColor;
    ctx.fillRect(area.x + 90, legendY - 8, 14, 8);
    ctx.fillStyle = this.options.textColor;
    ctx.fillText('买入持有', area.x + 108, legendY);
  }

  drawLine(ctx, data, area, minVal, maxVal, color, dashed) {
    if (!data || data.length < 2) return;

    const valToY = (v) => area.y + area.h * (1 - (v - minVal) / (maxVal - minVal));

    ctx.strokeStyle = color;
    ctx.lineWidth = dashed ? 1.5 : 2;
    if (dashed) ctx.setLineDash([5, 5]);
    else ctx.setLineDash([]);

    ctx.beginPath();
    const step = area.w / (data.length - 1);
    data.forEach((d, i) => {
      const x = area.x + step * i;
      const y = valToY(d.value);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }
}