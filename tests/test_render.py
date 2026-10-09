import pandas as pd
from rich.console import Console

from qtdv.profiler import build_preview, profile
from qtdv.ui.render import render_preview, render_profile


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


def test_profile_lists_columns_but_has_no_describe_table():
    df = pd.DataFrame({"n": [1.0, 2.0, None], "s": ["a", "b", "b"]})
    out = text_of(render_profile(profile(df)))
    assert "3 rows" in out and "2 columns" in out
    assert "nulls" in out and "unique" in out
    assert "describe" not in out and "mean" not in out  # the describe() table was removed on request


def test_profile_of_empty_table_renders():  # Review Focus 4
    out = text_of(render_profile(profile(pd.DataFrame())))
    assert "0 rows" in out


def test_numbers_are_never_in_scientific_notation():  # review #2
    from qtdv.ui.render import _cell

    assert _cell(1500000.0).plain == "1500000"
    assert _cell(123456789012.0).plain == "123456789012"
    assert _cell(1234567.89).plain == "1234567.89"
    assert _cell(0.1 + 0.2).plain == "0.3"
    assert _cell(float("nan")).plain == "null"


def test_float_id_column_with_a_blank_shows_full_digits():  # review #2
    df = pd.DataFrame({"id": [123456789012.0, None, 1234567.0]})
    out = text_of(render_preview(build_preview(df)))
    assert "123456789012" in out and "e+" not in out


def test_preview_rows_alternate_in_shade():
    from rich.console import Console

    df = pd.DataFrame({"v": ["r0", "r1", "r2", "r3"]})
    console = Console(width=40, force_terminal=True, color_system="truecolor")
    lines = console.render_lines(render_preview(build_preview(df)), console.options, pad=False)

    def backgrounds(token):
        line = next(seg_line for seg_line in lines if token in "".join(seg.text for seg in seg_line))
        return {seg.style.bgcolor.name for seg in line if seg.style and seg.style.bgcolor and token in seg.text}

    assert backgrounds("r0") != backgrounds("r1")  # neighbouring rows differ
    assert backgrounds("r0") == backgrounds("r2")  # every second row matches


def test_profile_clips_long_column_names_at_12_characters():
    df = pd.DataFrame({"abcdefghijklmnopqrstuvwxyz": [1, 2]})
    out = text_of(render_profile(profile(df)))
    assert "abcdefghijk…" in out  # 11 characters and an ellipsis make 12
    assert "abcdefghijkl" not in out


def test_preview_summary_line_tells_how_to_open_the_file():
    out = text_of(render_preview(build_preview(pd.DataFrame({"n": [1, 2]}))))
    first_line = out.splitlines()[0]
    assert "2 rows × 1 columns" in first_line and "o: open in default program" in first_line
