"""
Candlestick + RSI chart एकाच ठिकाणी बनवला जातो — Technical Chart page आणि
PDF report engine दोघेही हाच वापरतात, जेणेकरून PDF मधला chart आणि dashboard
मधला chart नेहमी सारखाच दिसेल.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_technical_chart(chart_df, analysis: dict, ticker: str, timeframe: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03,
        subplot_titles=(f"{ticker} — {timeframe}", "RSI (14)"),
    )

    fig.add_trace(go.Candlestick(
        x=chart_df["Date"], open=chart_df["Open"], high=chart_df["High"],
        low=chart_df["Low"], close=chart_df["Close"], name="Price",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=chart_df["Date"], y=chart_df["EMA_50"], name="EMA 50",
        line=dict(color="#ecc94b", width=1.5),
    ), row=1, col=1)

    for level in set(analysis.get("swing_highs", [])):
        fig.add_hline(y=level, line=dict(color="#e53e3e", width=0.5, dash="dot"), row=1, col=1)
    for level in set(analysis.get("swing_lows", [])):
        fig.add_hline(y=level, line=dict(color="#38a169", width=0.5, dash="dot"), row=1, col=1)

    for box in analysis.get("fvg_boxes", [])[-15:]:
        fig.add_hrect(
            y0=box["bottom"], y1=box["top"],
            fillcolor="#63b3ed", opacity=0.15, line_width=0,
            row=1, col=1,
        )

    fig.add_trace(go.Scatter(
        x=chart_df["Date"], y=chart_df["RSI"], name="RSI",
        line=dict(color="#9f7aea", width=1.5),
    ), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="#e53e3e", width=0.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="#38a169", width=0.5, dash="dash"), row=2, col=1)

    fig.update_layout(
        height=700, template="plotly_dark", showlegend=True,
        xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="#0b0e14", plot_bgcolor="#0b0e14",
    )
    return fig
