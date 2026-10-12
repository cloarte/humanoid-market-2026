"""Rebuild every output from data/ in one command.

Run:  python -m charts.all

Writes the matplotlib charts (PNG and GIF), the derived tables in analysis/ and the Datawrapper CSVs to
outputs/. Updating the Datawrapper charts themselves needs an API token and is a separate step:
python -m datawrapper.build
"""

from __future__ import annotations

from analysis import article_figures, disclosure_scorecard, valuation_per_unit
from charts import c01_capital_by_year, c02_units_vs_valuation, c06_cost_curve
from datawrapper import export


def main() -> None:
    for module in (c01_capital_by_year, c02_units_vs_valuation, c06_cost_curve):
        module.main()
    for analysis_module in (article_figures, valuation_per_unit, disclosure_scorecard):
        analysis_module.main()
    export.main()


if __name__ == "__main__":
    main()
