"""Turn a DataFrame into plain results for the screen.

No file reading and no UI code lives here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Preview:
    """The slice of a table that the preview panel shows."""

    head: pd.DataFrame
    tail: pd.DataFrame  # empty when every row already fits in ``head``
    gap_after: int | None  # put a "..." column after this many columns
    hidden_cols: int
    total_rows: int
    total_cols: int


@dataclass(frozen=True)
class Profile:
    """Facts about a whole table."""

    rows: int
    cols: int
    columns: pd.DataFrame  # index = column name; columns: dtype, nulls, unique
    describe: pd.DataFrame  # describe(include="all"), statistics as rows


def build_preview(
    df: pd.DataFrame,
    n_rows: int = 10,
    n_cols: int = 5,
    columns: Sequence[str] | None = None,
) -> Preview:
    """First/last ``n_rows`` rows and first/last ``n_cols`` columns of ``df``.

    ``columns`` shows exactly those columns instead of the first/last split.
    """
    total_rows, total_cols = df.shape
    gap_after: int | None = None
    if columns is not None:
        view = df.loc[:, list(columns)]
    elif total_cols > 2 * n_cols:
        keep = list(range(n_cols)) + list(range(total_cols - n_cols, total_cols))
        view = df.iloc[:, keep]
        gap_after = n_cols
    else:
        view = df
    hidden = total_cols - view.shape[1]

    if total_rows <= 2 * n_rows:
        head, tail = view, view.iloc[0:0]
    else:
        head, tail = view.head(n_rows), view.tail(n_rows)
    return Preview(head, tail, gap_after, hidden, total_rows, total_cols)


def profile(df: pd.DataFrame) -> Profile:
    """Row/column counts, per-column type, null count and unique count, and ``describe()``."""
    columns = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "nulls": df.isna().sum(),
            "unique": df.nunique(dropna=True),
        }
    )
    try:
        described = df.describe(include="all") if df.shape[1] else pd.DataFrame()
    except ValueError:  # pandas refuses to describe some empty frames
        described = pd.DataFrame()
    return Profile(df.shape[0], df.shape[1], columns, described)
