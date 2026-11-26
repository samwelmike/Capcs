import base64
import html
import json
import os
import sqlite3
import time
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st


#  THEMES (all color palettes are defined here)

THEMES = {
    "Navy Blue": dict(
        p="#1b2a5c", p2="#2b49a8", edge="#101a40", shadow="rgba(16,26,64,.35)",
        side="#1b2a5c", sb1="#34509f", sb2="#263f86", sbe="#121d45", hov1="#3f5fb8", hov2="#2c4a9c",
        act1="#3d7bff", act2="#1f5fe0", acte="#123a99", actt="#ffffff",
        acc="#1f5fe0", accd="#123a99", area="#7aa7ff", bg1="#eef2fb", bg2="#f7f9fe",
        ink="#1b2a5c", mut="#6b78a3", line="#e1e6f3", tbe="#c3cbe3",
        c1a="#eaf1ff", c1b="#c9dcff", c1e="#9db8ee", c1v="#1b2a5c",
        c2a="#e8f8ee", c2b="#c2ebd0", c2e="#93cfa9", c2v="#1d7a3a",
        c3a="#f0eaff", c3b="#d6c8fa", c3e="#b3a1e6", c3v="#3b1f8f"),
    "Orange & White": dict(
        p="#c2410c", p2="#fb923c", edge="#8f2f08", shadow="rgba(143,47,8,.35)",
        side="#b93a0a", sb1="#f97316", sb2="#ea580c", sbe="#8f2f08", hov1="#fb8a3c", hov2="#f06a12",
        act1="#ffffff", act2="#ffe6d2", acte="#d9a67f", actt="#9a3412",
        acc="#f97316", accd="#c2410c", area="#fdba74", bg1="#fff4ea", bg2="#fffaf5",
        ink="#7c2d12", mut="#a8744f", line="#f3dcc8", tbe="#efcfb6",
        c1a="#fff1e4", c1b="#ffd2a8", c1e="#eaa56e", c1v="#9a3412",
        c2a="#fffbea", c2b="#ffeaa3", c2e="#e0c866", c2v="#a16207",
        c3a="#ffece6", c3b="#ffc9b5", c3e="#e89a7f", c3v="#b42318"),
    "Gold & White": dict(
        p="#8a6508", p2="#d4a017", edge="#5e4505", shadow="rgba(94,69,5,.35)",
        side="#7a5806", sb1="#d4a017", sb2="#b8860b", sbe="#5e4505", hov1="#e0b030", hov2="#c8940f",
        act1="#ffffff", act2="#fff3cc", acte="#d9c27a", actt="#6b4e06",
        acc="#d4a017", accd="#8a6508", area="#f3d77a", bg1="#fbf6e6", bg2="#fffdf5",
        ink="#5e4505", mut="#9a8446", line="#efe3b8", tbe="#e6d7a0",
        c1a="#fff8e1", c1b="#fde9a5", c1e="#e0c35f", c1v="#7a5a07",
        c2a="#fffdf0", c2b="#fbf0b8", c2e="#dccf7c", c2v="#8a6d00",
        c3a="#fdf3e0", c3b="#f7dcae", c3e="#dfbb82", c3v="#8a5a0a"),
    "Black & White": dict(
        p="#111111", p2="#3a3a3a", edge="#000000", shadow="rgba(0,0,0,.4)",
        side="#111111", sb1="#3a3a3a", sb2="#262626", sbe="#000000", hov1="#4a4a4a", hov2="#333333",
        act1="#ffffff", act2="#e6e6e6", acte="#9a9a9a", actt="#111111",
        acc="#222222", accd="#000000", area="#9a9a9a", bg1="#eeeeee", bg2="#fafafa",
        ink="#111111", mut="#707070", line="#dddddd", tbe="#cfcfcf",
        c1a="#f7f7f7", c1b="#dcdcdc", c1e="#b0b0b0", c1v="#111111",
        c2a="#ffffff", c2b="#e8e8e8", c2e="#bdbdbd", c2v="#222222",
        c3a="#f0f0f0", c3b="#d0d0d0", c3e="#a5a5a5", c3v="#333333"),
}


#  SETTINGS (persisted in settings.json)

SETTINGS_FILE = "settings.json"
DEFAULTS = {
    "theme": "Navy Blue",
    "church_name": "AIC Chang'ombe",
    "tagline": "Together in Worship",
    "refresh": 5,
    "capacity": 500,
}
REFRESH_OPTIONS = [3, 5, 10, 30]


def load_settings():
    settings = DEFAULTS.copy()
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            settings.update(json.load(f))
    except Exception:
        pass
    if settings["theme"] not in THEMES:
        settings["theme"] = DEFAULTS["theme"]
    return settings


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


settings = load_settings()
palette = THEMES[settings["theme"]]
church_name_safe = html.escape(str(settings["church_name"]))
tagline_safe = html.escape(str(settings["tagline"]))

st.set_page_config(
    page_title=f"{settings['church_name']} Live",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Expose theme tokens as CSS custom properties
css_vars = "".join(f"--{k}:{v};" for k, v in palette.items())
st.markdown(f"<style>:root{{{css_vars}}}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
.stApp {background:linear-gradient(180deg,var(--bg1) 0%,var(--bg2) 100%); color:var(--ink);}
header[data-testid="stHeader"] {background:transparent; height:0;}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none;}
[data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {
    position:fixed; top:14px; left:14px; z-index:999999;
    background:rgba(255,255,255,.18); border-radius:12px; padding:4px;
    box-shadow:0 4px 0 rgba(0,0,0,.28);
}
[data-testid="collapsedControl"] *, [data-testid="stSidebarCollapsedControl"] *, [data-testid="stExpandSidebarButton"] * {color:white !important;}
.block-container {padding:0 2rem 1rem 2rem; max-width:100%;}
div[data-testid="stVerticalBlock"] {gap:0.9rem;}
div[data-testid="stWidgetLabel"] p, .stApp label p {color:var(--ink) !important; font-weight:600;}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background:var(--side);
    transform:none !important; margin-left:0 !important;
    visibility:visible !important;
    min-width:260px !important; width:260px !important;
}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarHeader"] button {display:none !important;}
section[data-testid="stSidebar"] * {color:white !important;}
section[data-testid="stSidebar"] div[role="radiogroup"] {gap:16px; margin-top:18px;}
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    width:100%; padding:14px 18px; border-radius:14px;
    background:linear-gradient(180deg,var(--sb1) 0%,var(--sb2) 100%);
    border:1px solid rgba(255,255,255,0.15);
    box-shadow:0 6px 0 var(--sbe), 0 12px 18px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.25);
    transition:all .15s ease; cursor:pointer;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {display:none !important;}
section[data-testid="stSidebar"] div[role="radiogroup"] label p {font-size:17px; font-weight:700; margin:0; letter-spacing:.3px;}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    transform:translateY(-2px);
    background:linear-gradient(180deg,var(--hov1) 0%,var(--hov2) 100%);
    box-shadow:0 8px 0 var(--sbe), 0 16px 22px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.3);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    transform:translateY(4px);
    background:linear-gradient(180deg,var(--act1) 0%,var(--act2) 100%);
    box-shadow:0 2px 0 var(--acte), 0 4px 10px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.5);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {color:var(--actt) !important;}
.logo-box {text-align:center; margin-top:10px;}
.logo-box img {width:110px; height:110px;}
.logo-box h4 {margin:6px 0 0 0;}

/* ---------- Topbar ---------- */
.topbar {
    background:linear-gradient(135deg,var(--p) 0%,var(--p2) 100%);
    color:white; padding:18px 32px; margin:0 -2rem 26px -2rem;
    border-radius:0 0 24px 24px;
    box-shadow:0 8px 0 var(--edge), 0 16px 28px var(--shadow);
    display:flex; justify-content:space-between; align-items:center;
}
.topbar h1 {margin:0; padding:0; font-size:26px; color:white; line-height:1.2; letter-spacing:.3px;
            text-shadow:0 2px 4px rgba(0,0,0,.35);}
.topbar i {opacity:.9; font-size:14px;}
.topbar .chips {display:flex; gap:14px;}
.topbar .chip {
    background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.28);
    border-radius:999px; padding:10px 20px; font-size:15px; font-weight:700;
    box-shadow:0 4px 0 rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.3);
}

/* ---------- Top KPI Cards ---------- */
.card {
    border-radius:20px; padding:16px 22px; height:132px; margin-bottom:10px; box-sizing:border-box;
    display:flex; align-items:center; gap:18px; transition:all .18s ease;
    border:1px solid rgba(255,255,255,.7);
}
.card:hover {transform:translateY(-4px);}
.card .ico {
    width:60px; height:60px; min-width:60px; border-radius:16px; background:white;
    display:flex; align-items:center; justify-content:center; font-size:30px;
    box-shadow:0 5px 0 rgba(0,0,0,.12), inset 0 1px 0 #fff;
}
.card .lbl {font-size:14px; font-weight:700; color:var(--ink); opacity:.8; text-transform:uppercase; letter-spacing:.6px;}
.card .val {font-size:32px; font-weight:800; line-height:1.15; white-space:nowrap;}
.card .sub {font-size:13px; font-weight:600; opacity:.85;}
.c-1 {background:linear-gradient(145deg,var(--c1a) 0%,var(--c1b) 100%); box-shadow:0 8px 0 var(--c1e), 0 16px 24px var(--shadow);}
.c-2 {background:linear-gradient(145deg,var(--c2a) 0%,var(--c2b) 100%); box-shadow:0 8px 0 var(--c2e), 0 16px 24px var(--shadow);}
.c-3 {background:linear-gradient(145deg,var(--c3a) 0%,var(--c3b) 100%); box-shadow:0 8px 0 var(--c3e), 0 16px 24px var(--shadow);}

/* ---------- Containers (charts & forms) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stForm"] {
    background:white; border:1px solid var(--line) !important; border-radius:22px;
    padding:8px 14px 4px 14px;
    box-shadow:0 8px 0 var(--tbe), 0 18px 28px var(--shadow);
    margin-bottom:10px;
}
.ttl {font-size:18px; font-weight:800; color:var(--ink); margin:0;}
.ttl-sub {font-size:13px; color:var(--mut); margin:0 0 4px 0;}

/* ---------- Bottom Summary Tiles ---------- */
.bottom {display:flex; gap:22px; margin-top:6px;}
.tile {
    flex:1; text-align:center; background:white; border-radius:20px; padding:16px 10px 14px 10px;
    border:1px solid var(--line); transition:all .18s ease;
}
.tile:hover {transform:translateY(-4px);}
.tile .lbl {font-size:14px; font-weight:700; color:var(--ink); opacity:.8; text-transform:uppercase; letter-spacing:.6px;}
.tile .val {font-size:36px; font-weight:800; line-height:1.15;}
.t-navy  {border-top:6px solid var(--p); box-shadow:0 7px 0 var(--tbe), 0 16px 24px var(--shadow);}
.t-green {border-top:6px solid #1d7a3a; box-shadow:0 7px 0 #b5dcc2, 0 16px 24px rgba(29,122,58,.18);}
.t-red   {border-top:6px solid #c0152b; box-shadow:0 7px 0 #eab4bc, 0 16px 24px rgba(192,21,43,.18);}

/* ---------- Capacity Bar ---------- */
.cap {background:white; border:1px solid var(--line); border-radius:20px; padding:16px 22px; margin-top:22px;
      box-shadow:0 7px 0 var(--tbe), 0 16px 24px var(--shadow);}
.cap-top {display:flex; justify-content:space-between; font-weight:700; color:var(--ink); margin-bottom:10px;}
.cap-bar {height:20px; border-radius:999px; background:#e9edf6; box-shadow:inset 0 3px 6px rgba(0,0,0,.18); overflow:hidden;}
.cap-fill {height:100%; border-radius:999px; box-shadow:inset 0 2px 0 rgba(255,255,255,.45);}
.cap-warn {margin-top:10px; font-weight:700;}

/* ---------- Theme Swatches (Settings) ---------- */
.swrow {display:flex; gap:16px; margin:6px 0 14px 0;}
.sw {flex:1; background:white; border:3px solid transparent; border-radius:16px; padding:10px; text-align:center;
     box-shadow:0 5px 0 var(--tbe);}
.sw.on {border-color:var(--acc);}
.sw-c {height:34px; border-radius:10px; margin-bottom:6px; box-shadow:inset 0 2px 0 rgba(255,255,255,.35);}
.sw span {font-weight:700; color:var(--ink); font-size:14px;}

/* ---------- Action Buttons ---------- */
div[data-testid="stFormSubmitButton"] button, div[data-testid="stDownloadButton"] button {
    background:linear-gradient(180deg,var(--acc) 0%,var(--accd) 100%); color:white; font-weight:700;
    border:none; border-radius:14px; padding:10px 22px;
    box-shadow:0 5px 0 var(--edge), 0 10px 16px var(--shadow); transition:all .15s ease;
}
div[data-testid="stFormSubmitButton"] button p, div[data-testid="stDownloadButton"] button p {color:white !important;}
div[data-testid="stFormSubmitButton"] button:hover, div[data-testid="stDownloadButton"] button:hover {
    transform:translateY(-2px); color:white; border:none;
}
div[data-testid="stFormSubmitButton"] button:active, div[data-testid="stDownloadButton"] button:active {
    transform:translateY(3px); box-shadow:0 2px 0 var(--edge);
}
</style>
""", unsafe_allow_html=True)

#  Sidebar 
if os.path.exists("logo.png"):
    with open("logo.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}">'
else:
    logo_html = "<h2 style='margin:0'>⛪</h2>"

st.sidebar.markdown(
    f'<div class="logo-box">{logo_html}<h4>{church_name_safe}</h4></div><hr>',
    unsafe_allow_html=True,
)
selected_page = st.sidebar.radio(
    "Menu",
    ["🏠 Dashboard", "📊 Reports", "⚙️ Settings"],
    label_visibility="collapsed",
)

#  Attendance Data 
try:
    conn = sqlite3.connect("church_attendance.db")
    logs_df = pd.read_sql_query("SELECT * FROM attendance_logs", conn)
    conn.close()
except Exception:
    logs_df = pd.DataFrame()

current_time = datetime.now()
st.markdown(
    f"""<div class="topbar"><div><h1>Automatic People Counting System</h1>
<i>{tagline_safe}</i></div>
<div class="chips"><div class="chip">📅 {current_time.strftime('%a, %b %d, %Y')}</div>
<div class="chip">🕒 {current_time.strftime('%I:%M %p')}</div></div></div>""",
    unsafe_allow_html=True,
)


#  SETTINGS PAGE

if selected_page == "⚙️ Settings":
    st.markdown(
        '<div class="ttl">⚙️ Settings</div>'
        '<div class="ttl-sub">Customize appearance and system preferences</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.pop("saved", False):
        st.success("✅ Settings saved.")

    swatches = "".join(
        f'<div class="sw{" on" if theme_name == settings["theme"] else ""}">'
        f'<div class="sw-c" style="background:linear-gradient(135deg,{theme_cfg["p"]},{theme_cfg["p2"]})"></div>'
        f"<span>{theme_name}</span></div>"
        for theme_name, theme_cfg in THEMES.items()
    )
    st.markdown(f'<div class="swrow">{swatches}</div>', unsafe_allow_html=True)

    with st.form("settings_form"):
        theme_choice = st.radio(
            "🎨 Theme",
            list(THEMES),
            index=list(THEMES).index(settings["theme"]),
            horizontal=True,
        )
        col_name, col_tag = st.columns(2)
        church_input = col_name.text_input("⛪ Church name", settings["church_name"])
        tagline_input = col_tag.text_input("✍️ Tagline", settings["tagline"])

        col_refresh, col_cap = st.columns(2)
        refresh_idx = REFRESH_OPTIONS.index(settings["refresh"]) if settings["refresh"] in REFRESH_OPTIONS else 1
        refresh_input = col_refresh.selectbox("⏱️ Auto-refresh interval (seconds)", REFRESH_OPTIONS, index=refresh_idx)
        capacity_input = col_cap.number_input(
            "👥 Church seating capacity",
            min_value=10,
            max_value=100000,
            value=int(settings["capacity"]),
            step=10,
        )

        if st.form_submit_button("💾 Save settings"):
            settings.update({
                "theme": theme_choice,
                "church_name": church_input.strip() or DEFAULTS["church_name"],
                "tagline": tagline_input.strip(),
                "refresh": int(refresh_input),
                "capacity": int(capacity_input),
            })
            save_settings(settings)
            st.session_state["saved"] = True
            st.rerun()
    st.stop()


#  REPORTS PAGE

if selected_page == "📊 Reports":
    st.markdown(
        '<div class="ttl">📊 Attendance Reports</div>'
        '<div class="ttl-sub">Browse past records and download them</div>',
        unsafe_allow_html=True,
    )
    if logs_df.empty:
        st.info("No records available yet. Reports will appear once the system starts counting people.")
        st.stop()

    logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])
    min_date = logs_df["timestamp"].dt.date.min()
    max_date = logs_df["timestamp"].dt.date.max()
    date_range = st.date_input(
        "📅 Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, (tuple, list)):
        start_date, end_date = date_range[0], date_range[-1]
    else:
        start_date = end_date = date_range

    filtered_df = logs_df[
        (logs_df["timestamp"].dt.date >= start_date) & (logs_df["timestamp"].dt.date <= end_date)
    ]
    if filtered_df.empty:
        st.warning("No records found for the selected dates.")
        st.stop()

    daily_summary = (
        filtered_df.groupby(filtered_df["timestamp"].dt.date)
        .agg(
            Peak=("current_inside", "max"),
            Total_In=("in_count", "max"),
            Total_Out=("out_count", "max"),
        )
        .reset_index()
        .rename(columns={"timestamp": "Date"})
    )

    st.markdown(
        f"""<div class="bottom">
<div class="tile t-navy"><div class="lbl">📆 Days</div><div class="val" style="color:{palette['ink']}">{len(daily_summary)}</div></div>
<div class="tile t-green"><div class="lbl">➡️ Total In</div><div class="val" style="color:#1d7a3a">{int(daily_summary['Total_In'].sum())}</div></div>
<div class="tile t-red"><div class="lbl">⬅️ Total Out</div><div class="val" style="color:#c0152b">{int(daily_summary['Total_Out'].sum())}</div></div>
<div class="tile t-navy"><div class="lbl">🔝 Highest Peak</div><div class="val" style="color:{palette['ink']}">{int(daily_summary['Peak'].max())}</div></div>
</div>""",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="ttl">📈 Peak attendance per day</div>', unsafe_allow_html=True)
        bars = (
            alt.Chart(daily_summary)
            .mark_bar(color=palette["acc"], cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("Date:T", title=None, axis=alt.Axis(format="%d %b", labelPadding=8)),
                y=alt.Y("Peak:Q", title=None, axis=alt.Axis(format="d", tickMinStep=1)),
                tooltip=[
                    alt.Tooltip("Date:T", format="%d %b %Y"),
                    alt.Tooltip("Peak:Q", title="Peak people", format="d"),
                ],
            )
            .properties(height=240)
            .configure(background="#ffffff")
            .configure_view(strokeWidth=0)
            .configure_axis(
                labelColor=palette["ink"],
                labelFontSize=12,
                gridColor="#e6ebf7",
                domain=False,
                tickSize=0,
            )
        )
        st.altair_chart(bars, width="stretch", theme=None)

    st.markdown('<div class="ttl">🗓️ Daily summary</div>', unsafe_allow_html=True)
    st.dataframe(daily_summary, width="stretch", hide_index=True)

    with st.expander("📋 View all event logs"):
        st.dataframe(filtered_df, width="stretch", hide_index=True)

    st.download_button(
        "⬇️ Download CSV (Excel)",
        filtered_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"attendance_{start_date}_to_{end_date}.csv",
        mime="text/csv",
    )
    st.stop()


#  DASHBOARD

current_inside = total_in = total_out = 0
peak_time, peak_count, trend_label, hourly_df = "--", 0, "Stable", pd.DataFrame()

if not logs_df.empty:
    logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])
    latest_row = logs_df.iloc[-1]
    current_inside = int(latest_row["current_inside"])
    total_in = int(latest_row["in_count"])
    total_out = int(latest_row["out_count"])

    hourly_df = (
        logs_df.set_index("timestamp")["current_inside"]
        .resample("60min")
        .max()
        .dropna()
        .reset_index()
    )
    peak_idx = hourly_df["current_inside"].idxmax()
    peak_time = hourly_df["timestamp"][peak_idx].strftime("%I:%M %p")
    peak_count = int(hourly_df["current_inside"][peak_idx])

    if len(hourly_df) >= 2:
        delta = hourly_df["current_inside"].iloc[-1] - hourly_df["current_inside"].iloc[-2]
        if delta > 0:
            trend_label = "Rising"
        elif delta < 0:
            trend_label = "Falling"
        else:
            trend_label = "Stable"

trend_icon = {"Rising": "▲", "Falling": "▼", "Stable": "▬"}[trend_label]
trend_color = {"Rising": "#1d7a3a", "Falling": "#c0152b", "Stable": palette["c3v"]}[trend_label]

#  Top Summary Cards
col1, col2, col3 = st.columns(3, gap="large")
col1.markdown(
    f"""<div class="card c-1"><div class="ico">👥</div>
<div><div class="lbl">Total Attendance</div>
<div class="val" style="color:{palette['c1v']}">{total_in}</div></div></div>""",
    unsafe_allow_html=True,
)
col2.markdown(
    f"""<div class="card c-2"><div class="ico">🕒</div>
<div><div class="lbl">Peak Time</div>
<div class="val" style="color:{palette['c2v']}">{peak_time}</div>
<div class="sub" style="color:{palette['c2v']}">({peak_count} People)</div></div></div>""",
    unsafe_allow_html=True,
)
col3.markdown(
    f"""<div class="card c-3"><div class="ico">📈</div>
<div><div class="lbl">Today's Trend</div>
<div class="val" style="color:{trend_color}">{trend_icon} {trend_label}</div></div></div>""",
    unsafe_allow_html=True,
)

# ---------- Hourly Trend Chart ----------
with st.container(border=True):
    st.markdown(
        '<div class="ttl">📈 Attendance Trend</div>'
        '<div class="ttl-sub">People inside the church, per hour</div>',
        unsafe_allow_html=True,
    )
    if hourly_df.empty:
        st.info("The chart will appear once the system starts counting people.")
    else:
        y_max = max(5, int(hourly_df["current_inside"].max()) + 1)
        base_chart = alt.Chart(hourly_df).encode(
            x=alt.X("timestamp:T", title=None, axis=alt.Axis(format="%-I%p", labelPadding=8)),
            y=alt.Y(
                "current_inside:Q",
                title=None,
                scale=alt.Scale(domain=[0, y_max]),
                axis=alt.Axis(format="d", tickMinStep=1, labelPadding=8),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%I:%M %p"),
                alt.Tooltip("current_inside:Q", title="People", format="d"),
            ],
        )
        area_layer = base_chart.mark_area(
            line={"color": palette["acc"], "strokeWidth": 3},
            interpolate="monotone",
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#ffffff", offset=0),
                    alt.GradientStop(color=palette["area"], offset=1),
                ],
                x1=1, x2=1, y1=1, y2=0,
            ),
        )
        point_layer = base_chart.mark_point(
            color=palette["acc"],
            size=110,
            filled=True,
            opacity=1,
            stroke="white",
            strokeWidth=2.5,
        )
        trend_chart = (
            (area_layer + point_layer)
            .properties(height=250)
            .configure(background="#ffffff")
            .configure_view(strokeWidth=0)
            .configure_axis(
                labelColor=palette["ink"],
                labelFontSize=12,
                labelFontWeight=600,
                gridColor="#e6ebf7",
                domain=False,
                tickSize=0,
            )
        )
        st.altair_chart(trend_chart, width="stretch", theme=None)

# ---------- Bottom Counter Tiles ----------
st.markdown(
    f"""<div class="bottom">
<div class="tile t-navy"><div class="lbl">👥 Currently In Church</div><div class="val" style="color:{palette['ink']}">{current_inside}</div></div>
<div class="tile t-green"><div class="lbl">➡️ Total In</div><div class="val" style="color:#1d7a3a">{total_in}</div></div>
<div class="tile t-red"><div class="lbl">⬅️ Total Out</div><div class="val" style="color:#c0152b">{total_out}</div></div>
</div>""",
    unsafe_allow_html=True,
)

# ---------- Capacity Meter ----------
capacity_limit = max(1, int(settings["capacity"]))
occupancy_pct = min(100.0, current_inside / capacity_limit * 100)
if occupancy_pct < 70:
    bar_color = "#1d7a3a"
elif occupancy_pct < 90:
    bar_color = "#e8a317"
else:
    bar_color = "#c0152b"

if occupancy_pct >= 100:
    capacity_warning = "<div class='cap-warn' style='color:#c0152b'>⚠️ Church is at full capacity!</div>"
elif occupancy_pct >= 90:
    capacity_warning = "<div class='cap-warn' style='color:#c0152b'>⚠️ Church is nearing capacity.</div>"
else:
    capacity_warning = ""

st.markdown(
    f"""<div class="cap"><div class="cap-top"><span>⛪ Capacity</span>
<span>{current_inside} / {capacity_limit} ({occupancy_pct:.0f}%)</span></div>
<div class="cap-bar"><div class="cap-fill" style="width:{occupancy_pct}%; background:{bar_color}"></div></div>{capacity_warning}</div>""",
    unsafe_allow_html=True,
)

# Refresh dashboard at the configured interval
time.sleep(int(settings["refresh"]))
st.rerun()