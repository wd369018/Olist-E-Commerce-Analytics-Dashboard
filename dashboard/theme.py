"""Theme selection and shared design tokens.

The dashboard has a light and a dark presentation. Streamlit's native widgets
(calendar, selects, data grids) are themed through the ``[theme.light]`` and
``[theme.dark]`` sections in ``.streamlit/config.toml``. The active browser
theme is stored in Streamlit's own ``stActiveTheme`` localStorage key so native
widgets and the custom chrome always agree.

The selected mode is also kept in the URL query string. That makes it survive a
refresh, a bookmark and page navigation, and lets the Python process render the
matching CSS variables and Plotly theme on the very first paint.
"""
from __future__ import annotations

import json
from typing import Any, Literal

import streamlit as st

ThemeMode = Literal["light", "dark"]
THEME_QUERY_KEY = "theme"

# URL paths created by st.navigation. Keeping the browser theme in sync for
# every path means switching pages never falls back to the wrong native theme.
THEME_PATHS = (
    "/",
    "/executive",
    "/sales",
    "/customers",
    "/products",
    "/delivery",
    "/satisfaction",
    "/payments",
    "/data-quality",
)

LIGHT: dict[str, Any] = {
    "mode": "light",
    "label": "Light",
    "icon": ":material/light_mode:",
    "canvas": "#F7F7FB",
    "canvas_alt": "#F1F1F7",
    "surface": "#FFFFFF",
    "surface_soft": "#FAFAFC",
    "surface_raised": "#FFFFFF",
    "surface_tint": "#F4F4FA",
    "sidebar": "#FBFBFD",
    "ink": "#0F1117",
    "text": "#4B4B57",
    "muted": "#6F6F7E",
    "faint": "#9A9AA8",
    "line": "#E8E8F0",
    "line_strong": "#D4D4E0",
    "brand": "#635BFF",
    "brand_bright": "#7C74FF",
    "brand_soft": "#F1EFFF",
    "brand_contrast": "#FFFFFF",
    "blue": "#2563EB",
    "blue_soft": "#EFF4FF",
    "violet": "#8B5CF6",
    "violet_soft": "#F5F1FF",
    "amber": "#D97706",
    "amber_soft": "#FFF7E6",
    "red": "#DC2626",
    "red_soft": "#FEF1F1",
    "green": "#0E9F6E",
    "green_soft": "#EAFBF4",
    "shadow_sm": "0 1px 2px rgba(17, 17, 30, .04), 0 1px 3px rgba(17, 17, 30, .05)",
    "shadow_md": "0 12px 32px rgba(17, 17, 30, .08), 0 2px 8px rgba(17, 17, 30, .04)",
    "shadow_lg": "0 24px 60px rgba(17, 17, 30, .12)",
    "glow_1": "rgba(99, 91, 255, .08)",
    "glow_2": "rgba(37, 99, 235, .06)",
    "hero_from": "#FFFFFF",
    "hero_via": "#F7F4FF",
    "hero_to": "#F2F7FF",
    "hero_glow_1": "rgba(99, 91, 255, .16)",
    "hero_glow_2": "rgba(37, 99, 235, .12)",
    "hero_ink": "#0F1117",
    "hero_text": "#4B4B57",
    "hero_chip_bg": "rgba(255, 255, 255, .72)",
    "hero_chip_border": "rgba(17, 17, 30, .08)",
    "dot": "rgba(17, 17, 30, .035)",
    "chart_template": "plotly_white",
    "chart_text": "#4B4B57",
    "chart_muted": "#6F6F7E",
    "chart_faint": "#9A9AA8",
    "chart_grid": "#EEEFF5",
    "chart_axis": "#E4E5EE",
    "chart_surface": "#FFFFFF",
    "chart_ink": "#0F1117",
    "chart_hover": "#FFFFFF",
    "chart_hover_border": "#E4E5EE",
    "chart_hover_text": "#0F1117",
    "chart_fill": "rgba(99, 91, 255, .10)",
    "chart_bar_soft": "rgba(99, 91, 255, .62)",
    "chart_blue_soft": "rgba(37, 99, 235, .22)",
    "chart_scale": ["#EEF2FF", "#C7D2FE", "#A5B4FC", "#6366F1", "#4338CA"],
    "score_colors": ["#DC2626", "#F97316", "#F59E0B", "#84CC16", "#0E9F6E"],
    "chart_palette": [
        "#635BFF",
        "#2563EB",
        "#8B5CF6",
        "#0E9F6E",
        "#D97706",
        "#DC2626",
        "#0891B2",
        "#65A30D",
        "#DB2777",
        "#64748B",
    ],
}

DARK: dict[str, Any] = {
    "mode": "dark",
    "label": "Dark",
    "icon": ":material/dark_mode:",
    "canvas": "#08080D",
    "canvas_alt": "#0C0C13",
    "surface": "#111119",
    "surface_soft": "#0E0E16",
    "surface_raised": "#16161F",
    "surface_tint": "#191923",
    "sidebar": "#0B0B11",
    "ink": "#F4F4F8",
    "text": "#C6C6D2",
    "muted": "#8D8D9C",
    "faint": "#666676",
    "line": "#24242F",
    "line_strong": "#343442",
    "brand": "#9B95FF",
    "brand_bright": "#B5B0FF",
    "brand_soft": "rgba(155, 149, 255, .12)",
    "brand_contrast": "#0B0B11",
    "blue": "#6AA6FF",
    "blue_soft": "rgba(106, 166, 255, .12)",
    "violet": "#B49CFF",
    "violet_soft": "rgba(180, 156, 255, .12)",
    "amber": "#F6C15A",
    "amber_soft": "rgba(246, 193, 90, .12)",
    "red": "#F78B8B",
    "red_soft": "rgba(247, 139, 139, .12)",
    "green": "#4ED6A5",
    "green_soft": "rgba(78, 214, 165, .12)",
    "shadow_sm": "0 1px 2px rgba(0, 0, 0, .35)",
    "shadow_md": "0 16px 40px rgba(0, 0, 0, .38), 0 2px 8px rgba(0, 0, 0, .28)",
    "shadow_lg": "0 30px 70px rgba(0, 0, 0, .55)",
    "glow_1": "rgba(155, 149, 255, .08)",
    "glow_2": "rgba(106, 166, 255, .06)",
    "hero_from": "#151322",
    "hero_via": "#11101B",
    "hero_to": "#101828",
    "hero_glow_1": "rgba(155, 149, 255, .20)",
    "hero_glow_2": "rgba(106, 166, 255, .14)",
    "hero_ink": "#F7F7FC",
    "hero_text": "#B6B6C5",
    "hero_chip_bg": "rgba(255, 255, 255, .05)",
    "hero_chip_border": "rgba(255, 255, 255, .10)",
    "dot": "rgba(255, 255, 255, .045)",
    "chart_template": "plotly_dark",
    "chart_text": "#C6C6D2",
    "chart_muted": "#8D8D9C",
    "chart_faint": "#666676",
    "chart_grid": "#1F1F2B",
    "chart_axis": "#2A2A38",
    "chart_surface": "#111119",
    "chart_ink": "#F4F4F8",
    "chart_hover": "#181822",
    "chart_hover_border": "#343442",
    "chart_hover_text": "#F4F4F8",
    "chart_fill": "rgba(155, 149, 255, .12)",
    "chart_bar_soft": "rgba(155, 149, 255, .50)",
    "chart_blue_soft": "rgba(106, 166, 255, .24)",
    "chart_scale": ["#1E1B4B", "#312E81", "#4338CA", "#6366F1", "#A5B4FC"],
    "score_colors": ["#F78B8B", "#FB923C", "#F6C15A", "#A3E635", "#4ED6A5"],
    "chart_palette": [
        "#9B95FF",
        "#6AA6FF",
        "#B49CFF",
        "#4ED6A5",
        "#F6C15A",
        "#F78B8B",
        "#5CC8E8",
        "#A3E635",
        "#F472B6",
        "#9CA3AF",
    ],
}

THEMES: dict[str, dict[str, Any]] = {"light": LIGHT, "dark": DARK}


def normalise_mode(value: Any, default: ThemeMode = "light") -> ThemeMode:
    """Coerce an arbitrary value to a supported theme name."""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if isinstance(value, str) and value.lower() in THEMES:
        return value.lower()  # type: ignore[return-value]
    return default


def _query_mode() -> ThemeMode | None:
    try:
        raw = st.query_params.get(THEME_QUERY_KEY)
    except Exception:  # never let URL parsing break the app
        return None
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = raw[0] if raw else ""
    return normalise_mode(raw, default="light") if raw else None


def _context_mode() -> ThemeMode | None:
    """Return the browser/native theme when Streamlit exposes it."""
    try:
        raw = getattr(st.context.theme, "type", None)
    except Exception:  # older Streamlit or a context that is not ready yet
        return None
    if isinstance(raw, str) and raw.lower() in THEMES:
        return raw.lower()  # type: ignore[return-value]
    return None


def current_mode() -> ThemeMode:
    """Return the active theme, preferring an explicit choice over browser defaults."""
    mode = _query_mode()
    if mode:
        st.session_state["theme_mode"] = mode
        return mode
    saved = st.session_state.get("theme_mode")
    if isinstance(saved, str) and saved.lower() in THEMES:
        return saved.lower()  # type: ignore[return-value]
    return _context_mode() or "light"


def set_mode(mode: str) -> ThemeMode:
    mode = normalise_mode(mode)
    st.session_state["theme_mode"] = mode
    try:
        st.query_params[THEME_QUERY_KEY] = mode
    except Exception:
        pass
    return mode  # type: ignore[return-value]


def toggle_mode() -> ThemeMode:
    return set_mode("light" if current_mode() == "dark" else "dark")


def tokens(mode: str | None = None) -> dict[str, Any]:
    active = normalise_mode(mode or current_mode())
    return THEMES[active]


def chart_tokens(mode: str | None = None) -> dict[str, Any]:
    return tokens(mode)


def css_variables(mode: str | None = None) -> str:
    """Build the custom-property block used by the dashboard chrome."""
    t = tokens(mode)
    mapping = {
        "bg": t["canvas"],
        "bg-alt": t["canvas_alt"],
        "surface": t["surface"],
        "surface-soft": t["surface_soft"],
        "surface-raised": t["surface_raised"],
        "surface-tint": t["surface_tint"],
        "sidebar": t["sidebar"],
        "ink": t["ink"],
        "text": t["text"],
        "muted": t["muted"],
        "faint": t["faint"],
        "line": t["line"],
        "line-strong": t["line_strong"],
        "brand": t["brand"],
        "brand-bright": t["brand_bright"],
        "brand-soft": t["brand_soft"],
        "brand-contrast": t["brand_contrast"],
        "blue": t["blue"],
        "blue-soft": t["blue_soft"],
        "violet": t["violet"],
        "violet-soft": t["violet_soft"],
        "amber": t["amber"],
        "amber-soft": t["amber_soft"],
        "red": t["red"],
        "red-soft": t["red_soft"],
        "green": t["green"],
        "green-soft": t["green_soft"],
        "shadow-sm": t["shadow_sm"],
        "shadow-md": t["shadow_md"],
        "shadow-lg": t["shadow_lg"],
        "glow-1": t["glow_1"],
        "glow-2": t["glow_2"],
        "hero-from": t["hero_from"],
        "hero-via": t["hero_via"],
        "hero-to": t["hero_to"],
        "hero-glow-1": t["hero_glow_1"],
        "hero-glow-2": t["hero_glow_2"],
        "hero-ink": t["hero_ink"],
        "hero-text": t["hero_text"],
        "hero-chip-bg": t["hero_chip_bg"],
        "hero-chip-border": t["hero_chip_border"],
        "dot": t["dot"],
    }
    return "\n".join(f"--{name}: {value};" for name, value in mapping.items())


_NATIVE_SYNC = """
<script>
(function () {
  const desired = __DESIRED__;
  const desiredLabel = __DESIRED_LABEL__;
  const storedLabel = JSON.stringify(desiredLabel);
  const hasQuery = __HAS_QUERY__;
  const paths = __PATHS__;
  const activeKey = (p) => `stActiveTheme-${p}-v2`;
  const cacheKey = (p) => `stActiveTheme-${p}`;
  const strip = (p) => (p.length > 1 ? p.replace(/\\/+$/, "") : p);
  const current = strip(window.location.pathname || "/");
  const candidates = Array.from(new Set([...paths, current, current + "/", "/"]));

  try {
    // The explicit choice survives refresh through both the URL and localStorage.
    // If the URL is opened without a theme parameter, restore the saved choice.
    if (!hasQuery) {
      const saved = localStorage.getItem("olist-theme");
      if ((saved === "light" || saved === "dark") && saved !== desired) {
        const url = new URL(window.location.href);
        url.searchParams.set("theme", saved);
        window.location.replace(url.toString());
        return;
      }
    }

    localStorage.setItem("olist-theme", desired);

    let needsReload = false;
    candidates.forEach((path) => {
      const key = activeKey(path);
      if (localStorage.getItem(key) !== storedLabel) {
        localStorage.setItem(key, storedLabel);
        if (path === current || path === current + "/") {
          needsReload = true;
        }
      }
      localStorage.removeItem(cacheKey(path));
    });

    if (needsReload) {
      window.setTimeout(() => window.location.reload(), 40);
    }
  } catch (error) {
    // localStorage can be unavailable in private/embedded contexts. The
    // Python-rendered CSS still applies, so the app remains usable.
  }
})();
</script>
"""


def native_sync_script(mode: str | None = None) -> str:
    """Return the script that aligns Streamlit's native theme with the app."""
    active = normalise_mode(mode or current_mode())
    label = "Dark" if active == "dark" else "Light"
    has_query = _query_mode() is not None
    return (
        _NATIVE_SYNC.replace("__DESIRED__", json.dumps(active))
        .replace("__DESIRED_LABEL__", json.dumps(label))
        .replace("__HAS_QUERY__", "true" if has_query else "false")
        .replace("__PATHS__", json.dumps(list(THEME_PATHS)))
    )


def sync_native_theme(mode: str | None = None) -> None:
    """Apply the native widget theme (best effort; script runs in the page)."""
    try:
        st.html(native_sync_script(mode), unsafe_allow_javascript=True)
    except TypeError:  # older Streamlit without unsafe_allow_javascript
        st.html(native_sync_script(mode))
    except Exception:
        pass
