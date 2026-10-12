"""Turn a DataFrame into plain results for the screen.

No file reading and no UI code lives here.
"""

from __future__ import annotations

import datetime
import numbers
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
    columns: pd.DataFrame  # index = column name; columns: dtype (a label), nulls, unique


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


# What pandas' fast, C-level ``infer_dtype`` says -> the label shown to people.
_INFERRED_LABELS = {
    "string": "text",
    "integer": "number",
    "floating": "number",
    "mixed-integer-float": "number",
    "decimal": "number",
    "boolean": "bool",
    "date": "date",
    "datetime": "date",
    "datetime64": "date",
    "empty": "empty",
}
_KIND_ORDER = ("text", "number", "date", "bool")


def _value_kind(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str):
        return "text"
    if isinstance(value, numbers.Number):
        return "number"
    if isinstance(value, datetime.date):  # also covers datetime and pd.Timestamp
        return "date"
    return "other"


def _describe_object(series: pd.Series) -> str:
    """Say what an ``object`` column holds: ``text``, ``mixed (text+number)``, ..."""
    label = _INFERRED_LABELS.get(pd.api.types.infer_dtype(series, skipna=True))
    if label is not None:
        return label
    kinds = {_value_kind(v) for v in series.dropna()}
    if len(kinds) == 1 and kinds <= set(_KIND_ORDER):
        return kinds.pop()
    if len(kinds) > 1 and kinds <= set(_KIND_ORDER):
        return "mixed (" + "+".join(k for k in _KIND_ORDER if k in kinds) + ")"
    return "mixed"


def _dtype_label(series: pd.Series) -> str:
    """pandas' own dtype name, except ``object`` is replaced by what the column holds."""
    if series.dtype == object:
        return _describe_object(series)
    return str(series.dtype)


def profile(df: pd.DataFrame) -> Profile:
    """Row/column counts, and per-column type, null count and unique count."""
    columns = pd.DataFrame(
        {
            "dtype": pd.Series([_dtype_label(df.iloc[:, i]) for i in range(df.shape[1])], index=df.columns, dtype=str),
            "nulls": df.isna().sum(),
            "unique": df.nunique(dropna=True),
        }
    )
    return Profile(df.shape[0], df.shape[1], columns)
