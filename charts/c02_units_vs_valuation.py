"""Chart 2 (hero): robots shipped in 2025 and latest valuation, humanoid makers, as paired bars
grouped by country. PNG + GIF.

Run:  python -m charts.c02_units_vs_valuation
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from charts import data
from charts.render import new_figure, ramp, save_gif
from src import style

NAME = "c02_units_vs_valuation"
TITLE = "Volume in China, valuation in America"
SUBTITLE = "Humanoid makers: robots shipped in 2025 and latest valuation, US dollars"
TAKEAWAY = "China ships the robots; America holds the valuations."
GROUPS = (("CN", "China"), ("US", "United States"), ("GB", "United Kingdom"))
BAR_HEIGHT = 0.62
# GIF timing (seconds): each country group grows in turn, then the takeaway fades in.
TIMING = {"CN": (0.6, 2.4), "US": (2.6, 4.0), "GB": (4.2, 4.8)}


@dataclass
class Row:
    name: str
    country: str
    valuation: float
    valuation_text: str
    units: float | None  # Omdia 2025 estimate; None when not disclosed
    own: tuple[float, str] | None  # company-reported count and qualifier, when it differs


def build_rows() -> list[Row]:
    """Humanoid makers with a closed or announced valuation, highest valuation first."""
    co = data.companies()
    vals = data.valuations()
    omdia = data.omdia_units_2025()
    own = data.company_units_2025()
    rows = [
        Row(
            c["name"],
            c["country"],
            vals[cid].value_usd,
            style.fmt_usd(vals[cid].value_usd, vals[cid].qualifier),
            omdia[cid][0] if cid in omdia else None,
            own.get(cid),
        )
        for cid, c in co.iterrows()
        if c["segment"] == "humanoid_fullstack" and cid in vals
    ]
    return sorted(rows, key=lambda r: -r.valuation)


def notes() -> list[tuple[str, str]]:
    """Note lines, with the company names taken from the data."""
    co = data.companies()
    vals = data.valuations()
    makers = [cid for cid in vals if co.loc[cid, "segment"] == "humanoid_fullstack"]
    listed = " and ".join(co.loc[cid, "name"].split()[0] for cid in makers if vals[cid].basis == "market cap")
    spac = ", ".join(co.loc[cid, "name"].split()[0] for cid in makers if co.loc[cid, "status"] == "spac_pending")
    pending = "; ".join(
        f"{co.loc[cid, 'name']} {style.fmt_usd(v.value_usd, v.qualifier)}"
        for cid, v in data.valuations(include_pending=True).items()
        if co.loc[cid, "segment"] == "humanoid_fullstack"
    )
    day = pd.Timestamp(data.MARKET_CAP_DATE)
    valuation = f"latest funding round; stock market value on {day.day} {day:%b %Y} for {listed}"
    valuation += f"; SPAC merger value for {spac}." if spac else "."
    return [
        (
            "Robots shipped:",
            "Omdia's 2025 estimates (via SCMP, 9 Jan 2026); the lighter bar runs to the company's own count.",
        ),
        ("Valuation:", valuation),
        ("Signs:", "'>' means at least; '~' means about."),
        ("Not shown:", f"deals not closed ({pending}); Tesla, whose Optimus has no valuation of its own."),
        ("Data and sources:", "github.com/cloarte/humanoid-market-2026"),
    ]


def layout(rows: list[Row]) -> list[tuple[str, object]]:
    """('header', country name) and ('row', Row) entries, top to bottom."""
    out: list[tuple[str, object]] = []
    for code, label in GROUPS:
        group = [r for r in rows if r.country == code]
        if group:
            out.append(("header", label))
            out += [("row", r) for r in group]
    return out


def draw(fig, t: float = 99.0) -> None:
    """Draw the chart; `t` (seconds) drives the GIF animation, the default draws everything."""
    rows = build_rows()
    items = layout(rows)
    style.add_title(fig, TITLE, SUBTITLE)
    top = style.add_notes(fig, notes())
    if (a := ramp(t, 5.2, 6.0)) > 0:
        style.add_takeaway(fig, TAKEAWAY, y=top + 0.02).set_alpha(a)
    bottom, height = top + 0.11, 0.83 - (top + 0.11)
    names = fig.add_axes((0.04, bottom, 0.17, height))
    left = fig.add_axes((0.23, bottom, 0.33, height))
    right = fig.add_axes((0.62, bottom, 0.33, height))
    n = len(items)
    for ax in (names, left, right):
        ax.set_ylim(n - 0.5, -0.9)
        ax.set_axis_off()
    names.set_xlim(0, 1)
    max_units = max(max(r.units or 0, r.own[0] if r.own else 0) for r in rows)
    left.set_xlim(0, max_units * 1.25)
    right.set_xlim(0, max(r.valuation for r in rows) * 1.18)
    for ax, heading in ((left, "Robots shipped in 2025"), (right, "Latest valuation")):
        ax.text(0, -0.9, heading, fontsize=style.SIZE_LABEL - 1, fontweight="semibold", color=style.INK, va="top")

    label_gap = max_units * 0.015
    for i, (kind, item) in enumerate(items):
        if kind == "header":
            names.text(
                0,
                i + 0.15,
                str(item).upper(),
                fontsize=style.SIZE_TICK - 1,
                fontweight="semibold",
                color=style.INK_MUTED,
                va="center",
            )
            for ax in (left, right):
                ax.axhline(i + 0.55, color=style.INK, alpha=style.HAIRLINE_ALPHA, linewidth=0.6)
            continue
        r: Row = item  # type: ignore[assignment]
        grow = ramp(t, *TIMING.get(r.country, TIMING["GB"]))
        if grow == 0:
            continue
        color = style.country_color(r.country)
        names.text(0, i, r.name, fontsize=style.SIZE_LABEL - 1, color=style.INK, va="center", alpha=min(1, grow * 2))
        if r.units is None:
            left.text(
                0,
                i,
                "not disclosed",
                fontsize=style.SIZE_TICK,
                color=style.INK_MUTED,
                va="center",
                style="italic",
                alpha=grow,
            )
        else:
            left.barh(i, r.units * grow, height=BAR_HEIGHT, color=color)
            end, label = r.units, f"{r.units:,.0f}"
            if r.own:
                left.barh(
                    i, (r.own[0] - r.units) * grow, left=r.units * grow, height=BAR_HEIGHT, color=color, alpha=0.35
                )
                end = r.own[0]
                label = f"{r.units:,.0f} → {style.QUALIFIER_SYMBOL[r.own[1]]}{r.own[0]:,.0f}"
            if grow == 1:
                left.text(end + label_gap, i, label, fontsize=style.SIZE_TICK, color=style.INK, va="center")
        right.barh(i, r.valuation * grow, height=BAR_HEIGHT, color=color)
        if grow == 1:
            right.text(
                r.valuation + right.get_xlim()[1] * 0.012,
                i,
                r.valuation_text,
                fontsize=style.SIZE_TICK,
                color=style.INK,
                va="center",
            )


def main() -> None:
    fig = new_figure()
    draw(fig)
    print(style.save_png(fig, NAME))
    print(save_gif(draw, NAME, seconds=7.0))


if __name__ == "__main__":
    main()
