"""Reusable Streamlit UI components for TalentMind.

Small, presentation-only building blocks shared across UI modules so that
cards, meters, and badges are rendered consistently (and without duplicated
code) everywhere. No business logic.
"""

from typing import Iterable, Optional

import streamlit as st

# Map a semantic style to the matching Streamlit status renderer.
_STATUS_RENDERERS = {
    "success": st.success,
    "info": st.info,
    "warning": st.warning,
    "error": st.error,
}

# Map a Low/Medium/High level to a card style + emoji.
_LEVEL_STYLE = {
    "Low": ("success", "🟢"),
    "Medium": ("warning", "🟡"),
    "High": ("error", "🔴"),
}


def render_cards(
    items: Iterable[str],
    style: str = "info",
    empty_message: Optional[str] = None,
) -> None:
    """Render an iterable of strings as a stack of colored status cards.

    Args:
        items: The card texts.
        style: One of ``success`` / ``info`` / ``warning`` / ``error``.
        empty_message: Optional caption shown when ``items`` is empty.
    """
    renderer = _STATUS_RENDERERS.get(style, st.info)
    rendered_any = False
    for item in items:
        renderer(item)
        rendered_any = True
    if not rendered_any and empty_message:
        st.caption(empty_message)


def render_meter(
    label: str,
    value: float,
    max_value: float = 100.0,
    help_text: Optional[str] = None,
) -> None:
    """Render a labelled metric with a normalized progress bar underneath.

    Args:
        label: Metric label.
        value: Current value.
        max_value: Value that maps to a full bar.
        help_text: Optional caption shown below the bar.
    """
    st.metric(label, f"{value:.0f}")
    ratio = 0.0 if max_value <= 0 else value / max_value
    st.progress(min(max(ratio, 0.0), 1.0))
    if help_text:
        st.caption(help_text)


def render_level_badge(label: str, level: str) -> None:
    """Render a Low/Medium/High level as a colored status badge.

    Falls back to an informational badge for unrecognized levels.
    """
    style, emoji = _LEVEL_STYLE.get(level, ("info", "⚪"))
    renderer = _STATUS_RENDERERS.get(style, st.info)
    renderer(f"{emoji} {label}: **{level}**")
