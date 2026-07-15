"""Enterprise branding for executive reports (Module 13).

A single, dependency-free source of truth for the report's visual identity —
colours, typography, cover-page copy and section numbering — shared by every
renderer and exporter so a PDF, DOCX, HTML and PPTX all look like the same
McKinsey/Deloitte-grade briefing. No engine or UI import here, so it is trivially
reusable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Brand:
    """The TalentMind executive-report brand system.

    Attributes:
        product: Product name shown on the cover / footer.
        tagline: One-line positioning statement.
        logo_placeholder: Text/emoji logo placeholder (real logo swaps in later).
        primary: Primary brand colour (hex) — headers, accents.
        secondary: Secondary colour (hex) — sub-headers.
        accent: Accent colour (hex) — highlights / positive.
        ink: Body-text colour (hex).
        muted: Muted/caption colour (hex).
        surface: Light surface/background colour (hex).
        danger / warning / success: Semantic status colours (hex).
        heading_font / body_font: Font stacks for HTML rendering.
    """

    product: str = "TalentMind"
    tagline: str = "Executive Hiring Intelligence"
    logo_placeholder: str = "🧠 TalentMind"
    primary: str = "#0B1F3A"
    secondary: str = "#13315C"
    accent: str = "#2E86DE"
    ink: str = "#1A1A2E"
    muted: str = "#5B6B7B"
    surface: str = "#F5F7FA"
    danger: str = "#C0392B"
    warning: str = "#E67E22"
    success: str = "#1E8449"
    heading_font: str = "'Georgia', 'Times New Roman', serif"
    body_font: str = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

    # Recommendation → semantic colour (for scorecards / badges).
    rec_colors: Dict[str, str] = field(
        default_factory=lambda: {
            "Hire Immediately": "#1E8449",
            "Strong Hire": "#1E8449",
            "Hire": "#27AE60",
            "Lean Hire": "#58D68D",
            "Proceed to Interview": "#2E86DE",
            "Further Assessment": "#E67E22",
            "Hold": "#E67E22",
            "Talent Pool": "#8E44AD",
            "Future Opportunity": "#8E44AD",
            "Lean No Hire": "#EC7063",
            "No Hire": "#C0392B",
            "Reject": "#C0392B",
        }
    )

    def rec_color(self, recommendation: str) -> str:
        """Return the brand colour for a recommendation label (accent default)."""
        return self.rec_colors.get(recommendation, self.accent)


# Process-wide default brand. Swap for a per-tenant brand later without a redesign.
DEFAULT_BRAND = Brand()


def section_number(index: int) -> str:
    """Return a zero-padded section number (``1`` -> ``"01"``) for the TOC."""
    return f"{index:02d}"
