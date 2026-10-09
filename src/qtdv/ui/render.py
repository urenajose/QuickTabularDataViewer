"""Turn preview and profile results into Rich tables.

Every cell and header is wrapped in ``Text`` so that data such as ``[red]``
is shown literally instead of being read as Rich markup.
"""

from __future__ import annotations

import pandas as pd
from rich.console import Group
from rich.table import Table
from rich.text import Text

from qtdv.profiler import Preview, Profile

NAME_CLIP = 12  # longest column name shown in the Profile
OPEN_HINT = "o: open in default program"  # shown beside the row and column count in the Preview
GAP = "…"
DIVIDER = "⋮"
STRIPE = "on #262c33"  # every second preview row, a little lighter than the background


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
    table = Table(header_style="bold cyan", row_styles=["", STRIPE])
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
    line = Text(summary, style="bold")
    line.append(f"   {OPEN_HINT}", style="dim")
    return Group(line, table)


def render_profile(profile: Profile) -> Group:
    """Summary line and a per-column table (type, nulls, unique)."""
    summary = Text(f"{profile.rows:,} rows · {profile.cols:,} columns", style="bold")

    columns = Table(title="Columns", header_style="bold cyan")
    for heading in ("Column", "dtype", "nulls", "unique"):
        # Column names are clipped at 12 cells (with an ellipsis) so the Profile panel stays narrow.
        columns.add_column(Text(heading), no_wrap=True, overflow="ellipsis", max_width=NAME_CLIP if heading == "Column" else 24)
    for name, row in profile.columns.iterrows():
        columns.add_row(Text(str(name)), Text(row["dtype"]), Text(f"{row['nulls']:,}"), Text(f"{row['unique']:,}"))

    return Group(summary, columns)
