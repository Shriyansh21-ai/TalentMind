"""Centralized design system for the TalentMind UI layer.

This is the single source of truth for the product's visual language — an
enterprise, Linear/Vercel/Stripe-grade look built entirely on top of Streamlit.
It contains no business logic; it only defines design tokens and presentation
helpers so that every screen shares one consistent, professional appearance
without duplicated colors, CSS, or component code.

What lives here:

* Design tokens — color palette, semantic colors, spacing, radius, shadows,
  typography.
* :func:`inject_theme` — one global CSS pass that restyles Streamlit's native
  widgets (headings, buttons, metrics, tabs, tables, expanders, sidebar) into
  the enterprise design language. Call it once, early, from the app shell.
* Reusable render helpers — badges, status/level pills, and empty states — so
  status wording and elevation are identical everywhere.

Native Streamlit primitives (``st.metric``, ``st.subheader``, ``st.dataframe``,
``st.spinner``) are intentionally kept and styled via CSS rather than replaced,
so behavior and test-visible structure are preserved while the look is unified.
"""

from __future__ import annotations

import html
import re

import streamlit as st

# Emoji / decorative-symbol ranges. Used only to sanitize strings produced by
# the (unchanged) backend before they are rendered, so no emoji reaches the
# screen without modifying business logic. Excludes arrows, bullets and dashes.
_EMOJI_RE = re.compile(
    "[\U0001f100-\U0001faff"  # pictographs, enclosed alphanumerics, supplemental
    "\U00002600-\U000027bf"  # misc symbols + dingbats
    "\U00002300-\U000023ff"  # misc technical
    "\U00002b00-\U00002bff"  # misc symbols & arrows
    "\U00002139"  # information source
    "\U000025a0-\U000025ff"  # geometric shapes
    "\U0000fe00-\U0000fe0f]+[︀-️‍⃣]*"  # + variation selectors
)


def strip_emoji(text: str) -> str:
    """Return ``text`` with emojis/decorative glyphs removed and spacing tidied.

    This is a presentation-layer sanitizer applied at render boundaries to
    strings that originate in the (deliberately unmodified) backend — e.g.
    provider logos, copilot action labels, monitor event logs. Business logic
    and stored data are never changed; only what is drawn on screen is cleaned.
    """
    if not text:
        return text
    cleaned = _EMOJI_RE.sub("", text)
    # Collapse the whitespace the removal can leave behind.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

#: Enterprise color palette. Blue primary, slate neutrals, restrained semantics.
COLORS: dict[str, str] = {
    # Brand / primary
    "primary": "#2563EB",  # blue-600
    "primary_hover": "#1D4ED8",  # blue-700
    "primary_soft": "#EFF6FF",  # blue-50
    "primary_border": "#BFDBFE",  # blue-200
    # Neutral / slate
    "text": "#0F172A",  # slate-900
    "text_secondary": "#475569",  # slate-600
    "text_muted": "#94A3B8",  # slate-400
    "border": "#E2E8F0",  # slate-200
    "border_strong": "#CBD5E1",  # slate-300
    "surface": "#FFFFFF",
    "surface_subtle": "#F8FAFC",  # slate-50
    "surface_muted": "#F1F5F9",  # slate-100
    # Semantic — success / warning / danger / info / neutral
    "success": "#16A34A",  # green-600
    "success_soft": "#F0FDF4",  # green-50
    "success_border": "#BBF7D0",  # green-200
    "warning": "#D97706",  # amber-600
    "warning_soft": "#FFFBEB",  # amber-50
    "warning_border": "#FDE68A",  # amber-200
    "danger": "#DC2626",  # red-600
    "danger_soft": "#FEF2F2",  # red-50
    "danger_border": "#FECACA",  # red-200
    "info": "#2563EB",  # blue-600
    "info_soft": "#EFF6FF",  # blue-50
    "info_border": "#BFDBFE",  # blue-200
    "neutral": "#475569",  # slate-600
    "neutral_soft": "#F1F5F9",  # slate-100
    "neutral_border": "#E2E8F0",  # slate-200
}

#: 4px-based spacing scale (rem values).
SPACE = {
    "xs": "0.25rem",
    "sm": "0.5rem",
    "md": "0.75rem",
    "lg": "1rem",
    "xl": "1.5rem",
    "2xl": "2rem",
}

#: Border radius scale.
RADIUS = {"sm": "6px", "md": "8px", "lg": "12px", "pill": "999px"}

#: Elevation scale — very subtle, enterprise-appropriate.
SHADOW = {
    "sm": "0 1px 2px 0 rgba(15, 23, 42, 0.04)",
    "md": "0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.04)",
    "lg": "0 4px 12px -2px rgba(15, 23, 42, 0.08)",
}

#: System font stack — matches Linear / Vercel / GitHub.
FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, '
    'sans-serif, "Apple Color Emoji", "Segoe UI Emoji"'
)
FONT_MONO = 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'

#: The five badge variants used across the product.
_BADGE_VARIANTS = ("success", "warning", "danger", "info", "neutral", "primary")

#: Map free-text status wording to a badge variant. Keys are lower-cased.
_STATUS_VARIANTS: dict[str, str] = {
    # success
    "ready": "success",
    "healthy": "success",
    "completed": "success",
    "complete": "success",
    "active": "success",
    "connected": "success",
    "passed": "success",
    "pass": "success",
    "approved": "success",
    "resolved": "success",
    "operational": "success",
    "online": "success",
    "success": "success",
    "compliant": "success",
    # info / running
    "running": "info",
    "in progress": "info",
    "in review": "info",
    "processing": "info",
    "generated": "info",
    "info": "info",
    # warning / pending
    "pending": "warning",
    "queued": "warning",
    "waiting": "warning",
    "warning": "warning",
    "degraded": "warning",
    "at risk": "warning",
    "review required": "warning",
    "partial": "warning",
    # danger
    "failed": "danger",
    "fail": "danger",
    "error": "danger",
    "critical": "danger",
    "rejected": "danger",
    "blocked": "danger",
    "offline": "danger",
    "incident": "danger",
    "non-compliant": "danger",
    # neutral
    "unknown": "neutral",
    "n/a": "neutral",
    "na": "neutral",
    "inactive": "neutral",
    "disconnected": "neutral",
    "not started": "neutral",
    "draft": "neutral",
}

#: Map Low/Medium/High-style levels to a badge variant.
_LEVEL_VARIANTS: dict[str, str] = {
    "low": "success",
    "low-medium": "success",
    "minimal": "success",
    "medium": "warning",
    "moderate": "warning",
    "medium-high": "warning",
    "elevated": "warning",
    "high": "danger",
    "critical": "danger",
    "severe": "danger",
}


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------


def _global_css() -> str:
    """Return the global stylesheet that restyles Streamlit into the theme."""
    c = COLORS
    return f"""
    <style>
    /* ---- Base typography ------------------------------------------------ */
    html, body, [class*="css"], .stMarkdown, .stApp {{
        font-family: {FONT_STACK};
        color: {c["text"]};
    }}
    .stApp {{ background: {c["surface"]}; }}

    /* Tighten the default page width & vertical rhythm for a denser, more
       professional layout. */
    .block-container {{
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }}

    /* ---- Headings ------------------------------------------------------- */
    h1, h2, h3, h4, h5, h6 {{
        color: {c["text"]};
        font-weight: 600;
        letter-spacing: -0.011em;
    }}
    h1 {{ font-size: 1.75rem; line-height: 2.1rem; font-weight: 650; }}
    h2 {{ font-size: 1.35rem; line-height: 1.8rem; }}
    h3 {{ font-size: 1.12rem; line-height: 1.6rem; }}
    h4 {{ font-size: 1rem; color: {c["text_secondary"]}; text-transform: none; }}

    /* Section captions read as muted supporting text. */
    [data-testid="stCaptionContainer"], .stCaption, small {{
        color: {c["text_muted"]} !important;
    }}

    /* ---- Buttons -------------------------------------------------------- */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
        border-radius: {RADIUS["md"]};
        border: 1px solid {c["border"]};
        font-weight: 550;
        font-size: 0.9rem;
        padding: 0.4rem 0.95rem;
        transition: background 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
        box-shadow: {SHADOW["sm"]};
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        border-color: {c["border_strong"]};
        background: {c["surface_subtle"]};
    }}
    /* Primary action buttons */
    .stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"],
    .stFormSubmitButton > button[kind="primary"] {{
        background: {c["primary"]};
        border-color: {c["primary"]};
        color: #fff;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {c["primary_hover"]};
        border-color: {c["primary_hover"]};
    }}

    /* ---- Metrics (KPI cards) — one identical layout everywhere ---------- */
    [data-testid="stMetric"] {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS["lg"]};
        padding: 1rem 1.15rem;
        box-shadow: {SHADOW["sm"]};
    }}
    [data-testid="stMetricLabel"] {{
        color: {c["text_secondary"]};
        font-weight: 550;
        font-size: 0.8rem;
    }}
    [data-testid="stMetricValue"] {{
        color: {c["text"]};
        font-weight: 640;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.02em;
    }}

    /* ---- Tabs — quiet, underlined, enterprise ------------------------- */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.25rem;
        border-bottom: 1px solid {c["border"]};
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 2.5rem;
        padding: 0 0.9rem;
        font-size: 0.9rem;
        font-weight: 550;
        color: {c["text_secondary"]};
    }}
    .stTabs [aria-selected="true"] {{ color: {c["primary"]}; }}

    /* ---- Expanders ----------------------------------------------------- */
    [data-testid="stExpander"] {{
        border: 1px solid {c["border"]};
        border-radius: {RADIUS["lg"]};
        box-shadow: {SHADOW["sm"]};
        overflow: hidden;
    }}
    [data-testid="stExpander"] summary {{ font-weight: 550; }}

    /* ---- Dataframes / tables ------------------------------------------ */
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        border: 1px solid {c["border"]};
        border-radius: {RADIUS["lg"]};
        overflow: hidden;
    }}

    /* ---- Alerts / notifications --------------------------------------- */
    [data-testid="stAlert"], [data-testid="stNotification"] {{
        border-radius: {RADIUS["md"]};
        border: 1px solid {c["border"]};
        box-shadow: none;
    }}

    /* ---- Progress bars ------------------------------------------------- */
    [data-testid="stProgress"] > div > div > div > div {{
        background-color: {c["primary"]};
    }}

    /* ---- Inputs -------------------------------------------------------- */
    .stTextInput input, .stTextArea textarea, .stNumberInput input,
    [data-baseweb="select"] > div {{
        border-radius: {RADIUS["md"]};
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: {c["primary"]};
        box-shadow: 0 0 0 3px {c["primary_soft"]};
    }}
    code, kbd, pre {{ font-family: {FONT_MONO}; }}

    /* ---- Sidebar navigation ------------------------------------------- */
    [data-testid="stSidebar"] {{
        background: {c["surface_subtle"]};
        border-right: 1px solid {c["border"]};
    }}
    [data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}
    /* Group labels rendered via st.caption in the sidebar */
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.68rem !important;
        font-weight: 650;
        color: {c["text_muted"]} !important;
        margin: 0.75rem 0 0.15rem 0;
    }}

    /* ---- Badges & pills (see tm.badge / status_pill / level_pill) ----- */
    .tm-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        border-radius: {RADIUS["pill"]};
        font-weight: 600;
        line-height: 1;
        border: 1px solid transparent;
        white-space: nowrap;
        vertical-align: middle;
    }}
    .tm-badge--sm {{ font-size: 0.68rem; padding: 0.2rem 0.5rem; }}
    .tm-badge--md {{ font-size: 0.75rem; padding: 0.28rem 0.65rem; }}
    .tm-badge--lg {{ font-size: 0.85rem; padding: 0.38rem 0.85rem; }}
    .tm-badge--dot::before {{
        content: "";
        width: 0.45rem; height: 0.45rem;
        border-radius: 50%;
        background: currentColor;
        opacity: 0.9;
    }}
    .tm-badge--success {{ color: {c["success"]}; background: {c["success_soft"]}; border-color: {c["success_border"]}; }}
    .tm-badge--warning {{ color: {c["warning"]}; background: {c["warning_soft"]}; border-color: {c["warning_border"]}; }}
    .tm-badge--danger  {{ color: {c["danger"]};  background: {c["danger_soft"]};  border-color: {c["danger_border"]}; }}
    .tm-badge--info    {{ color: {c["info"]};    background: {c["info_soft"]};    border-color: {c["info_border"]}; }}
    .tm-badge--primary {{ color: #fff;           background: {c["primary"]};      border-color: {c["primary"]}; }}
    .tm-badge--neutral {{ color: {c["neutral"]}; background: {c["neutral_soft"]}; border-color: {c["neutral_border"]}; }}

    /* ---- Empty state --------------------------------------------------- */
    .tm-empty {{
        border: 1px dashed {c["border_strong"]};
        border-radius: {RADIUS["lg"]};
        padding: 2.25rem 1.5rem;
        text-align: center;
        background: {c["surface_subtle"]};
        color: {c["text_secondary"]};
    }}
    .tm-empty__title {{ font-weight: 600; color: {c["text"]}; font-size: 1rem; margin-bottom: 0.25rem; }}
    .tm-empty__desc {{ color: {c["text_muted"]}; font-size: 0.88rem; }}
    </style>
    """


def inject_theme() -> None:
    """Inject the global enterprise stylesheet once per session run.

    Safe to call multiple times; the CSS is idempotent. Call this early from the
    application shell so every workspace inherits the design system.
    """
    st.markdown(_global_css(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Badges & pills
# ---------------------------------------------------------------------------


def badge(label: str, variant: str = "neutral", *, size: str = "md", dot: bool = False) -> str:
    """Return an HTML badge/pill string.

    Args:
        label: Visible text (HTML-escaped).
        variant: One of ``success``/``warning``/``danger``/``info``/``neutral``/``primary``.
        size: ``sm``/``md``/``lg``.
        dot: When ``True`` prefixes a small status dot.

    Returns:
        An inline ``<span>`` string for use with ``unsafe_allow_html=True``.
    """
    variant = variant if variant in _BADGE_VARIANTS else "neutral"
    size = size if size in ("sm", "md", "lg") else "md"
    classes = f"tm-badge tm-badge--{variant} tm-badge--{size}"
    if dot:
        classes += " tm-badge--dot"
    return f'<span class="{classes}">{html.escape(str(label))}</span>'


def status_variant(status: str) -> str:
    """Map free-text status wording to a badge variant (defaults to neutral)."""
    return _STATUS_VARIANTS.get(str(status).strip().lower(), "neutral")


def level_variant(level: str) -> str:
    """Map a Low/Medium/High-style level to a badge variant (defaults to info)."""
    return _LEVEL_VARIANTS.get(str(level).strip().lower(), "info")


def status_pill(status: str, *, size: str = "md") -> str:
    """Return an HTML status pill, colored by :func:`status_variant`."""
    return badge(status, status_variant(status), size=size, dot=True)


def level_pill(level: str, *, size: str = "md") -> str:
    """Return an HTML level pill, colored by :func:`level_variant`."""
    return badge(level, level_variant(level), size=size, dot=True)


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------


def empty_state(title: str, description: str | None = None) -> None:
    """Render a professional empty state instead of a blank screen."""
    desc = f'<div class="tm-empty__desc">{html.escape(description)}</div>' if description else ""
    st.markdown(
        f'<div class="tm-empty"><div class="tm-empty__title">{html.escape(title)}</div>{desc}</div>',
        unsafe_allow_html=True,
    )
