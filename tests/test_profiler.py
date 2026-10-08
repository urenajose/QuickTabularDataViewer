import numpy as np
import pandas as pd

from qtdv.profiler import build_preview, profile


def frame(rows, cols):
    return pd.DataFrame({f"c{i}": range(rows) for i in range(cols)})


def test_small_table_shows_everything_once():
    p = build_preview(frame(15, 4))
    assert len(p.head) == 15 and p.tail.empty
    assert p.gap_after is None and p.hidden_cols == 0


def test_exactly_twenty_rows_has_no_duplicates():
    p = build_preview(frame(20, 2))
    assert len(p.head) == 20 and p.tail.empty


def test_large_table_gets_head_and_tail():
    p = build_preview(frame(100, 2))
    assert p.head["c0"].tolist() == list(range(10))
    assert p.tail["c0"].tolist() == list(range(90, 100))
    assert p.total_rows == 100


def test_wide_table_keeps_first_and_last_columns():
    p = build_preview(frame(3, 20))
    assert list(p.head.columns) == ["c0", "c1", "c2", "c3", "c4", "c15", "c16", "c17", "c18", "c19"]
    assert p.gap_after == 5 and p.hidden_cols == 10 and p.total_cols == 20


def test_column_count_adapts():
    p = build_preview(frame(3, 20), n_cols=2)
    assert list(p.head.columns) == ["c0", "c1", "c18", "c19"]
    assert p.gap_after == 2


def test_chosen_columns_override_the_split():
    p = build_preview(frame(3, 20), columns=["c7", "c3"])
    assert list(p.head.columns) == ["c7", "c3"]
    assert p.gap_after is None and p.hidden_cols == 18


def test_empty_frames_do_not_crash():  # Review Focus 4
    for df in (pd.DataFrame(), pd.DataFrame({"a": [], "b": []})):
        p = build_preview(df)
        assert p.total_rows == 0
        prof = profile(df)
        assert prof.rows == 0


def test_profile_numbers():
    df = pd.DataFrame({"n": [1.0, 2.0, np.nan, 2.0], "s": ["a", "b", "b", None]})
    prof = profile(df)
    assert (prof.rows, prof.cols) == (4, 2)
    assert prof.columns.loc["n", "nulls"] == 1
    assert prof.columns.loc["n", "unique"] == 2
    assert prof.columns.loc["s", "nulls"] == 1
    assert prof.columns.loc["s", "unique"] == 2
    assert prof.describe.loc["count", "n"] == 3
    assert prof.describe.loc["mean", "n"] == (1 + 2 + 2) / 3


def test_profile_handles_mixed_and_cleaned_headers():  # Review Focus 2
    df = pd.DataFrame({"Unnamed: 0": [1, 2], "a": ["x", 3], "a.1": [None, None]})
    prof = profile(df)
    assert list(prof.columns.index) == ["Unnamed: 0", "a", "a.1"]
    assert prof.columns.loc["a.1", "nulls"] == 2
