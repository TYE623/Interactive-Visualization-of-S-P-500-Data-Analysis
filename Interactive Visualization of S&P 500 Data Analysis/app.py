# =============================================================================
# S&P 500 Multi-Factor Risk & Return Dashboard
# ACC102 Mini Assignment — Track 4
# Author: Taocheng Ye | Xi'an Jiaotong-Liverpool University
# Run: streamlit run app.py
# =============================================================================

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from scipy import stats
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="S&P 500 Risk & Return Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0e1117; color: #f0f6fc; }

    /* Sidebar */
    [data-testid="stSidebar"] { 
        background-color: #161b22; 
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] h3 {
        color: #58a6ff !important;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #e6edf3 !important;
    }

    /* Text and labels */
    p { color: #e6edf3; }
    label { color: #e6edf3 !important; }
    .stCaption { color: #8b949e !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] { 
        font-size: 1.5rem !important; 
        font-weight: 700;
        color: #58a6ff !important;
    }
    [data-testid="stMetricLabel"] {
        color: #d0d4d9 !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #0e1117; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 6px;
        border: 1px solid #30363d;
        color: #d0d4d9;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: #ffffff !important;
        border-color: #1f6feb !important;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #58a6ff;
        border-bottom: 1px solid #30363d;
        padding-bottom: 6px;
        margin-bottom: 12px;
    }

    /* Info boxes */
    .insight-box {
        background-color: #161b22;
        border-left: 3px solid #1f6feb;
        border-radius: 0 6px 6px 0;
        padding: 10px 14px;
        margin: 8px 0;
        font-size: 0.9rem;
        color: #e6edf3;
    }
    .warning-box {
        background-color: #161b22;
        border-left: 3px solid #f0883e;
        border-radius: 0 6px 6px 0;
        padding: 10px 14px;
        margin: 8px 0;
        font-size: 0.9rem;
        color: #e6edf3;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Plotly Theme ──────────────────────────────────────────────────────────────
PLOTLY_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(family="Inter, sans-serif", color="#e6edf3", size=12),
    margin=dict(l=40, r=20, t=50, b=40),
)

# ── Legend Template (for use in individual charts) ──────────────────────────────
LEGEND_STYLE = dict(
    bgcolor="rgba(22,27,34,0.8)",
    bordercolor="#30363d",
    borderwidth=1,
    font=dict(family="Inter, sans-serif", color="#f0f6fc", size=11)
)

SECTOR_NAMES = {
    'XLK':  'Technology',    'XLF':  'Financials',
    'XLE':  'Energy',        'XLV':  'Health Care',
    'XLI':  'Industrials',   'XLY':  'Consumer Discret.',
    'XLP':  'Consumer Stap.','XLU':  'Utilities',
    'XLB':  'Materials',     'XLRE': 'Real Estate',
    'XLC':  'Communication'
}

# ── Data Loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    base = "data"
    master  = pd.read_csv(f"{base}/master_data.csv",     index_col=0, parse_dates=True)
    returns = pd.read_csv(f"{base}/returns_data.csv",    index_col=0, parse_dates=True)
    reg     = pd.read_csv(f"{base}/regression_data.csv", index_col=0, parse_dates=True)
    betas   = pd.read_csv(f"{base}/sector_betas.csv",    index_col=0)
    mc      = pd.read_csv(f"{base}/monte_carlo_results.csv")
    return master, returns, reg, betas, mc

try:
    master, returns, reg, betas, mc = load_data()
    DATA_OK = True
except FileNotFoundError:
    DATA_OK = False

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("## 📈 S&P 500 Dashboard")
    st.markdown("*ACC102 · Track 4 · XJTLU*")
    st.divider()

    if DATA_OK:
        st.markdown("### 🗓️ Analysis Window")
        date_min = master.index.min().date()
        date_max = master.index.max().date()

        date_range = st.slider(
            "Select Date Range",
            min_value=date_min,
            max_value=date_max,
            value=(date_min, date_max),
            format="YYYY-MM"
        )
        start_dt = pd.Timestamp(date_range[0])
        end_dt   = pd.Timestamp(date_range[1])

        st.divider()
        st.markdown("### ⚙️ Risk Parameters")
        confidence_level = st.select_slider(
            "VaR Confidence Level",
            options=[0.90, 0.95, 0.99],
            value=0.95
        )
        st.caption(f"Selected: {int(confidence_level*100)}%")
        rolling_window = st.selectbox(
            "Rolling Window",
            options=[21, 63, 126, 252],
            index=1
        )
        window_labels = {21: '1 Month', 63: '1 Quarter', 126: '6 Months', 252: '1 Year'}
        st.caption(f"Selected: {window_labels[rolling_window]}")

        st.divider()
        st.markdown("### 🎲 Monte Carlo")
        mc_horizon = st.slider("Forecast Horizon (days)", 63, 504, 252, 63)
        st.caption(f"~{mc_horizon//21} months")
        mc_sims    = st.select_slider("Simulations", [1000, 5000, 10000], value=5000)

        st.divider()
        # Summary stats (handle different index lengths)
        master_mask = (master.index >= start_dt) & (master.index <= end_dt)
        returns_mask = (returns.index >= start_dt) & (returns.index <= end_dt)
        sp_slice = master.loc[master_mask, 'SP500']
        ret_slice = returns.loc[returns_mask, 'SP500_log'].dropna()

        n_days = returns_mask.sum()
        cagr   = ret_slice.mean() * 252 * 100
        vol    = ret_slice.std() * np.sqrt(252) * 100

        st.markdown("### 📊 Period Summary")
        st.metric("Trading Days", f"{n_days:,}")
        st.metric("CAGR", f"{cagr:.2f}%")
        st.metric("Annual Volatility", f"{vol:.2f}%")

        data_start = master.index.min().strftime('%Y-%m-%d')
        data_end   = master.index.max().strftime('%Y-%m-%d')
        st.caption(f"Data: {data_start} → {data_end}")
    else:
        st.error("⚠️ Data files not found.\n\nPlease run the analysis notebook first:\n`notebooks/01_data_fetching_eda.ipynb`")
        st.stop()

# =============================================================================
# HEADER
# =============================================================================
st.markdown("""
<div style="padding:20px 0 10px 0;">
    <h1 style="margin:0; font-size:2rem; color:#ffffff;">
        S&P 500 Multi-Factor Risk & Return Dashboard
    </h1>
    <p style="margin:4px 0 0 0; color:#b8c5d6; font-size:0.95rem;">
        Macro Factors · Sector Dynamics · Monte Carlo Simulation · Risk Metrics
    </p>
</div>
""", unsafe_allow_html=True)

# Filter data to selected window
mask       = (master.index  >= start_dt) & (master.index  <= end_dt)
ret_mask   = (returns.index >= start_dt) & (returns.index <= end_dt)
reg_mask   = (reg.index     >= start_dt) & (reg.index     <= end_dt)
m  = master.loc[mask].copy()
r  = returns.loc[ret_mask].copy()
rg = reg.loc[reg_mask].copy()

# ── Top KPI Strip ─────────────────────────────────────────────────────────────
log_ret   = r['SP500_log'].dropna()
cagr      = log_ret.mean() * 252 * 100
vol_ann   = log_ret.std()  * np.sqrt(252) * 100
var_val   = np.percentile(log_ret, (1-confidence_level)*100) * 100
cvar_val  = log_ret[log_ret <= np.percentile(log_ret, (1-confidence_level)*100)].mean() * 100
max_dd    = r['drawdown'].min() * 100 if 'drawdown' in r.columns else np.nan
rf_est    = m['10Y_Treasury_Yield'].mean() / 100 if '10Y_Treasury_Yield' in m.columns else 0.04
sharpe    = (log_ret.mean()*252 - rf_est) / (log_ret.std()*np.sqrt(252))
total_ret = ((m['SP500'].iloc[-1] / m['SP500'].iloc[0]) - 1) * 100

col1,col2,col3,col4,col5,col6 = st.columns(6)
col1.metric("Total Return",      f"{total_ret:+.1f}%")
col2.metric("CAGR",              f"{cagr:.2f}%")
col3.metric("Ann. Volatility",   f"{vol_ann:.2f}%")
col4.metric("Sharpe Ratio",      f"{sharpe:.3f}")
col5.metric(f"VaR {int(confidence_level*100)}%",  f"{var_val:.2f}%", delta=f"CVaR {cvar_val:.2f}%", delta_color="inverse")
col6.metric("Max Drawdown",      f"{max_dd:.2f}%", delta_color="inverse")

st.divider()

# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Price & Returns",
    "🔗 Macro Factor Analysis",
    "🏭 Sector Analysis",
    "🎲 Monte Carlo Simulation",
    "⚡ Risk Metrics"
])

# =============================================================================
# TAB 1 — PRICE & RETURNS EXPLORER
# =============================================================================
with tab1:
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.markdown('<div class="section-header">S&P 500 Price, VIX & Drawdown</div>', unsafe_allow_html=True)

        chart_type = st.radio("Price Scale", ["Linear", "Log"], horizontal=True, key="price_scale")
        show_vol   = st.checkbox("Show Rolling Volatility Bands", value=True)

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            subplot_titles=('S&P 500 Price', 'VIX — Fear Index', 'Drawdown from Peak (%)'),
            row_heights=[0.55, 0.22, 0.23],
            vertical_spacing=0.04
        )

        # Price
        fig.add_trace(go.Scatter(
            x=m.index, y=m['SP500'], name='S&P 500',
            line=dict(color='#58a6ff', width=1.8)
        ), row=1, col=1)

        if show_vol and 'vol_63d' in r.columns:
            sp_aligned = m['SP500'].reindex(r.index)
            upper = sp_aligned * (1 + r['vol_63d']/np.sqrt(252)*1.5)
            lower = sp_aligned * (1 - r['vol_63d']/np.sqrt(252)*1.5)
            fig.add_trace(go.Scatter(
                x=r.index, y=upper, name='Vol Band (+)',
                line=dict(width=0), showlegend=False
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=r.index, y=lower, name='Vol Band',
                fill='tonexty', fillcolor='rgba(34,197,94,0.25)',
                line=dict(width=1.2, color='#22c55e', dash='dot'), showlegend=True
            ), row=1, col=1)

        # VIX with panic zones
        vix_color = ['#ef4444' if v > 30 else '#f97316' if v > 20 else '#22c55e'
                     for v in m['VIX']]
        fig.add_trace(go.Scatter(
            x=m.index, y=m['VIX'], name='VIX',
            line=dict(color='#f97316', width=1.2)
        ), row=2, col=1)
        fig.add_hrect(y0=30, y1=m['VIX'].max()+5, row=2, col=1,
                      fillcolor="rgba(239,68,68,0.1)", line_width=0, annotation_text="Panic Zone (VIX>30)")
        fig.add_hrect(y0=20, y1=30, row=2, col=1,
                      fillcolor="rgba(249,115,22,0.08)", line_width=0, annotation_text="Elevated")

        # Drawdown
        if 'drawdown' in r.columns:
            fig.add_trace(go.Scatter(
                x=r.index, y=r['drawdown']*100, name='Drawdown',
                fill='tozeroy', fillcolor='rgba(239,68,68,0.25)',
                line=dict(color='#ef4444', width=1)
            ), row=3, col=1)

        if chart_type == "Log":
            fig.update_yaxes(type='log', row=1, col=1)

        fig.update_layout(height=580, showlegend=True,
                          legend=dict(orientation='h', y=1.02, x=0, **LEGEND_STYLE),
                          **PLOTLY_THEME)
        fig.update_yaxes(tickprefix="$", row=1, col=1)
        fig.update_yaxes(ticksuffix="%", row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-header">Return Distribution</div>', unsafe_allow_html=True)

        # Distribution histogram
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=log_ret*100, nbinsx=60, name='Daily Returns',
            marker_color='#58a6ff', opacity=0.7,
            histnorm='probability density'
        ))
        x_norm = np.linspace(log_ret.min()*100, log_ret.max()*100, 200)
        y_norm = stats.norm.pdf(x_norm, log_ret.mean()*100, log_ret.std()*100)
        fig2.add_trace(go.Scatter(
            x=x_norm, y=y_norm, name='Normal Fit',
            line=dict(color='#ef4444', width=2, dash='dash')
        ))
        fig2.add_vline(x=var_val, line_dash='dot', line_color='#f97316',
                       annotation_text=f'VaR {int(confidence_level*100)}%', annotation_font_size=10)
        fig2.update_layout(
            height=260, showlegend=True,
            title="Daily Log Return Distribution",
            xaxis_title="Return (%)", yaxis_title="Density",
            legend=dict(orientation='h', y=1.15, **LEGEND_STYLE),
            **PLOTLY_THEME
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Stats table
        kurt  = log_ret.kurtosis()
        skew  = log_ret.skew()
        jb_stat, jb_p = stats.jarque_bera(log_ret)

        stats_data = {
            "Metric": ["Mean (daily)", "Std Dev (daily)", "Skewness", "Excess Kurtosis", "JB p-value"],
            "Value":  [f"{log_ret.mean()*100:.4f}%",
                       f"{log_ret.std()*100:.4f}%",
                       f"{skew:.4f}",
                       f"{kurt:.2f}",
                       f"{jb_p:.2e}"]
        }
        st.dataframe(pd.DataFrame(stats_data), hide_index=True, use_container_width=True)

        st.markdown(f"""
        <div class="warning-box">
        ⚠️ <strong>Fat Tails Detected</strong><br>
        Excess kurtosis = {kurt:.1f} (Normal = 0). JB test rejects normality (p≈0).
        Extreme losses occur ~{kurt/3:.1f}× more often than a normal model predicts.
        </div>""", unsafe_allow_html=True)

        # Rolling Sharpe
        st.markdown('<div class="section-header" style="margin-top:12px">Rolling Sharpe Ratio</div>', unsafe_allow_html=True)
        if 'rolling_sharpe_63d' in r.columns:
            fig3 = go.Figure()
            rs = r['rolling_sharpe_63d'].dropna()
            colors_sharpe = ['#22c55e' if v > 0 else '#ef4444' for v in rs]
            fig3.add_trace(go.Bar(
                x=rs.index, y=rs, name='Sharpe',
                marker_color=colors_sharpe, opacity=0.8
            ))
            fig3.add_hline(y=0, line_color='white', line_width=0.5)
            fig3.add_hline(y=1, line_dash='dash', line_color='#22c55e',
                           annotation_text='Sharpe=1', annotation_font_size=9)
            fig3.update_layout(height=220, showlegend=False,
                               title="63-Day Rolling Sharpe",
                               xaxis_title="", yaxis_title="Sharpe",
                               **PLOTLY_THEME)
            st.plotly_chart(fig3, use_container_width=True)

# =============================================================================
# TAB 2 — MACRO FACTOR ANALYSIS
# =============================================================================
with tab2:
    st.markdown('<div class="section-header">Macro Factor Correlation & OLS Regression</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])

    with col_a:
        # Correlation heatmap
        macro_cols_available = [c for c in ['SP500_ret','VIX_chg','Treasury_chg','USD_chg','VIX','Treasury_10Y','Fed_Rate','USD_Index']
                                 if c in rg.columns]
        corr = rg[macro_cols_available].corr()
        labels_map = {
            'SP500_ret': 'S&P500 Return', 'VIX_chg': 'ΔVIX',
            'Treasury_chg': 'Δ10Y Yield', 'USD_chg': 'ΔUSD Index',
            'VIX': 'VIX Level', 'Treasury_10Y': '10Y Yield',
            'Fed_Rate': 'Fed Rate', 'USD_Index': 'USD Index'
        }
        corr.index   = [labels_map.get(c, c) for c in corr.index]
        corr.columns = [labels_map.get(c, c) for c in corr.columns]

        fig_corr = px.imshow(
            corr, text_auto='.2f',
            color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
            title='Correlation Matrix: Returns vs Macro Factors',
            aspect='auto'
        )
        fig_corr.update_layout(height=400, coloraxis_showscale=True, **PLOTLY_THEME)
        st.plotly_chart(fig_corr, use_container_width=True)

    with col_b:
        # Scatter: S&P vs VIX change
        st.markdown("**S&P 500 Return vs ΔVIX (daily)**")
        if 'VIX_chg' in rg.columns and 'SP500_ret' in rg.columns:
            scatter_df = rg[['SP500_ret','VIX_chg']].dropna()
            # Colour by return sign
            scatter_df['color'] = scatter_df['SP500_ret'].apply(lambda x: 'Up' if x>0 else 'Down')

            fig_sc = go.Figure()
            for label, clr in [('Up', '#22c55e'), ('Down', '#ef4444')]:
                sub = scatter_df[scatter_df['color']==label]
                fig_sc.add_trace(go.Scatter(
                    x=sub['VIX_chg']*100, y=sub['SP500_ret']*100,
                    mode='markers', name=label,
                    marker=dict(color=clr, size=3, opacity=0.4)
                ))

            # OLS trendline
            x_sc = sm.add_constant(scatter_df['VIX_chg'])
            ols_sc = sm.OLS(scatter_df['SP500_ret'], x_sc).fit()
            x_line = np.linspace(scatter_df['VIX_chg'].min(), scatter_df['VIX_chg'].max(), 100)
            y_line = ols_sc.params['const'] + ols_sc.params['VIX_chg'] * x_line
            fig_sc.add_trace(go.Scatter(
                x=x_line*100, y=y_line*100, name=f"OLS (β={ols_sc.params['VIX_chg']:.4f})",
                line=dict(color='white', width=2, dash='dash')
            ))
            fig_sc.update_layout(
                height=400, xaxis_title='ΔVIX (%)', yaxis_title='S&P 500 Return (%)',
                title=f"R² = {ols_sc.rsquared:.3f} | β(VIX) = {ols_sc.params['VIX_chg']:.4f}",
                **PLOTLY_THEME
            )
            st.plotly_chart(fig_sc, use_container_width=True)

    # OLS Multi-Factor Results Table
    st.markdown('<div class="section-header">OLS Regression: S&P 500 Return ~ ΔVIX + ΔTreasury + ΔUSD</div>', unsafe_allow_html=True)

    reg_vars = [c for c in ['VIX_chg','Treasury_chg','USD_chg'] if c in rg.columns]
    if reg_vars and 'SP500_ret' in rg.columns:
        reg_clean = rg[['SP500_ret'] + reg_vars].dropna()
        X_full = sm.add_constant(reg_clean[reg_vars])
        ols_full = sm.OLS(reg_clean['SP500_ret'], X_full).fit(cov_type='HC3')

        col_ols1, col_ols2, col_ols3 = st.columns(3)
        col_ols1.metric("R-squared",   f"{ols_full.rsquared:.4f}",
                         help="Fraction of return variance explained by macro factors")
        col_ols2.metric("F-statistic", f"{ols_full.fvalue:.2f}",
                         help="Joint significance of all regressors")
        col_ols3.metric("Observations",f"{int(ols_full.nobs):,}")

        # Coefficient table
        coef_df = pd.DataFrame({
            'Variable':  ['Intercept'] + [{'VIX_chg':'ΔVIX','Treasury_chg':'Δ10Y Yield','USD_chg':'ΔUSD'}
                                           .get(v,v) for v in reg_vars],
            'Coefficient': ols_full.params.values,
            'Std Error':   ols_full.bse.values,
            't-statistic': ols_full.tvalues.values,
            'p-value':     ols_full.pvalues.values,
            'Significant': ['✅' if p < 0.05 else '❌' for p in ols_full.pvalues.values]
        })
        coef_df['Coefficient'] = coef_df['Coefficient'].map('{:.6f}'.format)
        coef_df['Std Error']   = coef_df['Std Error'].map('{:.6f}'.format)
        coef_df['t-statistic'] = coef_df['t-statistic'].map('{:.3f}'.format)
        coef_df['p-value']     = coef_df['p-value'].map('{:.4f}'.format)
        st.dataframe(coef_df, hide_index=True, use_container_width=True)

        st.markdown("""
        <div class="insight-box">
        💡 <strong>Interpretation</strong>: HC3 heteroscedasticity-robust standard errors used.
        Low R² is expected for daily returns — macro factors explain the <em>direction</em> of risk, not precise daily magnitude.
        ΔVIX is the dominant factor: markets systematically sell off as fear spikes.
        </div>""", unsafe_allow_html=True)

    # Macro time series panel
    st.markdown('<div class="section-header">Macro Factor Time Series</div>', unsafe_allow_html=True)

    macro_available = {k: v for k, v in {
        '10Y_Treasury_Yield': '10Y Treasury Yield (%)',
        'Fed_Funds_Rate':      'Fed Funds Rate (%)',
        'USD_Index':           'USD Index (Trade-Weighted)',
        'VIX':                 'VIX (Implied Volatility)'
    }.items() if k in m.columns}

    selected_macro = st.multiselect(
        "Select macro indicators to display:",
        options=list(macro_available.values()),
        default=list(macro_available.values())[:3]
    )
    inv_map = {v: k for k, v in macro_available.items()}

    if selected_macro:
        fig_macro = make_subplots(
            rows=len(selected_macro), cols=1, shared_xaxes=True,
            subplot_titles=selected_macro,
            vertical_spacing=0.06
        )
        colors_macro = ['#58a6ff','#22c55e','#f97316','#a855f7']
        for i, label in enumerate(selected_macro):
            col_key = inv_map[label]
            if col_key in m.columns:
                fig_macro.add_trace(go.Scatter(
                    x=m.index, y=m[col_key], name=label,
                    line=dict(color=colors_macro[i % len(colors_macro)], width=1.5)
                ), row=i+1, col=1)
        fig_macro.update_layout(
            height=120*len(selected_macro)+60, showlegend=False, **PLOTLY_THEME
        )
        st.plotly_chart(fig_macro, use_container_width=True)

# =============================================================================
# TAB 3 — SECTOR ANALYSIS
# =============================================================================
with tab3:
    st.markdown('<div class="section-header">S&P 500 Sector Rotation & Beta Analysis</div>', unsafe_allow_html=True)

    col_s1, col_s2 = st.columns([1, 1])

    with col_s1:
        # Sector Beta bar chart (from pre-computed betas)
        if len(betas) > 0 and 'Beta' in betas.columns:
            beta_sorted = betas.sort_values('Beta', ascending=True)
            bar_colors  = ['#22c55e' if b < 1.0 else '#ef4444' for b in beta_sorted['Beta']]

            fig_beta = go.Figure()
            fig_beta.add_trace(go.Bar(
                x=beta_sorted['Beta'],
                y=beta_sorted['Sector'] if 'Sector' in beta_sorted.columns else beta_sorted.index,
                orientation='h',
                marker_color=bar_colors,
                text=[f"{b:.3f}" for b in beta_sorted['Beta']],
                textposition='outside',
                textfont=dict(size=11)
            ))
            fig_beta.add_vline(x=1.0, line_dash='dash', line_color='yellow',
                               annotation_text='β=1 (Market)', annotation_font_size=10)
            fig_beta.update_layout(
                title='Sector Beta vs S&P 500<br><sup>Green=Defensive (β<1) · Red=Aggressive (β>1)</sup>',
                xaxis_title='Beta Coefficient',
                height=430, **PLOTLY_THEME
            )
            st.plotly_chart(fig_beta, use_container_width=True)

    with col_s2:
        # Sector performance heatmap (year-by-year returns)
        sector_cols = [c for c in r.columns if c.endswith('_log') and not c.startswith('SP')]
        tickers_in_data = [c.replace('_log','') for c in sector_cols]

        if tickers_in_data:
            r_copy = r[sector_cols + ['SP500_log']].copy()
            r_copy.index = pd.DatetimeIndex(r_copy.index)
            annual = r_copy.resample('YE').sum() * 100

            col_rename = {c: SECTOR_NAMES.get(c.replace('_log',''), c.replace('_log','')) for c in sector_cols}
            col_rename['SP500_log'] = 'S&P 500'
            annual.rename(columns=col_rename, inplace=True)
            annual.index = annual.index.year

            fig_heat = px.imshow(
                annual.T,
                text_auto='.1f',
                color_continuous_scale='RdYlGn',
                zmin=-40, zmax=50,
                title='Annual Sector Returns Heatmap (%)',
                aspect='auto',
                labels=dict(x='Year', y='Sector', color='Return %')
            )
            fig_heat.update_layout(height=430, **PLOTLY_THEME)
            st.plotly_chart(fig_heat, use_container_width=True)

    # Sector cumulative performance
    st.markdown('<div class="section-header">Cumulative Sector Performance (Indexed to 100)</div>', unsafe_allow_html=True)

    # sector selector
    all_sector_labels = [SECTOR_NAMES.get(t, t) for t in tickers_in_data]
    label_to_col = {SECTOR_NAMES.get(t,t): f'{t}_log' for t in tickers_in_data}

    selected_sectors = st.multiselect(
        "Select sectors to compare (max 6 recommended):",
        options=all_sector_labels,
        default=all_sector_labels[:5] if len(all_sector_labels) >= 5 else all_sector_labels
    )

    if selected_sectors:
        fig_cum = go.Figure()
        palette = ['#58a6ff','#22c55e','#f97316','#a855f7','#ec4899','#eab308',
                   '#06b6d4','#ef4444','#84cc16','#f43f5e','#10b981']

        # Add S&P 500 as reference
        sp_cum = (1 + r['SP500_log']).cumprod() * 100
        fig_cum.add_trace(go.Scatter(
            x=sp_cum.index, y=sp_cum,
            name='S&P 500 (Benchmark)',
            line=dict(color='white', width=2.5, dash='dot')
        ))

        for i, label in enumerate(selected_sectors):
            col_key = label_to_col.get(label)
            if col_key and col_key in r.columns:
                cum = (1 + r[col_key].fillna(0)).cumprod() * 100
                fig_cum.add_trace(go.Scatter(
                    x=cum.index, y=cum, name=label,
                    line=dict(color=palette[i % len(palette)], width=1.8)
                ))

        fig_cum.update_layout(
            title='Sector Cumulative Return (Base=100)',
            yaxis_title='Indexed Return',
            height=400, **PLOTLY_THEME,
            legend=dict(orientation='h', y=1.02, x=0, xanchor='left', yanchor='bottom', **LEGEND_STYLE)
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    # Rolling 63-day sector correlation with S&P500
    st.markdown('<div class="section-header">Rolling Sector Correlation with S&P 500 (63-Day)</div>', unsafe_allow_html=True)

    if tickers_in_data and 'SP500_log' in r.columns:
        show_tickers = tickers_in_data[:6]
        fig_roll_corr = go.Figure()
        pal2 = ['#58a6ff','#22c55e','#f97316','#a855f7','#ec4899','#eab308']
        for i, t in enumerate(show_tickers):
            col = f'{t}_log'
            if col in r.columns:
                roll_c = r[col].rolling(63).corr(r['SP500_log'])
                fig_roll_corr.add_trace(go.Scatter(
                    x=roll_c.index, y=roll_c,
                    name=SECTOR_NAMES.get(t, t),
                    line=dict(color=pal2[i], width=1.3)
                ))
        fig_roll_corr.add_hline(y=1.0, line_dash='dash', line_color='white', line_width=0.5)
        fig_roll_corr.update_layout(
            height=320, yaxis_title='Rolling Correlation', **PLOTLY_THEME,
            legend=dict(orientation='h', y=1.05, x=0, xanchor='left', yanchor='bottom', **LEGEND_STYLE)
        )
        st.plotly_chart(fig_roll_corr, use_container_width=True)
        st.markdown("""
        <div class="insight-box">
        💡 <strong>Sector Rotation Insight</strong>: When correlations converge toward 1 (e.g. 2020 COVID crash),
        diversification benefits collapse — all sectors fall together. Low-correlation sectors
        (typically Utilities, Consumer Staples) provide defensive value during stress periods.
        </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 4 — MONTE CARLO SIMULATION
# =============================================================================
with tab4:
    st.markdown('<div class="section-header">Monte Carlo Simulation — Geometric Brownian Motion</div>', unsafe_allow_html=True)

    # Re-run simulation with user parameters
    log_ret_mc = r['SP500_log'].dropna()
    mu_d     = log_ret_mc.mean()
    sigma_d  = log_ret_mc.std()
    S0       = m['SP500'].iloc[-1]

    col_mc1, col_mc2, col_mc3, col_mc4 = st.columns(4)
    col_mc1.metric("Current S&P 500", f"{S0:,.2f}")
    col_mc2.metric("Daily Drift (μ)", f"{mu_d:.5f}", help=f"Annualised: {mu_d*252*100:.2f}%")
    col_mc3.metric("Daily Vol (σ)",   f"{sigma_d:.5f}", help=f"Annualised: {sigma_d*np.sqrt(252)*100:.2f}%")
    col_mc4.metric("Horizon",         f"{mc_horizon} days (~{mc_horizon//21} months)")

    # Advanced options
    with st.expander("⚙️ Advanced Monte Carlo Settings"):
        col_adv1, col_adv2 = st.columns(2)
        with col_adv1:
            use_fat_tails = st.checkbox("Use Student-t distribution (fat tails)", value=False,
                                        help="More realistic — captures excess kurtosis observed in actual returns")
            t_dof = st.slider("Degrees of freedom (t-distribution)", 3, 30, 5) if use_fat_tails else None
        with col_adv2:
            shock_pct  = st.slider("Apply market shock (%)", -30, 30, 0,
                                    help="Simulate a one-off shock at start of projection (e.g. -20% crash)")
            S0_shocked = S0 * (1 + shock_pct/100)

    # Run GBM
    @st.cache_data(max_entries=20)
    def run_gbm(mu, sigma, S_start, T, N, fat_tails=False, dof=5, seed=42):
        np.random.seed(seed)
        if fat_tails and dof:
            Z = stats.t.rvs(df=dof, size=(T, N)) / np.sqrt(dof/(dof-2))
        else:
            Z = np.random.standard_normal((T, N))
        dr = np.exp((mu - 0.5*sigma**2) + sigma*Z)
        paths = S_start * np.cumprod(dr, axis=0)
        return paths

    with st.spinner("Running simulation…"):
        paths = run_gbm(mu_d, sigma_d, S0_shocked, mc_horizon, mc_sims,
                        fat_tails=use_fat_tails, dof=t_dof if use_fat_tails else None)
    terminal = paths[-1, :]

    # Percentile summary
    pct_labels = [5, 10, 25, 50, 75, 90, 95]
    pct_values = {p: np.percentile(terminal, p) for p in pct_labels}

    st.markdown('<div class="section-header">Simulation Results</div>', unsafe_allow_html=True)
    cols_pct = st.columns(len(pct_labels))
    colors_pct = ['#ef4444','#f97316','#eab308','#22c55e','#22c55e','#22c55e','#22c55e']
    for i, (p, col) in enumerate(zip(pct_labels, cols_pct)):
        val  = pct_values[p]
        chg  = (val/S0 - 1)*100
        col.metric(f"P{p}", f"{val:,.0f}", delta=f"{chg:+.1f}%",
                   delta_color="normal" if p >= 50 else "inverse")

    # Path fan chart
    col_mc_l, col_mc_r = st.columns([2, 1])

    with col_mc_l:
        fig_mc = go.Figure()

        # Sample paths
        n_show = min(300, mc_sims)
        sample_idx = np.random.choice(mc_sims, n_show, replace=False)
        for i in sample_idx:
            fig_mc.add_trace(go.Scatter(
                y=paths[:, i], mode='lines',
                line=dict(width=0.4, color='rgba(88,166,255,0.12)'),
                showlegend=False, hoverinfo='skip'
            ))

        # Percentile bands
        day_axis = np.arange(1, mc_horizon+1)
        band_config = [
            (95, '#22c55e', '95th Percentile'),
            (75, '#58a6ff', '75th Percentile'),
            (50, '#f0f6fc', 'Median'),
            (25, '#f97316', '25th Percentile'),
            (5,  '#ef4444', '5th Percentile'),
        ]
        for p, clr, name in band_config:
            pct_line = np.percentile(paths, p, axis=1)
            fig_mc.add_trace(go.Scatter(
                x=day_axis, y=pct_line, name=name,
                line=dict(color=clr, width=2.2)
            ))

        fig_mc.add_hline(y=S0, line_dash='dot', line_color='yellow', line_width=1.5,
                         annotation_text=f'Today: {S0:,.0f}',
                         annotation_position='bottom right')
        if shock_pct != 0:
            fig_mc.add_annotation(x=1, y=S0_shocked,
                                  text=f"Shock: {shock_pct:+d}% → {S0_shocked:,.0f}",
                                  font=dict(color='#f97316', size=11))

        fig_mc.update_layout(
            title=f'GBM Monte Carlo: {mc_sims:,} paths · {mc_horizon}d horizon · '
                  f'{"Student-t" if use_fat_tails else "Normal"} distribution',
            xaxis_title='Trading Days',
            yaxis_title='S&P 500 Level',
            height=500, **PLOTLY_THEME,
            legend=dict(orientation='v', x=1.02, y=1, xanchor='left', yanchor='top', **LEGEND_STYLE)
        )
        st.plotly_chart(fig_mc, use_container_width=True)

    with col_mc_r:
        # Terminal distribution histogram
        fig_term = go.Figure()
        fig_term.add_trace(go.Histogram(
            x=terminal, nbinsx=60,
            marker_color='#58a6ff', opacity=0.75,
            name='Terminal S&P 500'
        ))
        fig_term.add_vline(x=S0, line_dash='dash', line_color='yellow',
                           annotation_text='Today', annotation_font_size=10)
        for p, clr, _ in band_config:
            fig_term.add_vline(x=pct_values[p], line_dash='dot', line_color=clr, line_width=1.5)

        fig_term.update_layout(
            title=f'Terminal Distribution<br><sup>{mc_horizon}-Day Horizon</sup>',
            xaxis_title='S&P 500 Level',
            yaxis_title='Count',
            height=300, showlegend=False, **PLOTLY_THEME
        )
        st.plotly_chart(fig_term, use_container_width=True)

        # Prob of gain / loss
        prob_above = (terminal > S0).mean() * 100
        prob_10pct_gain = (terminal > S0*1.10).mean() * 100
        prob_10pct_loss = (terminal < S0*0.90).mean() * 100

        st.markdown(f"""
        <div class="insight-box">
        🎲 <strong>Probability Estimates</strong><br>
        P(above today): <strong>{prob_above:.1f}%</strong><br>
        P(+10% gain):   <strong>{prob_10pct_gain:.1f}%</strong><br>
        P(-10% loss):   <strong>{prob_10pct_loss:.1f}%</strong>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="warning-box">
        ⚠️ <strong>GBM Limitations</strong><br>
        Assumes constant μ, σ and log-normal returns.
        Fat-tail mode (Student-t) partially corrects this.
        Past calibration ≠ future regime.
        Not investment advice.
        </div>""", unsafe_allow_html=True)

# =============================================================================
# TAB 5 — RISK METRICS
# =============================================================================
with tab5:
    st.markdown('<div class="section-header">Comprehensive Risk Metrics Dashboard</div>', unsafe_allow_html=True)

    # VaR / CVaR across all levels
    col_r1, col_r2 = st.columns([1, 1])

    with col_r1:
        cl_levels = [0.90, 0.95, 0.99]
        var_vals  = {cl: np.percentile(log_ret, (1-cl)*100)*100 for cl in cl_levels}
        cvar_vals = {cl: log_ret[log_ret <= np.percentile(log_ret, (1-cl)*100)].mean()*100 for cl in cl_levels}

        fig_risk = go.Figure()
        fig_risk.add_trace(go.Bar(
            x=[f"{int(c*100)}%" for c in cl_levels],
            y=[abs(var_vals[c]) for c in cl_levels],
            name='VaR (daily %)',
            marker_color='#f97316', text=[f"{abs(var_vals[c]):.3f}%" for c in cl_levels],
            textposition='outside'
        ))
        fig_risk.add_trace(go.Bar(
            x=[f"{int(c*100)}%" for c in cl_levels],
            y=[abs(cvar_vals[c]) for c in cl_levels],
            name='CVaR / Expected Shortfall',
            marker_color='#ef4444', text=[f"{abs(cvar_vals[c]):.3f}%" for c in cl_levels],
            textposition='outside'
        ))
        fig_risk.update_layout(
            title='Daily VaR vs CVaR by Confidence Level<br><sup>Absolute values — daily loss threshold</sup>',
            yaxis_title='Loss (%)',
            barmode='group', height=380, **PLOTLY_THEME,
            legend=dict(orientation='v', x=1.02, y=1, xanchor='left', yanchor='top', **LEGEND_STYLE)
        )
        st.plotly_chart(fig_risk, use_container_width=True)

        # VaR context
        selected_var = var_vals[confidence_level]
        selected_cvar = cvar_vals[confidence_level]
        st.markdown(f"""
        <div class="insight-box">
        📌 <strong>{int(confidence_level*100)}% VaR = {selected_var:.3f}%</strong><br>
        On any given trading day, there is a {int((1-confidence_level)*100)}% probability 
        of losing more than <strong>{abs(selected_var):.2f}%</strong> of portfolio value.<br><br>
        📌 <strong>CVaR = {selected_cvar:.3f}%</strong><br>
        When losses exceed the VaR, the average expected loss is 
        <strong>{abs(selected_cvar):.2f}%</strong> — this is the Expected Shortfall (ES).
        </div>""", unsafe_allow_html=True)

    with col_r2:
        # Rolling VaR over time
        roll_var = log_ret.rolling(rolling_window).apply(
            lambda x: np.percentile(x, (1-confidence_level)*100)*100, raw=True
        )
        roll_cvar = log_ret.rolling(rolling_window).apply(
            lambda x: x[x <= np.percentile(x, (1-confidence_level)*100)].mean()*100
            if len(x[x <= np.percentile(x, (1-confidence_level)*100)]) > 0 else np.nan,
            raw=True
        )

        fig_rv = go.Figure()
        fig_rv.add_trace(go.Scatter(
            x=roll_var.index, y=roll_var,
            name=f'{rolling_window}d Rolling VaR {int(confidence_level*100)}%',
            line=dict(color='#f97316', width=1.5)
        ))
        fig_rv.add_trace(go.Scatter(
            x=roll_cvar.index, y=roll_cvar,
            name=f'{rolling_window}d Rolling CVaR',
            line=dict(color='#ef4444', width=1.5, dash='dot'),
            fill='tonexty', fillcolor='rgba(239,68,68,0.08)'
        ))
        fig_rv.update_layout(
            title=f'Rolling {rolling_window}-Day VaR & CVaR Over Time',
            yaxis_title='Daily Loss (%)',
            height=380, **PLOTLY_THEME,
            legend=dict(orientation='v', x=1.02, y=1, xanchor='left', yanchor='top', **LEGEND_STYLE)
        )
        st.plotly_chart(fig_rv, use_container_width=True)

    # Vol regimes + GARCH-style rolling vol
    st.markdown('<div class="section-header">Volatility Regime Analysis</div>', unsafe_allow_html=True)

    col_v1, col_v2 = st.columns([2, 1])

    with col_v1:
        fig_vol = go.Figure()
        vol_cols = {
            '21d Realised Vol':  ('vol_21d',  '#eab308', 1.2),
            '63d Realised Vol':  ('vol_63d',  '#22c55e', 1.8),
            '252d Realised Vol': ('vol_252d', '#58a6ff', 2.2),
        }
        for label, (col_key, clr, width) in vol_cols.items():
            if col_key in r.columns:
                fig_vol.add_trace(go.Scatter(
                    x=r.index, y=r[col_key]*100,
                    name=label, line=dict(color=clr, width=width)
                ))

        if 'VIX' in m.columns:
            fig_vol.add_trace(go.Scatter(
                x=m.index, y=m['VIX'],
                name='VIX (Implied Vol)',
                line=dict(color='#ef4444', width=1.3, dash='dot')
            ))

        # Regime thresholds
        fig_vol.add_hrect(y0=30, y1=100, fillcolor='rgba(239,68,68,0.06)', line_width=0,
                          annotation_text='High Vol Regime (>30%)', annotation_font_size=9)
        fig_vol.add_hrect(y0=0,  y1=15,  fillcolor='rgba(34,197,94,0.06)', line_width=0,
                          annotation_text='Low Vol Regime (<15%)',  annotation_font_size=9)

        fig_vol.update_layout(
            title='Volatility Regimes: Realised vs Implied (VIX)',
            yaxis_title='Annualised Volatility (%)',
            height=400, **PLOTLY_THEME,
            legend=dict(orientation='v', x=1.02, y=1, xanchor='left', yanchor='top', **LEGEND_STYLE)
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_v2:
        # Tail risk summary table
        st.markdown("**Tail Risk Summary**")

        worst_days = log_ret.nsmallest(10).reset_index()
        worst_days.columns = ['Date', 'Log Return']
        worst_days['Return (%)'] = (worst_days['Log Return']*100).round(3)
        worst_days['Date'] = worst_days['Date'].dt.strftime('%Y-%m-%d')
        worst_days = worst_days[['Date','Return (%)']].head(10)
        st.dataframe(worst_days, hide_index=True, use_container_width=True, height=200)

        # Annualised metrics summary
        st.markdown("**Annualised Risk Summary**")
        metrics_tbl = pd.DataFrame({
            'Metric': ['CAGR','Volatility','Sharpe Ratio','Max Drawdown',
                       f'VaR {int(confidence_level*100)}% (Ann.)',
                       f'CVaR {int(confidence_level*100)}% (Ann.)'],
            'Value': [
                f"{cagr:.2f}%",
                f"{vol_ann:.2f}%",
                f"{sharpe:.3f}",
                f"{max_dd:.2f}%",
                f"{var_val*np.sqrt(252):.2f}%",
                f"{cvar_val*np.sqrt(252):.2f}%"
            ]
        })
        st.dataframe(metrics_tbl, hide_index=True, use_container_width=True)

        st.markdown("""
        <div class="insight-box">
        💡 VaR assumes i.i.d. returns. In reality, volatility clusters
        (ARCH effects) — losses tend to follow losses. CVaR (Expected Shortfall)
        is the Basel III / FRTB regulatory standard precisely because it captures
        tail severity, not just the threshold.
        </div>""", unsafe_allow_html=True)

    # Rolling Beta vs VIX (reprise from notebook)
    st.markdown('<div class="section-header">Dynamic Market Sensitivity: Rolling Beta vs ΔVIX</div>', unsafe_allow_html=True)

    if 'VIX_chg' in rg.columns and 'SP500_ret' in rg.columns:
        reg_aligned = rg[['SP500_ret','VIX_chg']].dropna()
        roll_beta = pd.Series(index=reg_aligned.index, dtype=float)
        w = rolling_window
        for i in range(w, len(reg_aligned)):
            sl = reg_aligned.iloc[i-w:i]
            try:
                b = sm.OLS(sl['SP500_ret'], sm.add_constant(sl['VIX_chg'])).fit().params.get('VIX_chg', np.nan)
                roll_beta.iloc[i] = b
            except:
                pass

        fig_rb = go.Figure()
        rb = roll_beta.dropna()
        fig_rb.add_trace(go.Scatter(
            x=rb.index, y=rb, name='Rolling Beta (S&P ~ ΔVIX)',
            line=dict(color='#a855f7', width=1.8),
            fill='tozeroy', fillcolor='rgba(168,85,247,0.1)'
        ))
        fig_rb.add_hline(y=0, line_color='white', line_width=0.5)
        fig_rb.update_layout(
            title=f'Rolling {rolling_window}-Day Beta: S&P 500 Return ~ ΔVIX<br>'
                  f'<sup>Negative = inverse relationship; larger magnitude = stronger sensitivity</sup>',
            yaxis_title='Beta Coefficient',
            height=320, showlegend=False, **PLOTLY_THEME
        )
        st.plotly_chart(fig_rb, use_container_width=True)

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.markdown("""
<div style="text-align:center; color:#b8c5d6; font-size:0.82rem; padding:12px 0;">
    S&P 500 Multi-Factor Risk & Return Dashboard · ACC102 Mini Assignment (Track 4) ·
    Xi'an Jiaotong-Liverpool University · 2026<br>
    Data: Yahoo Finance (yfinance) · FRED (pandas-datareader) ·
    Analysis: Python (pandas, numpy, statsmodels, scipy) · Visualisation: Plotly / Streamlit<br>
    ⚠️ This dashboard is for educational purposes only and does not constitute investment advice.
</div>
""", unsafe_allow_html=True)
