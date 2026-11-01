"""Reusable visual components and page chrome."""
from __future__ import annotations

import html
from typing import Any, Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import theme
from .config import COLORS, PLOTLY_CONFIG, STATE_NAMES
from .filters import AnalysisContext

_CSS_TEMPLATE = """
<style>
:root {
    __TOKENS__
    --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    --radius-xs: 6px;
    --radius-sm: 10px;
    --radius-md: 14px;
    --radius-lg: 18px;
    --radius-xl: 22px;
    --transition-fast: 0.15s cubic-bezier(0.16, 1, 0.3, 1);
    --transition-smooth: 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}
*, *::before, *::after {
    box-sizing: border-box;
}
html, body, .stApp, [class*="css"] {
    font-family: var(--font-sans);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}
body {
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 0;
}
html, body, .stApp, [data-testid="stAppViewContainer"] {
    max-width: 100vw;
    overflow-x: hidden;
}
.stApp {
    background: var(--bg);
    color: var(--text);
}
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1200px 600px at 100% 0%, var(--glow-1), transparent 60%),
        radial-gradient(1000px 500px at 0% 0%, var(--glow-2), transparent 55%),
        var(--bg);
    background-attachment: fixed;
}
header[data-testid="stHeader"] {
    background: color-mix(in srgb, var(--bg) 82%, transparent) !important;
    backdrop-filter: saturate(160%) blur(16px) !important;
    -webkit-backdrop-filter: saturate(160%) blur(16px) !important;
    border-bottom: 1px solid var(--line) !important;
    z-index: 9999 !important;
}
#MainMenu, footer { visibility: hidden; }
/* The Deploy control is developer chrome and collides with the theme
   switch at narrow widths. Hide it while leaving the main menu usable. */
header[data-testid="stHeader"] button[aria-label="Deploy"],
header[data-testid="stHeader"] [data-testid="stAppDeployButton"] {
    display: none !important;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 3.5rem;
    max-width: 1440px;
}

/* ---------------------------------------------------------- sidebar */
[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] > div { background: transparent; }
[data-testid="stSidebar"] .block-container {
    padding: 1.25rem 1rem 2rem;
}
[data-testid="stSidebarNav"] { padding-top: .3rem; }
[data-testid="stSidebarNav"] ul { gap: .2rem; }
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNavLink"] {
    border-radius: var(--radius-sm);
    padding: .52rem .75rem;
    color: var(--text);
    font-size: .84rem;
    font-weight: 500;
    transition: all var(--transition-fast);
    display: flex;
    align-items: center;
}
[data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebarNavLink"]:hover {
    background: var(--surface-tint);
    color: var(--ink);
    transform: translateX(2px);
}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: var(--brand-soft);
    color: var(--brand);
    font-weight: 650;
    box-shadow: inset 3px 0 0 var(--brand);
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: var(--muted);
    font-size: .75rem;
    font-weight: 650;
    letter-spacing: .02em;
}

/* ------------------------------------------------------ theme switch */
.st-key-theme_switch {
    position: fixed;
    top: .56rem;
    right: 4.8rem;
    z-index: 100000;
    width: auto;
}
.st-key-theme_switch [data-testid="stWidgetLabel"] { display: none; }
.st-key-theme_switch [data-testid="stSegmentedControl"] {
    background: var(--surface);
    border: 1px solid var(--line-strong);
    border-radius: 9999px;
    padding: 3px;
    box-shadow: var(--shadow-sm);
    display: inline-flex;
    align-items: center;
}
.st-key-theme_switch [data-testid="stSegmentedControl"] > div { gap: 2px; }
.st-key-theme_switch button {
    border: 0 !important;
    border-radius: 9999px !important;
    background: transparent !important;
    color: var(--muted) !important;
    box-shadow: none !important;
    font-size: .75rem !important;
    font-weight: 600 !important;
    padding: .3rem .68rem !important;
    transition: all var(--transition-fast) !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
    cursor: pointer !important;
}
.st-key-theme_switch button:hover {
    background: var(--surface-tint) !important;
    color: var(--ink) !important;
}
.st-key-theme_switch button[aria-checked="true"],
.st-key-theme_switch button[aria-pressed="true"],
.st-key-theme_switch button[data-testid*="Active"] {
    background: var(--brand) !important;
    color: var(--brand-contrast) !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 10px color-mix(in srgb, var(--brand) 38%, transparent) !important;
}

/* ------------------------------------------------------------ brand */
.app-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0 0 .9rem 0;
    padding: .2rem 0 .8rem;
    border-bottom: 1px solid var(--line);
}
.brand-mark {
    width: 36px; height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--brand), var(--violet));
    color: #FFFFFF;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 16px;
    box-shadow: 0 4px 14px color-mix(in srgb, var(--brand) 32%, transparent);
    flex-shrink: 0;
}
.brand-title {
    font-weight: 700; color: var(--ink); font-size: 14.5px;
    line-height: 1.2; letter-spacing: -.02em;
}
.brand-sub {
    color: var(--muted); font-size: 11px; margin-top: 2px;
    font-weight: 500;
}
.sidebar-label {
    font-size: 10px; letter-spacing: .12em; text-transform: uppercase;
    color: var(--faint); font-weight: 700; margin: 1.2rem 0 .4rem;
}

/* ------------------------------------------------------------- hero */
.hero {
    position: relative;
    overflow: hidden;
    border-radius: var(--radius-xl);
    padding: 30px 32px 28px;
    color: var(--hero-ink);
    background:
        radial-gradient(circle at 92% 12%, var(--hero-glow-1), transparent 36%),
        radial-gradient(circle at 75% 105%, var(--hero-glow-2), transparent 44%),
        linear-gradient(135deg, var(--hero-from) 0%, var(--hero-via) 52%, var(--hero-to) 100%);
    border: 1px solid var(--line);
    box-shadow: var(--shadow-md);
    margin-bottom: 1.25rem;
}
.hero::after {
    content: "";
    position: absolute; right: -80px; top: -110px;
    width: 300px; height: 300px; border-radius: 50%;
    border: 1px solid color-mix(in srgb, var(--brand) 20%, transparent);
    pointer-events: none;
}
.hero-eyebrow {
    font-size: 10.5px; letter-spacing: .16em; text-transform: uppercase;
    color: var(--brand); font-weight: 750; margin-bottom: 8px;
    display: inline-block;
}
.hero h1 {
    font-size: 32px; line-height: 1.15; margin: 0 0 8px;
    color: var(--hero-ink); letter-spacing: -.03em; font-weight: 750;
}
.hero p {
    margin: 0; max-width: 820px; color: var(--hero-text);
    font-size: 13.5px; line-height: 1.6; font-weight: 450;
}
.hero-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.hero-chip {
    background: var(--hero-chip-bg);
    border: 1px solid var(--hero-chip-border);
    color: var(--hero-ink);
    border-radius: 9999px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 600;
    backdrop-filter: blur(8px);
    box-shadow: 0 1px 3px rgba(0, 0, 0, .04);
    font-variant-numeric: tabular-nums;
}

/* -------------------------------------------------------- page head */
.page-head {
    position: relative;
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    padding: 24px 26px 22px;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-sm);
}
.page-head::before {
    content: "";
    position: absolute; left: 26px; top: 0;
    width: 48px; height: 3px;
    border-radius: 0 0 9999px 9999px;
    background: linear-gradient(90deg, var(--brand), var(--violet));
}
.page-head::after {
    content: "";
    position: absolute; right: -40px; top: -60px;
    width: 200px; height: 200px; border-radius: 50%;
    background: radial-gradient(circle, var(--glow-1), transparent 70%);
    pointer-events: none;
}
.page-eyebrow {
    font-size: 10px; letter-spacing: .14em; text-transform: uppercase;
    color: var(--brand); font-weight: 750; margin-bottom: 6px;
}
.page-head h1 {
    font-size: 26px; line-height: 1.2; margin: 0 0 6px;
    color: var(--ink); letter-spacing: -.025em; font-weight: 750;
}
.page-head p {
    margin: 0; color: var(--muted); font-size: 13px; line-height: 1.55;
}

/* --------------------------------------------------------- filters */
.filter-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; margin: 0 0 1.15rem 0; }
.filter-chip {
    background: var(--surface); border: 1px solid var(--line); color: var(--muted);
    border-radius: 9999px; padding: 5px 11px; font-size: 11px; font-weight: 550;
    box-shadow: 0 1px 2px color-mix(in srgb, var(--ink) 4%, transparent);
    font-variant-numeric: tabular-nums;
}
.filter-chip strong { color: var(--ink); font-weight: 650; }
.filter-count { color: var(--brand); font-weight: 750; }

/* ------------------------------------------------------------- KPIs */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin: .25rem 0 1.3rem;
}
.kpi-card {
    --accent: var(--brand);
    position: relative;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 18px 18px 16px;
    min-height: 116px;
    box-shadow: var(--shadow-sm);
    transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kpi-card:hover {
    transform: translateY(-2px);
    border-color: color-mix(in srgb, var(--accent) 35%, var(--line));
    box-shadow: var(--shadow-md);
}
.kpi-top { display: flex; align-items: center; gap: 8px; }
.kpi-dot {
    width: 7px; height: 7px; flex: 0 0 7px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent);
}
.kpi-label {
    color: var(--muted); font-size: 10.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em;
}
.kpi-value {
    color: var(--ink); font-size: 26px; font-weight: 750;
    letter-spacing: -.03em; margin: 9px 0 3px; line-height: 1.1;
    font-variant-numeric: tabular-nums;
}
.kpi-sub { color: var(--faint); font-size: 11px; line-height: 1.45; }
.kpi-delta {
    display: inline-flex; align-items: center; width: fit-content;
    font-size: 10.5px; font-weight: 700; margin-top: 7px;
    padding: 2px 8px; border-radius: 9999px;
    font-variant-numeric: tabular-nums;
}
.kpi-delta.pos { color: var(--green); background: var(--green-soft); }
.kpi-delta.neg { color: var(--red); background: var(--red-soft); }
.kpi-delta.neutral { color: var(--muted); background: var(--surface-tint); }

/* ---------------------------------------------------------- sections */
.section-head { margin: 1.5rem 0 .65rem; }
.section-head h3 {
    font-size: 1.02rem; color: var(--ink); margin: 0; letter-spacing: -.015em;
    font-weight: 700;
}
.section-head h3::before {
    content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
    background: var(--brand); margin-right: 8px; vertical-align: middle;
}
.section-head p { margin: 4px 0 0 14px; color: var(--muted); font-size: .78rem; line-height: 1.5; }

/* ---------------------------------------------------------- callouts */
.callout {
    display: flex; gap: 12px; align-items: flex-start;
    border-radius: var(--radius-sm); padding: 13px 16px; margin: .7rem 0 1.1rem;
    border: 1px solid var(--line); background: var(--surface);
    color: var(--text); font-size: 12.5px; line-height: 1.6;
    box-shadow: var(--shadow-sm);
}
.callout-icon {
    width: 24px; height: 24px; flex: 0 0 24px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 800;
}
.callout.info { border-left: 3px solid var(--blue); }
.callout.info .callout-icon { background: var(--blue-soft); color: var(--blue); }
.callout.success { border-left: 3px solid var(--green); }
.callout.success .callout-icon { background: var(--green-soft); color: var(--green); }
.callout.warning { border-left: 3px solid var(--amber); }
.callout.warning .callout-icon { background: var(--amber-soft); color: var(--amber); }
.callout.danger { border-left: 3px solid var(--red); }
.callout.danger .callout-icon { background: var(--red-soft); color: var(--red); }
.callout strong { color: var(--ink); }

.empty-state {
    background: var(--surface); border: 1px dashed var(--line-strong); border-radius: var(--radius-md);
    padding: 44px 24px; text-align: center; color: var(--muted); margin: 1rem 0;
}
.empty-state h3 { color: var(--ink); margin: 0 0 6px; font-size: 1.05rem; font-weight: 700; }
.empty-state p { margin: 0; font-size: .82rem; }

/* ------------------------------------------------------------ notes */
.source-note {
    color: var(--faint); font-size: 11px; line-height: 1.55;
    border-top: 1px solid var(--line); padding-top: 10px; margin-top: 14px;
}
.source-note strong { color: var(--muted); font-weight: 600; }
.small-note { color: var(--faint); font-size: 11px; line-height: 1.45; }
.metric-inline {
    display: inline-flex; align-items: baseline; gap: 5px;
    background: var(--surface-tint); border: 1px solid var(--line);
    border-radius: var(--radius-xs); padding: 3px 8px; font-size: 11px; color: var(--muted);
}
.metric-inline strong { color: var(--ink); }
.footer-note {
    color: var(--faint); font-size: 11px; line-height: 1.55;
    border-top: 1px solid var(--line); padding-top: 14px; margin-top: 26px;
}

/* ---------------------------------------------------------- controls */
.stButton > button, .stDownloadButton > button {
    border-radius: var(--radius-sm);
    border: 1px solid var(--line-strong);
    background: var(--surface);
    color: var(--ink);
    font-weight: 600;
    font-size: .84rem;
    padding: .45rem .95rem;
    transition: all var(--transition-fast);
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: color-mix(in srgb, var(--brand) 55%, var(--line-strong));
    color: var(--brand);
    background: var(--brand-soft);
    box-shadow: 0 2px 10px color-mix(in srgb, var(--brand) 18%, transparent);
    transform: translateY(-1px);
}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
    outline: 2px solid color-mix(in srgb, var(--brand) 60%, transparent);
    outline-offset: 2px;
}
[data-testid="stDateInput"] input,
[data-testid="stTextInput"] input,
[data-baseweb="input"],
[data-baseweb="select"] > div {
    background: var(--surface) !important;
    border-color: var(--line-strong) !important;
    color: var(--ink) !important;
    border-radius: var(--radius-sm) !important;
    font-size: .84rem !important;
}
[data-baseweb="tag"] {
    background: var(--brand-soft) !important;
    color: var(--brand) !important;
    border-radius: 6px !important;
    font-weight: 550 !important;
}
[data-baseweb="tag"] span, [data-baseweb="tag"] svg { color: var(--brand) !important; }

/* -------------------------------- BaseWeb Calendar & Popovers (Fixed) */
div[data-baseweb="popover"] {
    background: var(--surface) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-lg) !important;
    color: var(--ink) !important;
    z-index: 100001 !important;
    overflow: visible !important;
}
div[data-baseweb="calendar"] {
    background: var(--surface) !important;
    color: var(--ink) !important;
    padding: 12px 14px !important;
    border-radius: var(--radius-md) !important;
    font-family: var(--font-sans) !important;
}
div[data-baseweb="calendar"] header {
    background: transparent !important;
    color: var(--ink) !important;
    border-bottom: 1px solid var(--line) !important;
    padding-bottom: 10px !important;
    margin-bottom: 8px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
}
/* Previous and Next Month navigation buttons */
div[data-baseweb="calendar"] header button {
    background: var(--surface-tint) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
    color: var(--ink) !important;
    cursor: pointer !important;
    pointer-events: auto !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 32px !important;
    height: 32px !important;
    transition: all var(--transition-fast) !important;
    opacity: 1 !important;
}
div[data-baseweb="calendar"] header button:hover:not(:disabled) {
    background: var(--brand-soft) !important;
    border-color: var(--brand) !important;
    color: var(--brand) !important;
}
div[data-baseweb="calendar"] header button:disabled {
    opacity: 0.3 !important;
    cursor: not-allowed !important;
}
div[data-baseweb="calendar"] header button svg {
    fill: var(--ink) !important;
    stroke: var(--ink) !important;
    width: 14px !important;
    height: 14px !important;
}
div[data-baseweb="calendar"] header button:hover:not(:disabled) svg {
    fill: var(--brand) !important;
    stroke: var(--brand) !important;
}
div[data-baseweb="calendar"] [data-baseweb="select"] > div {
    background: var(--surface-tint) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}
div[data-baseweb="calendar"] [role="grid"] {
    background: transparent !important;
}
/* Weekday row header */
div[data-baseweb="calendar"] [role="row"] > div {
    color: var(--muted) !important;
    font-size: 11px !important;
    font-weight: 650 !important;
    text-transform: uppercase !important;
}
/* Calendar day cells */
div[data-baseweb="calendar"] [role="gridcell"] {
    color: var(--ink) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: background var(--transition-fast) !important;
}
div[data-baseweb="calendar"] [role="gridcell"]:hover:not([aria-disabled="true"]) {
    background: var(--surface-tint) !important;
    color: var(--brand) !important;
}
div[data-baseweb="calendar"] [aria-selected="true"],
div[data-baseweb="calendar"] [data-highlighted="true"] {
    background: var(--brand) !important;
    color: var(--brand-contrast) !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
}
div[data-baseweb="calendar"] [data-range-middle="true"] {
    background: var(--brand-soft) !important;
    color: var(--brand) !important;
    border-radius: 0 !important;
}
div[data-baseweb="calendar"] [aria-disabled="true"] {
    color: var(--faint) !important;
    opacity: 0.35 !important;
    cursor: not-allowed !important;
}

/* -------------------------------- BaseWeb Multiselect / Select Dropdown */
[data-baseweb="menu"],
ul[role="listbox"] {
    background: var(--surface) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: var(--radius-sm) !important;
    box-shadow: var(--shadow-lg) !important;
    padding: 4px !important;
}
li[role="option"] {
    background: transparent !important;
    color: var(--ink) !important;
    border-radius: 6px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 10px !important;
    transition: all var(--transition-fast) !important;
}
li[role="option"]:hover,
li[role="option"][aria-selected="true"] {
    background: var(--brand-soft) !important;
    color: var(--brand) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--surface-tint);
    padding: 4px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--line);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 6px 14px;
    color: var(--muted);
    font-weight: 550;
    transition: all var(--transition-fast);
}
.stTabs [aria-selected="true"] {
    background: var(--surface);
    color: var(--ink);
    box-shadow: var(--shadow-sm);
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
[data-testid="stExpander"] details {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    transition: border-color var(--transition-fast);
}
[data-testid="stExpander"] details:hover {
    border-color: var(--line-strong);
}
[data-testid="stExpander"] summary { color: var(--muted); font-weight: 600; }
div[data-testid="stPlotlyChart"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 12px 12px 6px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow var(--transition-fast), border-color var(--transition-fast);
    max-width: 100%;
}
div[data-testid="stPlotlyChart"]:hover {
    border-color: var(--line-strong);
    box-shadow: var(--shadow-md);
}
div[data-testid="stDataFrame"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    max-width: 100%;
}
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb {
    background: color-mix(in srgb, var(--line-strong) 78%, transparent);
    border-radius: 9999px;
    border: 2px solid transparent;
    background-clip: padding-box;
}

/* -------------------------------------------------------- responsive */
@media (max-width: 1100px) {
    .block-container { padding-left: 1.4rem; padding-right: 1.4rem; }
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); }
}
@media (max-width: 760px) {
    .block-container { padding: 1.15rem .85rem 3rem; max-width: 100%; }
    .st-key-theme_switch { top: .52rem; right: 3.35rem; }
    .st-key-theme_switch button { font-size: .68rem !important; padding: .24rem .48rem !important; }
    .hero { padding: 22px 18px 20px; border-radius: 16px; }
    .hero h1 { font-size: 1.5rem; }
    .hero p { font-size: .82rem; }
    .page-head { padding: 20px 18px 18px; border-radius: 14px; }
    .page-head::before { left: 18px; }
    .page-head h1 { font-size: 1.35rem; }
    .page-head p { font-size: .78rem; }
    .kpi-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
    .kpi-card { padding: 14px; border-radius: 12px; min-height: 0; }
    .kpi-value { font-size: 1.35rem; margin-top: 6px; }
    .kpi-label { font-size: .62rem; }
    .kpi-sub { font-size: .68rem; }
    .section-head { margin-top: 1.25rem; }
    .section-head h3 { font-size: .94rem; }
    .section-head p { margin-left: 14px; font-size: .7rem; }
    .callout { padding: 12px 14px; font-size: .78rem; }
    .filter-chip { font-size: .65rem; padding: 4px 8px; }
    .source-note, .footer-note { font-size: .65rem; }
    div[data-testid="stPlotlyChart"] { border-radius: 12px; padding: 6px 4px 0; max-width: 100% !important; }
    div[data-testid="stPlotlyChart"] > div { max-width: 100% !important; }
    .js-plotly-plot, .plot-container { width: 100% !important; max-width: 100% !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: .75rem !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }
    .stTabs [data-baseweb="tab-list"] { overflow-x: auto; flex-wrap: nowrap; -webkit-overflow-scrolling: touch; }
    .stTabs [data-baseweb="tab"] { white-space: nowrap; padding: 6px 11px; }
    div[data-testid="stDataFrame"] { width: 100% !important; max-width: 100% !important; overflow-x: auto !important; }
}
@media (max-width: 480px) {
    .kpi-grid { grid-template-columns: 1fr; gap: 8px; }
    .hero-meta { gap: 5px; }
    .hero-chip { font-size: .62rem; padding: 4px 8px; }
    .st-key-theme_switch { top: .5rem; right: 3.1rem; }
    .st-key-theme_switch button { padding: .22rem .4rem !important; font-size: .65rem !important; }
}
</style>
"""


def inject_css(mode: str | None = None) -> None:
    """Inject the theme-aware stylesheet for the custom dashboard chrome."""
    active = theme.normalise_mode(mode or theme.current_mode())
    st.markdown(
        _CSS_TEMPLATE.replace("__TOKENS__", theme.css_variables(active)),
        unsafe_allow_html=True,
    )


def _theme_changed() -> None:
    """Persist the segmented-control choice before the next script run."""
    theme.set_mode(st.session_state.get("theme_control", theme.current_mode()))


def theme_control() -> None:
    """Render the sun/moon theme switch in the top-right corner."""
    active = theme.current_mode()
    with st.container(key="theme_switch"):
        st.segmented_control(
            "Colour theme",
            options=("light", "dark"),
            default=active,
            format_func=lambda value: "☀️  Light" if value == "light" else "🌙  Dark",
            key="theme_control",
            on_change=_theme_changed,
            label_visibility="collapsed",
            help="Switch between light and dark mode",
        )


def sidebar_brand() -> None:
    st.markdown(
        '<div class="app-brand">'
        '<div class="brand-mark">O</div>'
        '<div>'
        '<div class="brand-title">Olist Commerce</div>'
        '<div class="brand-sub">Analytics workspace</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def hero(eyebrow: str, title: str, subtitle: str, chips: Iterable[str] = ()) -> None:
    chip_html = "".join(f'<span class="hero-chip">{html.escape(str(chip))}</span>' for chip in chips)
    hero_html = (
        f'<div class="hero">'
        f'<div class="hero-eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1>{html.escape(title)}</h1>'
        f'<p>{html.escape(subtitle)}</p>'
        f'<div class="hero-meta">{chip_html}</div>'
        f'</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, eyebrow: str = "Analytics") -> None:
    header_html = (
        f'<div class="page-head">'
        f'<div class="page-eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1>{html.escape(title)}</h1>'
        f'<p>{html.escape(subtitle)}</p>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def kpi_cards(cards: list[dict[str, Any]]) -> None:
    """Render a responsive grid of compact KPI cards.

    Each card supports label, value, sub, delta, delta_tone, accent and help.
    """
    pieces = []
    for card in cards:
        tone = card.get("delta_tone", "neutral")
        delta = card.get("delta")
        delta_html = (
            f'<div class="kpi-delta {html.escape(tone)}">{html.escape(str(delta))}</div>'
            if delta
            else ""
        )
        title = html.escape(str(card.get("help", "")), quote=True)
        accent = html.escape(str(card.get("accent", COLORS["teal"])))
        label = html.escape(str(card.get("label", "")))
        value = html.escape(str(card.get("value", "—")))
        sub = html.escape(str(card.get("sub", "")))
        card_html = (
            f'<div class="kpi-card" style="--accent:{accent}" title="{title}">'
            f'<div class="kpi-top">'
            f'<span class="kpi-dot"></span>'
            f'<div class="kpi-label">{label}</div>'
            f'</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'{delta_html}'
            f'</div>'
        )
        pieces.append(card_html)
    grid_html = f'<div class="kpi-grid">{"".join(pieces)}</div>'
    st.markdown(grid_html, unsafe_allow_html=True)


def section(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="section-head"><h3>{html.escape(title)}</h3>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def callout(text: str, tone: str = "info", icon: str = "i") -> None:
    callout_html = (
        f'<div class="callout {html.escape(tone)}">'
        f'<div class="callout-icon">{html.escape(icon)}</div>'
        f'<div>{html.escape(text)}</div>'
        f'</div>'
    )
    st.markdown(callout_html, unsafe_allow_html=True)


def empty_state(title: str = "No data matches these filters", message: str | None = None) -> None:
    message = message or "Try widening the date range or clearing one of the sidebar filters."
    empty_html = (
        f'<div class="empty-state">'
        f'<h3>{html.escape(title)}</h3>'
        f'<p>{html.escape(message)}</p>'
        f'</div>'
    )
    st.markdown(empty_html, unsafe_allow_html=True)


def active_filter_bar(ctx: AnalysisContext) -> None:
    filters = ctx.filters
    start = filters.start_date.strftime("%d %b %Y") if filters.start_date else "Any"
    end = filters.end_date.strftime("%d %b %Y") if filters.end_date else "Any"
    statuses = ", ".join(filters.statuses) if filters.statuses else "All statuses"
    states = ", ".join(filters.states) if filters.states else "All states"
    categories = (
        f"{len(filters.categories)} selected" if filters.categories else "All categories"
    )
    orders = len(ctx.orders)
    bar_html = (
        f'<div class="filter-bar">'
        f'<span class="filter-chip"><strong>Period</strong>&nbsp; {html.escape(start)} → {html.escape(end)}</span>'
        f'<span class="filter-chip"><strong>Status</strong>&nbsp; {html.escape(statuses)}</span>'
        f'<span class="filter-chip"><strong>State</strong>&nbsp; {html.escape(states)}</span>'
        f'<span class="filter-chip"><strong>Category</strong>&nbsp; {html.escape(categories)}</span>'
        f'<span class="filter-chip"><strong>Orders</strong>&nbsp; <span class="filter-count">{orders:,}</span></span>'
        f'</div>'
    )
    st.markdown(bar_html, unsafe_allow_html=True)
    if ctx.notes:
        callout(" ".join(ctx.notes), tone="info", icon="i")


def plot(fig: go.Figure, height: int | None = None) -> None:
    if height:
        fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def show_table(
    frame: pd.DataFrame,
    column_config: dict[str, Any] | None = None,
    height: int | None = None,
    hide_index: bool = True,
) -> None:
    st.dataframe(
        frame,
        width="stretch",
        height=height,
        hide_index=hide_index,
        column_config=column_config or {},
    )


def download_csv(frame: pd.DataFrame, filename: str, label: str = "Download CSV") -> None:
    st.download_button(
        label,
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        width="content",
    )


def state_name(code: str) -> str:
    return STATE_NAMES.get(code, code)


def footer_note(source: str | None = None) -> None:
    st.markdown(
        '<div class="footer-note">Olist Brazilian E-Commerce public dataset · '
        "All figures are calculated from the source data.</div>",
        unsafe_allow_html=True,
    )
