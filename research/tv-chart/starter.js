/* 最小骨架：兩層 pane 的互動 K 線圖
 * 刻意只做骨架、不做完整五格——完整版看 SKILL.md 末尾指的實作。
 * 這裡示範的是每次都會用到、而且每次都容易踩錯的四件事：
 *   ① 分段畫線（空白點不會斷線）
 *   ② setStretchFactor 配 pane 高度
 *   ③ 只有點沒有線的序列（畫零軸標記用）
 *   ④ 固定高度的十字游標讀數列（不跳版）
 *
 * 資料採緊湊編碼，欄位定義：
 *   dates : ["2026-01-02", ...]                    時間軸，其餘欄位都用索引指向它
 *   bars  : [[i, o, h, l, c, colorIdx], ...]
 *   segs  : [{t: 1|-1, p: [[i, value], ...]}, ...] 已依狀態切好的線段
 *   vol   : [[i, value, 0|1], ...]                 0=紅 1=綠
 *   marks : [i, ...]                               畫在零軸上的點
 */
(function () {
  'use strict';
  var LC = window.LightweightCharts;

  var C = {
    panel: '#0a1222', grid: '#143352', text: '#cfe6ff', muted: '#5f80a6',
    up: '#ff5277', down: '#2ee6a8',        // 台股紅漲綠跌，不可調動
    line1: '#b39dff', line2: '#ffd54f',    // 疊圖刻意避開紅綠，免得跟漲跌混淆
    cyan: '#25e6ff'
  };
  var RATIO = [3.2, 1.0];                  // 主圖 : 副圖

  function render(host, d) {
    // starter.css 的規則全掛在 .mofi-chart 底下，這裡自己補上，
    // 免得照文件抄完卻完全沒有樣式（讀數列高度沒寫死就會跳版）
    host.classList.add('mofi-chart');
    var D = d.dates, T = function (i) { return D[i]; };
    host.innerHTML =
      '<div class="tc-readout"><div class="tc-ro-line">移到圖上看數值</div>'
      + '<div class="tc-ro-line"></div></div><div class="tc-canvas"></div>';
    var readout = host.querySelector('.tc-readout');
    var wrap = host.querySelector('.tc-canvas');
    var mob = window.innerWidth < 768;

    var chart = LC.createChart(wrap, {
      width: wrap.clientWidth, height: mob ? 460 : 600,
      layout: {
        background: { color: C.panel }, textColor: C.text,
        fontFamily: "'Fira Code','Microsoft JhengHei',ui-monospace,monospace",
        attributionLogo: false,
        panes: { separatorColor: C.grid, enableResize: !mob }
      },
      grid: { vertLines: { color: C.grid, style: 1 }, horzLines: { color: C.grid, style: 1 } },
      rightPriceScale: { borderColor: C.grid },
      timeScale: {
        borderColor: C.grid, barSpacing: mob ? 3 : 6,
        // 預設會吐出「3日」「20日」這種怪標記，一定要自訂
        tickMarkFormatter: function (t, type) {
          var p = String(t).split('-');
          if (type === LC.TickMarkType.Year) return p[0] + '年';
          if (type === LC.TickMarkType.Month) return Number(p[1]) + '月';
          return Number(p[1]) + '/' + Number(p[2]);
        }
      },
      crosshair: { mode: LC.CrosshairMode.Normal,
                   vertLine: { color: C.cyan, style: 2 }, horzLine: { color: C.cyan, style: 2 } },
      handleScroll: { vertTouchDrag: false }   // 手機垂直拖曳留給頁面捲動
    });

    // ---- pane 0：K 線 ----
    var candle = chart.addSeries(LC.CandlestickSeries, { borderVisible: true }, 0);
    var PAL = [C.up, C.down, '#8f2740', '#1a7a5c'];   // 0/1 陽線亮色、2/3 陰線暗色
    candle.setData(d.bars.map(function (b) {
      var c = PAL[b[5]], yang = b[5] < 2;
      return { time: T(b[0]), open: b[1], high: b[2], low: b[3], close: b[4],
               // 陰線填背景色做成空心
               color: yang ? c : C.panel, borderColor: c, wickColor: c };
    }));

    // ⛔ 坑①：每段連續狀態各自一條 series。
    // 若把同狀態的散點丟進同一條線、缺的填空白點，Lightweight Charts 不會斷線，
    // 會把它們連成一條穿越全圖的假趨勢線——而且看起來很像真的。
    (d.segs || []).forEach(function (seg, i, arr) {
      var s = chart.addSeries(LC.LineSeries, {
        color: seg.t === 1 ? C.line1 : C.line2, lineWidth: 2,
        priceLineVisible: false, lastValueVisible: i === arr.length - 1,
        crosshairMarkerVisible: false
      }, 0);
      s.setData(seg.p.map(function (p) { return { time: T(p[0]), value: p[1] }; }));
    });

    // ---- pane 1：成交量 ----
    var vol = chart.addSeries(LC.HistogramSeries, {
      priceFormat: { type: 'volume' }, priceLineVisible: false, lastValueVisible: false
    }, 1);
    vol.setData(d.vol.map(function (v) {
      return { time: T(v[0]), value: v[1], color: v[2] === 0 ? C.up : C.down };
    }));

    // ⛔ 坑③：要在零軸上畫一排標記，用「只有點、沒有線」的 LineSeries。
    // markers 的 y 只能貼著 bar，無法指定固定高度。
    if ((d.marks || []).length) {
      var dots = chart.addSeries(LC.LineSeries, {
        color: C.cyan, lineVisible: false,
        pointMarkersVisible: true, pointMarkersRadius: 3,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false
      }, 1);
      dots.setData(d.marks.map(function (i) { return { time: T(i), value: 0 }; }));
    }

    // ⛔ 坑②：用 setStretchFactor 配比例。setHeight 是絕對像素，
    // 改一個會連鎖擠壓其他 pane，比例會跑掉。
    chart.panes().forEach(function (p, i) {
      if (i < RATIO.length) p.setStretchFactor(RATIO[i]);
    });

    // ---- 十字游標讀數 ----
    var idxOf = {}; D.forEach(function (t, i) { idxOf[t] = i; });
    var barAt = {}; d.bars.forEach(function (b) { barAt[b[0]] = b; });
    var volAt = {}; d.vol.forEach(function (v) { volAt[v[0]] = v[1]; });
    chart.subscribeCrosshairMove(function (p) {
      var i = p && p.time !== undefined ? idxOf[p.time] : undefined;
      var L = host.querySelectorAll('.tc-ro-line');
      if (i === undefined || !barAt[i]) { L[0].textContent = '移到圖上看數值'; L[1].textContent = ''; return; }
      var b = barAt[i], chg = ((b[4] - b[1]) / b[1] * 100).toFixed(2);
      L[0].textContent = D[i] + '　開 ' + b[1] + '　高 ' + b[2] + '　低 ' + b[3] + '　收 ' + b[4];
      L[1].textContent = (chg >= 0 ? '+' : '') + chg + '%　量 ' + (volAt[i] || '—');
    });

    // ⛔ 坑⑦：觀察外層 host，不要觀察 wrap。
    // applyOptions({height}) 會改變 wrap 高度、再觸發 observer，兩者會打成無限迴圈。
    function layout() {
      chart.applyOptions({ width: wrap.clientWidth,
                           height: window.innerWidth < 768 ? 460 : 600 });
    }
    if (window.ResizeObserver) new ResizeObserver(layout).observe(host);
    else window.addEventListener('resize', layout);

    chart.timeScale().fitContent();
    return chart;
  }

  window.MofiChartStarter = { render: render };
})();
