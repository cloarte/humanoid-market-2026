"""Chart style: palette, fonts, label rules and export sizes.

This is the only file in the repo allowed to contain colour codes
(`src/validate.py` fails on hex colours anywhere else). Charts import from here.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
FONT_DIR = ROOT / "assets" / "fonts"  # bundled OFL fonts (Inter, Source Serif 4) for identical renders

# --- Palette -----------------------------------------------------------------
# Checked with a colour-vision validator (OKLab ΔE, simulated colour blindness) on PAPER, 2026-10-12:
# SLATE / AMBER / OTHER are separable for all common colour-vision deficiencies (worst ΔE 17) and for
# normal vision (worst ΔE 18.7). Two known limits, both by design: SLATE is darker and greyer than a
# generic categorical palette would choose (brand colour), and AMBER has 2.5:1 contrast on PAPER, so
# every amber mark carries a direct text label in INK and every chart has a table view.

PAPER = "#F4F1EA"  # background
INK = "#2B2B2B"  # text, axes
SLATE = "#33506B"  # United States / analysis
SLATE_LIGHT = "#B0B9BE"  # SLATE at 35% on PAPER: a broader total that a SLATE series sits inside
AMBER = "#C9903A"  # China / volume
OTHER = "#8A7CA3"  # any other country (e.g. UK); muted violet, validated against SLATE and AMBER
INK_MUTED = "#7B7A77"  # secondary text (subtitle, axis ticks): INK at 60% on PAPER
NOTE_INK = "#55534F"  # note text under a chart: darker than INK_MUTED so small text stays readable
HAIRLINE = "#D6D3CD"  # the one permitted gridline: INK at 15% on PAPER
HAIRLINE_ALPHA = 0.15  # same hairline expressed as INK + alpha, for matplotlib

COUNTRY_COLOR = {"US": SLATE, "CN": AMBER}
COUNTRY_LABEL = {"US": "United States", "CN": "China"}


def country_color(iso2: str) -> str:
    return COUNTRY_COLOR.get(iso2, OTHER)


# Datawrapper has no access to this module: datawrapper/export.py writes these into dw_colors.md.
DATAWRAPPER_COLORS = {
    "background": PAPER,
    "text": INK,
    "United States": SLATE,
    "China": AMBER,
    "Other": OTHER,
    "secondary text": INK_MUTED,
    "gridline": HAIRLINE,
}

# --- Marks -------------------------------------------------------------------
# Filled = disclosed. Hollow (paper fill, coloured edge) = undisclosed; never drawn as zero.
# Deals not closed (in_talks / term_sheet) are a light tint with a dashed edge, plus a text suffix,
# so they stay distinguishable from both closed deals and undisclosed values.

MARKER_SIZE = 120  # scatter area, points^2
EDGE_WIDTH = 1.6


def marker_style(color: str, *, disclosed: bool = True, pending: bool = False) -> dict:
    """Scatter kwargs: filled = disclosed, paper fill = undisclosed; a dashed edge marks a pending deal."""
    edge = dict(edgecolors=color, linewidths=EDGE_WIDTH, linestyles=(0, (2, 1.5)) if pending else "solid")
    if not disclosed:
        return dict(facecolors=PAPER, **edge)
    if pending:
        return dict(facecolors=color, alpha=0.35, **edge)
    return dict(facecolors=color, **edge)


PENDING_STATUSES = {"in_talks", "term_sheet"}
PENDING_SUFFIX = {"in_talks": " (in talks)", "term_sheet": " (term sheet)"}
YTD_HATCH = "////"

# --- Typography ----------------------------------------------------------------

SANS = ["Inter", "Roboto", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]
SERIF = ["Source Serif 4", "Georgia", "DejaVu Serif"]
SIZE_TITLE = 17
SIZE_LABEL = 12
SIZE_TICK = 10
SIZE_TAKEAWAY = 14
SIZE_SOURCE = 8.5
SIZE_NOTE = 10
TAKEAWAY_MAX_WORDS = 15

# --- Export ------------------------------------------------------------------

FIG_WIDTH_IN = 12.0
PNG_WIDTH_PX = 2400  # @2x of a 1200 px layout
GIF_WIDTH_PX = 1200
GIF_MAX_BYTES = 8 * 1024 * 1024
GIF_SECONDS = (6.0, 10.0)  # allowed total duration
GIF_HOLD_FIRST_S = 1.5  # first frame (the cover: the complete chart) is held this long
GIF_HOLD_FINAL_S = 2.5  # last frame is held this long

# --- Label rules ---------------------------------------------------------------

QUALIFIER_SYMBOL = {"eq": "", "approx": "~", "gt": ">", "gte": "≥", "lt": "<", "lte": "≤", "range": ""}


def _compact(x: float) -> str:
    """Three significant figures at most, trailing zeros dropped: 5.50 -> 5.5, 39.0 -> 39."""
    return f"{x:.3g}" if x < 1000 else f"{x:,.0f}"


def fmt_usd(x: float, qualifier: str = "") -> str:
    """$39B, $5.5B, $520M, $13.5k, $5,900. Prefixed with ~ > < etc. from the qualifier."""
    sym = QUALIFIER_SYMBOL.get(qualifier or "eq", "")
    for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(x) >= div:
            return f"{sym}${_compact(x / div)}{suffix}"
    if abs(x) >= 10_000:
        return f"{sym}${_compact(x / 1e3)}k"
    return f"{sym}${x:,.0f}"


def fmt_units(n: float, qualifier: str = "", noun: str = "units") -> str:
    """5,168 units; ~5,500 units; <100 units; 1.4M units."""
    sym = QUALIFIER_SYMBOL.get(qualifier or "eq", "")
    body = f"{_compact(n / 1e6)}M" if abs(n) >= 1e6 else f"{n:,.0f}"
    return f"{sym}{body} {noun}".strip()


def check_takeaway(text: str) -> str:
    words = len(text.split())
    if words > TAKEAWAY_MAX_WORDS:
        raise ValueError(f"takeaway has {words} words (max {TAKEAWAY_MAX_WORDS}): {text!r}")
    return text


# --- Matplotlib setup ---------------------------------------------------------


def apply() -> None:
    """Register bundled fonts (if any) and set rcParams. Call once per chart script."""
    import matplotlib as mpl
    from matplotlib import font_manager

    if FONT_DIR.exists():
        for f in list(FONT_DIR.glob("*.ttf")) + list(FONT_DIR.glob("*.otf")):
            font_manager.fontManager.addfont(str(f))
    mpl.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "savefig.facecolor": PAPER,
            "text.color": INK,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "axes.linewidth": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": SANS,
            "font.serif": SERIF,
            "font.size": SIZE_LABEL,
            "axes.titlesize": SIZE_TITLE,
            "xtick.labelsize": SIZE_TICK,
            "ytick.labelsize": SIZE_TICK,
            "legend.frameon": False,
            "text.parse_math": False,  # "$" is currency here, never TeX math
            "hatch.color": INK_MUTED,
            "hatch.linewidth": 0.6,
        }
    )


def hairline(ax, axis: str = "y") -> None:
    """The single permitted gridline style."""
    ax.grid(True, axis=axis, color=INK, alpha=HAIRLINE_ALPHA, linewidth=0.6)
    ax.set_axisbelow(True)


def add_title(fig, text: str, subtitle: str = ""):
    """Bold title and an optional muted subtitle, top left. Returns the title Text."""
    title = fig.text(0.04, 0.965, text, ha="left", va="top", fontsize=SIZE_TITLE, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.04, 0.925, subtitle, ha="left", va="top", fontsize=SIZE_LABEL, color=INK_MUTED)
    return title


def add_takeaway(fig, text: str, y: float = 0.075):
    """One serif-italic line under the chart, at most TAKEAWAY_MAX_WORDS words. Returns the Text."""
    return fig.text(
        0.04,
        y,
        check_takeaway(text),
        ha="left",
        va="bottom",
        fontsize=SIZE_TAKEAWAY,
        family="serif",
        style="italic",
        color=INK,
    )


def add_notes(fig, lines: list[tuple[str, str]], y: float = 0.02) -> float:
    """Notes under a chart, one idea per line with its lead term in bold, e.g.
    ("Valuation:", "latest funding round."). Drawn upwards from `y` (figure fraction); returns the
    top of the block so the takeaway can sit above it."""
    from matplotlib.text import Annotation

    step = SIZE_NOTE * 1.6 / 72 / fig.get_size_inches()[1]
    for i, (term, text) in enumerate(reversed(lines)):
        row = y + i * step
        head = fig.text(0.04, row, term, ha="left", va="bottom", fontsize=SIZE_NOTE, fontweight="bold", color=INK)
        # Anchored to the bold term's right edge at draw time, so the gap is the same at any resolution.
        body = Annotation(text, xy=(1, 0), xycoords=head, xytext=(4, 0), textcoords="offset points", va="bottom")
        body.set(fontsize=SIZE_NOTE, color=NOTE_INK)
        fig.add_artist(body)
    return y + len(lines) * step


def add_source(fig, text: str, y: float = 0.025):
    """Muted source line(s) at the bottom. Returns the Text."""
    return fig.text(0.04, y, text, ha="left", va="bottom", fontsize=SIZE_SOURCE, color=INK_MUTED, linespacing=1.5)


def save_png(fig, name: str, out: Path = OUTPUTS) -> Path:
    """Save <out>/<name>.png exactly PNG_WIDTH_PX wide (out defaults to outputs/)."""
    out.mkdir(exist_ok=True)
    w_in = fig.get_size_inches()[0]
    path = out / f"{name}.png"
    fig.savefig(path, dpi=PNG_WIDTH_PX / w_in, facecolor=PAPER)
    return path
