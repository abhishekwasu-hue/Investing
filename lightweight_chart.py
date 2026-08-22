"""
TradingView चा अधिकृत 'lightweight-charts' JS लायब्ररी वापरून खरा
TradingView-style candlestick chart — plotly ऐवजी. हा फक्त Dashboard मध्ये
(इंटरॅक्टिव्ह HTML component) वापरला जातो; PDF रिपोर्टसाठी अजूनही
chart_builder.py (plotly + kaleido) वापरतो, कारण lightweight-charts
थेट स्टॅटिक इमेज एक्सपोर्ट करत नाही.
"""

import json
import pandas as pd


def build_lightweight_chart_html(chart_df: pd.DataFrame, analysis: dict, ticker: str,
                                  timeframe: str, height: int = 520) -> str:
    df = chart_df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["time"] = df["Date"].dt.strftime("%Y-%m-%d")

    candles = df[["time", "Open", "High", "Low", "Close"]].rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"}
    ).to_dict(orient="records")

    ema_series = []
    if "EMA_50" in df.columns:
        ema_series = df[["time", "EMA_50"]].dropna().rename(
            columns={"EMA_50": "value"}
        ).to_dict(orient="records")

    # Swing highs/lows -> horizontal price lines
    swing_highs = list(set(analysis.get("swing_highs", [])))[:15]
    swing_lows = list(set(analysis.get("swing_lows", [])))[:15]

    candles_json = json.dumps(candles)
    ema_json = json.dumps(ema_series)
    swing_highs_json = json.dumps(swing_highs)
    swing_lows_json = json.dumps(swing_lows)

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

    // Swing highs (red) / lows (green) — price lines
    const swingHighs = {swing_highs_json};
    const swingLows = {swing_lows_json};
    swingHighs.forEach(function(price) {{
        candleSeries.createPriceLine({{
            price: price, color: '#e53e3e', lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false,
        }});
    }});
    swingLows.forEach(function(price) {{
        candleSeries.createPriceLine({{
            price: price, color: '#38a169', lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: false,
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
