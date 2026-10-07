"""Turn preview and profile results into Rich tables.

Every cell and header is wrapped in ``Text`` so that data such as ``[red]``
is shown literally instead of being read as Rich markup.
"""

from __future__ import annotations

import pandas as pd
from rich.console import Group
from rich.table import Table
from rich.text import Text

from qxc.profiler import Preview, Profile

GAP = "…"
DIVIDER = "⋮"


def _cell(value) -> Text:
    if value is None or (not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)):
        return Text("null", style="dim italic")
    if isinstance(value, float):
        # Plain digits, never scientific notation: IDs and amounts must stay readable.
        if value.is_integer() and abs(value) < 1e15:
            return Text(str(int(value)))
        return Text(f"{value:.15g}")
    return Text(str(value))


def render_preview(preview: Preview) -> Group:
    """A summary line, then head rows, a divider and tail rows.

    A ``…`` column marks where columns were hidden. The summary is its own line
    (not the table title) so it never wraps inside a narrow table.
    """
    summary = f"{preview.total_rows:,} rows × {preview.total_cols:,} columns"
    if preview.hidden_cols:
        summary += f" · {preview.hidden_cols:,} not shown"
    table = Table(header_style="bold cyan")
    names = list(preview.head.columns)
    if not names:  # Rich prints nothing for a table with no columns
        table.add_column(Text("(no columns)", style="dim"))
    for position, name in enumerate(names, start=1):
        table.add_column(Text(str(name)), no_wrap=True, overflow="ellipsis", max_width=20)
        if preview.gap_after == position:
            table.add_column(Text(GAP), justify="center", no_wrap=True)

    def add_rows(frame: pd.DataFrame) -> None:
        for row in frame.itertuples(index=False):
            cells: list[Text] = []
            for position, value in enumerate(row, start=1):
                cells.append(_cell(value))
                if preview.gap_after == position:
                    cells.append(Text(GAP, style="dim"))
            table.add_row(*cells)

    add_rows(preview.head)
    if len(preview.tail):
        width = len(names) + (1 if preview.gap_after else 0)
        table.add_row(*[Text(DIVIDER, style="dim")] * width)
        add_rows(preview.tail)
    return Group(Text(summary, style="bold"), table)


def render_profile(profile: Profile) -> Group:
    """Summary line, a per-column table, and the ``describe()`` table."""
    summary = Text(f"{profile.rows:,} rows · {profile.cols:,} columns", style="bold")

    columns = Table(title="Columns", header_style="bold cyan")
    for heading in ("Column", "dtype", "nulls", "unique"):
        columns.add_column(Text(heading), no_wrap=True, overflow="ellipsis", max_width=24)
    for name, row in profile.columns.iterrows():
        columns.add_row(Text(str(name)), Text(row["dtype"]), Text(f"{row['nulls']:,}"), Text(f"{row['unique']:,}"))

    parts: list = [summary, columns]
    stats = profile.describe.T.dropna(axis=1, how="all")
    if not stats.empty:
        described = Table(title="describe()", header_style="bold cyan")
        described.add_column(Text("Column"), no_wrap=True, overflow="ellipsis", max_width=24)
        for stat in stats.columns:
            described.add_column(Text(str(stat)), justify="right", no_wrap=True)
        for name, row in stats.iterrows():
            described.add_row(Text(str(name)), *[_cell(value) for value in row])
        parts.append(described)
    return Group(*parts)
