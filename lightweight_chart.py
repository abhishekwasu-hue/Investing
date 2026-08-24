"""
TradingView चा अधिकृत 'lightweight-charts' JS लायब्ररी वापरून खरा
TradingView-style candlestick chart — plotly ऐवजी. हा फक्त Dashboard मध्ये
(इंटरॅक्टिव्ह HTML component) वापरला जातो; PDF रिपोर्टसाठी अजूनही
chart_builder.py (plotly + kaleido) वापरतो, कारण lightweight-charts
थेट स्टॅटिक इमेज एक्सपोर्ट करत नाही.
"""

import json
import pandas as pd

from investment_technical import compute_support_resistance_levels


def build_lightweight_chart_html(chart_df: pd.DataFrame, analysis: dict, ticker: str,
                                  timeframe: str, height: int = 520) -> str:
    df = chart_df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    # Daily/Weekly/Monthly साठी नुसती तारीख पुरते, पण Intraday (75-Minute)
    # साठी वेळही लागते — नाहीतर एकाच दिवसाचे सगळे बार्स एकावर एक collapse
    # होतात. एकाच calendar date वर एकापेक्षा जास्त बार्स असतील तर ते
    # intraday आहे असं ओळखून Unix timestamp (seconds) वापरतो.
    is_intraday = df["Date"].dt.date.duplicated().any()
    if is_intraday:
        # dtype-agnostic (pandas कधी datetime64[ns] तर कधी datetime64[us]
        # वापरतं — astype(int64) दोन्हीत वेगळा result देतं, त्यामुळे थेट
        # Timedelta ने भागून सेकंद काढतो, हे नेहमी बरोबर येतं)
        epoch = pd.Timestamp("1970-01-01")
        df["time"] = ((df["Date"] - epoch) / pd.Timedelta(seconds=1)).astype(int)
    else:
        df["time"] = df["Date"].dt.strftime("%Y-%m-%d")

    candles = df[["time", "Open", "High", "Low", "Close"]].rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"}
    ).to_dict(orient="records")

    ema_series = []
    if "EMA_50" in df.columns:
        ema_series = df[["time", "EMA_50"]].dropna().rename(
            columns={"EMA_50": "value"}
        ).to_dict(orient="records")

    # ---- Support/Resistance — जवळपासचे swing points clustered करून,
    # touch-count (probability) नुसार strength ठरवतो — chart वर तेच
    # strength line-width/color/style ठरवतं ----
    sr_levels = compute_support_resistance_levels(
        analysis.get("swing_highs", []), analysis.get("swing_lows", []), tolerance_pct=1.5
    )[:12]  # जास्त गोंधळ टाळण्यासाठी टॉप १२ पुरेत (आधीच touch-count नुसार sorted आहेत)

    sr_levels_json = json.dumps(sr_levels)

    candles_json = json.dumps(candles)
    ema_json = json.dumps(ema_series)

    html = f"""
<div id="tv_chart_container" style="width:100%; height:{height}px;"></div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function() {{
    const container = document.getElementById('tv_chart_container');
    const chart = LightweightCharts.createChart(container, {{
        width: container.clientWidth,
        height: {height},
        layout: {{
            background: {{ color: '#0b0e14' }},
            textColor: '#d1d4dc',
        }},
        grid: {{
            vertLines: {{ color: '#1e222d' }},
            horzLines: {{ color: '#1e222d' }},
        }},
        crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
        rightPriceScale: {{ borderColor: '#2a2e39' }},
        timeScale: {{ borderColor: '#2a2e39', timeVisible: true }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
        upColor: '#26a69a', downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    }});
    candleSeries.setData({candles_json});

    const emaData = {ema_json};
    if (emaData.length > 0) {{
        const emaSeries = chart.addLineSeries({{
            color: '#ecc94b', lineWidth: 1.5, title: 'EMA 50',
        }});
        emaSeries.setData(emaData);
    }}

    // ---- Support/Resistance — strength (touch_count) नुसार जाडी/रंग/style ----
    // Strong (४+ touches) = जाड, solid, ठळक रंग | Moderate (२-३) = मध्यम, dashed |
    // Weak (१) = बारीक, dotted, फिकट रंग — जितका जास्त probability तितकी रेषा जास्त ठळक
    const srLevels = {sr_levels_json};
    const STRENGTH_STYLE = {{
        'Strong':   {{ width: 3, style: LightweightCharts.LineStyle.Solid,  resColor: '#ff3333', supColor: '#00e676' }},
        'Moderate': {{ width: 2, style: LightweightCharts.LineStyle.Dashed, resColor: '#e53e3e', supColor: '#38a169' }},
        'Weak':     {{ width: 1, style: LightweightCharts.LineStyle.Dotted, resColor: '#e53e3e88', supColor: '#38a16988' }},
    }};
    srLevels.forEach(function(level) {{
        const st = STRENGTH_STYLE[level.strength] || STRENGTH_STYLE['Weak'];
        const color = level.type === 'Resistance' ? st.resColor : st.supColor;
        candleSeries.createPriceLine({{
            price: level.price,
            color: color,
            lineWidth: st.width,
            lineStyle: st.style,
            axisLabelVisible: true,
            title: level.type[0] + ' (' + level.touch_count + 'x)',
        }});
    }});

    chart.timeScale().fitContent();

    new ResizeObserver(entries => {{
        if (entries.length === 0 || entries[0].target !== container) return;
        chart.applyOptions({{ width: container.clientWidth }});
    }}).observe(container);
}})();
</script>
"""
    return html
