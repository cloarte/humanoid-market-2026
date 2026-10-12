"""Chart 1: venture capital into robotics and into humanoids, by year. PNG + GIF.

Run:  python -m charts.c01_capital_by_year
"""

from __future__ import annotations

import matplotlib.ticker as mticker
import pandas as pd

from charts import data
from charts.render import new_figure, ramp, save_gif
from src import style

NAME = "c01_capital_by_year"
TITLE = "Robotics funding hit a record by June 2026"
SUBTITLE = "Venture capital invested worldwide each year, US dollars; dark bars are humanoid robot companies"
TAKEAWAY = "Humanoids drew $6.1B in 2025 and over $5B by mid-May 2026."
NOTES = [
    (
        "All robotics:",
        "Crunchbase News (22 Jun 2026); venture rounds, broad definition that includes drones and defense.",
    ),
    ("Humanoid robots:", "PitchBook News (11 Feb 2026; the 2026 figure from 15 May 2026)."),
    (
        "Caution:",
        "the two providers classify deals differently, so the humanoid bar is not an exact part of the total.",
    ),
    ("Hatched bars:", "year to date, up to the date shown."),
    ("Data and sources:", "github.com/cloarte/humanoid-market-2026"),
]
YEARS = list(range(2020, 2027))
SECONDS_PER_YEAR = 0.6


def series() -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per year and scope; for a partial year, the most recent cut-off."""
    s = data.load("sector_funding")
    s["year"] = s["year"].astype(int)
    s["amount"] = s["amount_usd"].astype(float)

    def pick(scope: str) -> pd.DataFrame:
        rows = s[(s["scope"] == scope) & s["year"].isin(YEARS)].sort_values(["year", "period_end"])
        return rows.drop_duplicates("year", keep="last").set_index("year")

    return pick("robotics_all"), pick("humanoid")


def _partial_label(period_end: str) -> str:
    """'to Jun 22' (portable: no platform-specific strftime flags)."""
    if not period_end:
        return ""
    day = pd.Timestamp(period_end)
    return f"to {day:%b} {day.day}"


def draw(fig, t: float = 99.0) -> None:
    robotics, humanoid = series()
    style.add_title(fig, TITLE, SUBTITLE)
    _legend(fig, ramp(t, 0.1, 0.6))
    ax = fig.add_axes((0.08, 0.31, 0.86, 0.52))
    ax.set_ylim(0, 21e9)
    ax.set_xlim(YEARS[0] - 0.6, YEARS[-1] + 0.6)
    style.hairline(ax, "y")
    ax.yaxis.set_major_locator(mticker.MultipleLocator(5e9))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: style.fmt_usd(v) if v else "$0"))
    ax.set_xticks(YEARS)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    for i, year in enumerate(YEARS):
        grow = ramp(t, 0.6 + i * SECONDS_PER_YEAR, 0.6 + (i + 1) * SECONDS_PER_YEAR)
        if grow == 0:
            continue
        for frame, width, color, top in (
            (robotics, 0.72, style.SLATE_LIGHT, True),
            (humanoid, 0.34, style.SLATE, False),
        ):
            if year not in frame.index:
                continue
            row = frame.loc[year]
            partial = bool(row["period_end"])
            ax.bar(
                year,
                row["amount"] * grow,
                width=width,
                color=color,
                edgecolor=style.PAPER,
                linewidth=1.5,
                hatch=style.YTD_HATCH if partial else None,
                zorder=2 if top else 3,
            )
            if grow < 1:
                continue
            value = style.fmt_usd(row["amount"], row["amount_qualifier"])
            if top:
                label = value + (f"\n{_partial_label(row['period_end'])}" if partial else "")
                ax.annotate(
                    label,
                    (year, row["amount"]),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=style.SIZE_TICK,
                    color=style.INK,
                    linespacing=1.3,
                )
            else:
                label = value + (f" ({_partial_label(row['period_end'])})" if partial else "")
                ax.annotate(
                    label,
                    (year + width / 2, row["amount"]),
                    xytext=(3, 2),
                    textcoords="offset points",
                    ha="left",
                    va="bottom",
                    fontsize=style.SIZE_TICK - 1,
                    color=style.INK,
                    fontweight="semibold",
                )
    top = style.add_notes(fig, NOTES)
    if (a := ramp(t, 5.2, 6.0)) > 0:
        style.add_takeaway(fig, TAKEAWAY, y=top + 0.02).set_alpha(a)


def _legend(fig, alpha: float) -> None:
    lg = fig.add_axes((0.0, 0.85, 1.0, 0.045))
    lg.set_axis_off()
    lg.set_xlim(0, 1)
    lg.set_ylim(0, 1)
    x = 0.045
    for color, hatch, label in (
        (style.SLATE_LIGHT, None, "All robotics (Crunchbase)"),
        (style.SLATE, None, "Humanoid robots (PitchBook)"),
        (style.SLATE_LIGHT, style.YTD_HATCH, "Year to date"),
    ):
        lg.bar(x, 0.6, width=0.012, bottom=0.2, color=color, hatch=hatch, edgecolor=style.PAPER, alpha=alpha)
        lg.text(x + 0.012, 0.5, label, fontsize=style.SIZE_TICK, color=style.INK, va="center", alpha=alpha)
        x += 0.03 + 0.0062 * len(label)


def main() -> None:
    fig = new_figure()
    draw(fig)
    print(style.save_png(fig, NAME))
    print(save_gif(draw, NAME, seconds=6.5))


if __name__ == "__main__":
    main()
