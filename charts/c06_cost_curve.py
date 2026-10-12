"""Chart 6: the cost curve — list prices, targets and analyst cost estimates per humanoid. PNG.

Run:  python -m charts.c06_cost_curve
"""

from __future__ import annotations

import matplotlib.ticker as mticker

from charts import data
from charts.render import new_figure
from src import style

NAME = "c06_cost_curve"
TITLE = "The cost gap"
SUBTITLE = "US dollars per humanoid robot (logarithmic scale): list prices, price targets and analyst cost estimates"
TAKEAWAY = "Chinese parts may cost under $17k by 2030; Western robots cost $90k+ to build."
NOTES = [
    (
        "List prices:",
        "Unitree (AI Business, Jul 2025; Bloomberg via Business Standard, Jul 2025; Fortune, Mar 2026); "
        "1X NEO (The Cryptonomist, Aug 2026).",
    ),
    ("Costs:", "Fortune (13 Mar 2026), reporting on BofA Global Research's humanoid robot forecast."),
    (
        "Outlook:",
        "Morgan Stanley (May 2025), about $50k by 2050 in high-income countries; Tesla, Musk's 'at scale' remark "
        "(Oct 2024).",
    ),
    ("Data and sources:", "github.com/cloarte/humanoid-market-2026"),
]
X_MIN, X_MAX = 2023.6, 2030.6
Y_MIN, Y_MAX = 4_000, 320_000
SIZE = {"full_size": "full-size", "compact": "compact"}  # robot size, written in the label


def draw(fig) -> None:
    p = data.load("prices_bom")
    p["year"] = p["year"].astype(int)
    p["value"] = p["value_usd"].astype(float)
    p["high"] = p["value_usd_high"].replace("", None).astype(float)
    style.add_title(fig, TITLE, SUBTITLE)
    _legend(fig)
    ax = fig.add_axes((0.08, 0.30, 0.86, 0.53))
    ax.set_yscale("log")
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    style.hairline(ax, "y")
    ax.yaxis.set_major_locator(mticker.FixedLocator([5e3, 10e3, 20e3, 50e3, 100e3, 200e3]))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: style.fmt_usd(v)))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xticks(range(2024, 2031))

    def label(x, y, text, dx=8, dy=0, ha="left", bold=False):
        ax.annotate(
            text,
            (x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va="center",
            fontsize=style.SIZE_TICK,
            color=style.INK,
            fontweight="semibold" if bold else "normal",
        )

    # Morgan Stanley price path, high-income countries.
    ms = p[(p["company_id"] == "_generic") & (p["kind"] == "price_estimate") & p["product"].str.contains("high-income")]
    ms = ms[ms["year"] <= 2030].sort_values("year")
    ax.plot(
        ms["year"],
        ms["value"],
        color=style.SLATE,
        linewidth=1.6,
        linestyle=(0, (4, 3)),
        marker="s",
        markersize=6,
        markerfacecolor=style.PAPER,
        markeredgecolor=style.SLATE,
    )
    label(2028, 150e3, "Morgan Stanley: expected price,\nhigh-income countries", dx=10, dy=12)

    # Western pilot-stage production cost (BofA via Fortune).
    west = p[p["company_id"] == "_generic_west"].iloc[0]
    ax.plot([west["year"]] * 2, [west["value"], west["high"]], color=style.SLATE, linewidth=9, solid_capstyle="butt")
    label(west["year"], 95e3, "Western robot, early production:\n$90–100k to build", dx=12)

    # Chinese bill of materials path (BofA).
    cn = p[p["company_id"] == "_generic_cn"].sort_values("year")
    ax.plot(cn["year"], cn["value"], color=style.AMBER, linewidth=2.2, marker="s", markersize=7)
    first, last = cn.iloc[0], cn.iloc[-1]
    label(first["year"], first["value"], "Parts cost, Chinese robot: $35k", dx=10, dy=10)
    label(
        last["year"],
        last["value"],
        f"{style.fmt_usd(last['value'], last['value_qualifier'])} by 2030",
        dx=-10,
        dy=-14,
        ha="right",
    )

    # Unitree list prices (lowest list price per model and year; other quotes are in the data).
    uni = p[(p["company_id"] == "unitree") & (p["kind"] == "list_price")]
    uni = uni.sort_values("value").groupby(["product", "year"], as_index=False).first()
    for _, r in uni.iterrows():
        ax.scatter(
            [r["year"]],
            [r["value"]],
            s=style.MARKER_SIZE,
            marker="o",
            color=style.AMBER,
            zorder=4,
            edgecolors=style.PAPER,
            linewidths=1.2,
        )
    for _, r in uni.iterrows():
        text = f"Unitree {r['product']} ({SIZE[r['product_class']]}) {style.fmt_usd(r['value'])}"
        if r["product"] == "H1":
            ax.annotate(
                text,
                (r["year"], r["value"]),
                xytext=(0, 14),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=style.SIZE_TICK,
                color=style.INK,
            )
        elif r["year"] == uni[uni["product"] == r["product"]]["year"].min():
            label(r["year"], r["value"], text, dx=-10, ha="right")
        else:
            label(r["year"], r["value"], text, dx=10)

    # 1X NEO list price and Tesla Optimus target.
    neo = p[(p["company_id"] == "1x-technologies") & (p["kind"] == "list_price")].iloc[0]
    ax.scatter(
        [neo["year"]],
        [neo["value"]],
        s=style.MARKER_SIZE,
        marker="o",
        color=style.SLATE,
        zorder=4,
        edgecolors=style.PAPER,
        linewidths=1.2,
    )
    label(neo["year"], neo["value"], f"1X NEO ({SIZE[neo['product_class']]}) {style.fmt_usd(neo['value'])}", dx=10)
    tesla = p[p["company_id"] == "tesla"].iloc[0]
    ax.plot(
        [tesla["year"]] * 2, [tesla["value"], tesla["high"]], color=style.SLATE, linewidth=3, linestyle=(0, (2, 1.5))
    )
    label(tesla["year"], 24.5e3, "Tesla Optimus: Musk's target\nof $20–30k 'at scale'", dx=10)

    top = style.add_notes(fig, NOTES)
    style.add_takeaway(fig, TAKEAWAY, y=top + 0.02)


def _legend(fig) -> None:
    lg = fig.add_axes((0.0, 0.85, 1.0, 0.045))
    lg.set_axis_off()
    lg.set_xlim(0, 1)
    lg.set_ylim(0, 1)
    x = 0.045
    for color, marker, label in (
        (style.AMBER, "o", "China"),
        (style.SLATE, "o", "United States / West"),
        (style.INK, "o", "List price (product on sale)"),
        (style.INK, "s", "Estimate or target"),
    ):
        lg.scatter([x], [0.5], s=style.MARKER_SIZE * 0.6, marker=marker, color=color)
        lg.text(x + 0.012, 0.5, label, fontsize=style.SIZE_TICK, color=style.INK, va="center")
        x += 0.03 + 0.0062 * len(label)


def main() -> None:
    fig = new_figure()
    draw(fig)
    print(style.save_png(fig, NAME))


if __name__ == "__main__":
    main()
