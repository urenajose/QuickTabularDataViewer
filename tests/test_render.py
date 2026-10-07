import pandas as pd
from rich.console import Console

from qxc.profiler import build_preview, profile
from qxc.ui.render import render_preview, render_profile


def text_of(renderable, width=140):
    console = Console(record=True, width=width, force_terminal=False)
    console.print(renderable)
    return console.export_text()


def test_preview_shows_head_divider_and_tail():
    df = pd.DataFrame({"n": range(100)})
    out = text_of(render_preview(build_preview(df)))
    assert "100 rows" in out
    assert " 0 " in out and "99" in out
    assert "50" not in out  # middle rows are hidden


def test_preview_shows_gap_column_for_wide_tables():
    df = pd.DataFrame({f"c{i}": [i] for i in range(20)})
    out = text_of(render_preview(build_preview(df)), width=250)
    assert "c0" in out and "c19" in out and "c10" not in out
    assert "…" in out


def test_square_brackets_are_shown_literally():  # Review Focus 3
    df = pd.DataFrame({"[red]col[/red]": ["[bold]x[/bold]", "[1]"]})
    out = text_of(render_preview(build_preview(df)))
    assert "[red]col[/red]" in out
    assert "[bold]x[/bold]" in out
    assert "[1]" in out


def test_nulls_are_marked():
    df = pd.DataFrame({"a": [1.0, None]})
    assert "null" in text_of(render_preview(build_preview(df)))


def test_empty_table_renders():  # Review Focus 4
    out = text_of(render_preview(build_preview(pd.DataFrame())))
    assert "0 rows" in out


def test_profile_lists_columns_and_stats():
    df = pd.DataFrame({"n": [1.0, 2.0, None], "s": ["a", "b", "b"]})
    out = text_of(render_profile(profile(df)))
    assert "3 rows" in out and "2 columns" in out
    assert "nulls" in out and "unique" in out
    assert "mean" in out


def test_profile_of_empty_table_renders():  # Review Focus 4
    out = text_of(render_profile(profile(pd.DataFrame())))
    assert "0 rows" in out
