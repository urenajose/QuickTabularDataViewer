import asyncio

import pandas as pd
from textual.widgets import DataTable, Input

from qtdv.ui import app as app_module
from qtdv.ui.app import QtdvApp
from qtdv.ui.screens import ColumnPicker, ConfirmLargeFile


def run(scenario):
    asyncio.run(scenario())


async def settle(app, pilot):
    await app.workers.wait_for_complete()
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


def make_folder(tmp_path):
    (tmp_path / "alpha.csv").write_text("x,y\n1,2\n3,4\n")
    (tmp_path / "beta.csv").write_text("name\nAnn\n")
    sub = tmp_path / "deeper"
    sub.mkdir()
    (sub / "gamma.csv").write_text("a\n1\n")
    return tmp_path


def test_lists_files_at_requested_depth(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        for depth, expected in ((0, 2), (1, 3)):
            app = QtdvApp(folder, depth=depth)
            async with app.run_test(size=(160, 50)) as pilot:
                await settle(app, pilot)
                assert app.query_one("#files", DataTable).row_count == expected

    run(scenario)


def test_search_filters_the_list(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#search", Input).value = "alp"
            await pilot.pause()
            assert [r.name for r in app.shown_files] == ["alpha.csv"]
            app.query_one("#search", Input).value = "zzz"
            await pilot.pause()
            assert app.query_one("#files", DataTable).row_count == 0

    run(scenario)


def test_type_key_cycles_filter(tmp_path):
    folder = make_folder(tmp_path)
    (folder / "book.ods").write_bytes(b"")

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("t")  # csv
            assert {r.ext for r in app.shown_files} == {".csv"}
            await pilot.press("t", "t", "t")  # xlsx, xls, ods
            assert {r.ext for r in app.shown_files} == {".ods"}
            await pilot.press("t")  # back to all
            assert len(app.shown_files) == 3

    run(scenario)


def test_bad_date_marks_the_box_and_is_ignored(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            box = app.query_one("#date-from", Input)
            box.value = "2025-13-40"
            await pilot.pause()
            assert box.has_class("invalid")
            assert len(app.shown_files) == 2
            box.value = "2000-01-01"
            await pilot.pause()
            assert not box.has_class("invalid")

    run(scenario)


def test_enter_opens_file_and_fills_preview_and_profile(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            assert app.current.name == "alpha.csv"
            assert app.df.shape == (2, 2)
            assert app.profile_result.rows == 2

    run(scenario)


def test_empty_folder_shows_no_files(tmp_path):
    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            assert app.query_one("#files", DataTable).row_count == 0

    run(scenario)


def test_corrupt_file_shows_error_not_crash(tmp_path):
    (tmp_path / "bad.xlsx").write_bytes(b"not a zip")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            assert app.df is None

    run(scenario)


def test_large_file_asks_before_loading(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    monkeypatch.setattr(app_module, "is_large", lambda size: True)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmLargeFile)
            await pilot.press("n")
            await settle(app, pilot)
            assert app.df is None
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("y")
            await settle(app, pilot)
            assert app.df is not None

    run(scenario)


def test_stale_result_is_ignored(tmp_path):  # Review Focus 5
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            current = app.shown_files[0]
            app.current = current
            app._token = 5
            stale = pd.DataFrame({"old": [1]})
            app._show_table(4, current, None, None, stale, app_module.profile(stale))
            assert app.df is None  # token 4 is older than 5, so ignored
            fresh = pd.DataFrame({"new": [1]})
            app._show_table(5, current, None, None, fresh, app_module.profile(fresh))
            assert list(app.df.columns) == ["new"]

    run(scenario)


def test_column_picker_limits_preview_columns(tmp_path):
    (tmp_path / "wide.csv").write_text("a,b,c,d\n1,2,3,4\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, ColumnPicker)
            app.screen.dismiss(["b", "d"])
            await pilot.pause()
            assert app.selected_columns == ["b", "d"]

    run(scenario)


def test_column_picker_empty_result_resets_to_default(tmp_path):
    (tmp_path / "wide.csv").write_text("a,b\n1,2\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            app.selected_columns = ["a"]
            await pilot.press("c")
            await pilot.pause()
            app.screen.dismiss([])
            await pilot.pause()
            assert app.selected_columns is None

    run(scenario)


def test_c_does_nothing_before_a_file_is_open(tmp_path):
    (tmp_path / "a.csv").write_text("a\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("c")
            await pilot.pause()
            assert not isinstance(app.screen, ColumnPicker)

    run(scenario)


def test_column_picker_enter_applies_the_checked_columns(tmp_path):
    (tmp_path / "wide.csv").write_text("a,b,c,d\n1,2,3,4\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            await pilot.press("c")
            await pilot.pause()
            await pilot.press("down", "space")  # uncheck "b"
            await pilot.press("enter")  # must apply, not toggle
            await pilot.pause()
            assert not isinstance(app.screen, ColumnPicker)
            assert app.selected_columns == ["a", "c", "d"]

    run(scenario)


def test_narrow_terminal_uses_one_panel_and_p_toggles(tmp_path):
    (tmp_path / "a.csv").write_text("a\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(90, 40)) as pilot:
            await settle(app, pilot)
            main = app.query_one("#main")
            assert main.has_class("narrow")
            assert not main.has_class("show-preview")
            assert app.query_one("#top").display and not app.query_one("#preview-box").region.width
            await pilot.press("p")  # p switches to the Preview
            assert main.has_class("show-preview")
            assert app.query_one("#preview-box").region.width > 60 and not app.query_one("#top").region.width
            await pilot.press("p")  # and back
            assert not main.has_class("show-preview")
            assert app.query_one("#top").region.width > 60
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 40)) as pilot:
            await settle(app, pilot)
            assert not app.query_one("#main").has_class("narrow")

    run(scenario)


def test_file_names_with_brackets_show_literally(tmp_path):  # review #5
    from rich.text import Text

    (tmp_path / "Report [final].csv").write_text("a\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            row = app.query_one("#files", DataTable).get_row(str(tmp_path / "Report [final].csv"))
            assert isinstance(row[2], Text) and row[2].plain.strip() == "Report [final].csv"

    run(scenario)


def test_no_files_match_message_when_filters_hide_everything(tmp_path):  # review #8
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#search", Input).value = "zzz"
            await pilot.pause()
            assert "No files match" in app.status_message

    run(scenario)


def test_picker_survives_markup_like_column_names(tmp_path):  # review #1
    (tmp_path / "odd.csv").write_text("[/],[red]x[/red],b\n1,2,3\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, ColumnPicker)

    run(scenario)


def test_switching_sheet_clears_old_table_state(tmp_path):  # review #4
    from openpyxl import Workbook

    wb = Workbook()
    wb.active.title = "A"
    wb.active.append(["x"])
    wb.active.append([1])
    wb.create_sheet("B").append(["y"])
    path = tmp_path / "two.xlsx"
    wb.save(path)

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            assert app.df is not None
            app.selected_columns = ["x"]
            app._load_target(app.current, "B", None)  # starts loading sheet B
            assert app.df is None and app.selected_columns is None
            await pilot.press("c")
            await pilot.pause()
            assert not isinstance(app.screen, ColumnPicker)

    run(scenario)


def test_picker_result_with_unknown_columns_is_ignored(tmp_path):  # review #4
    (tmp_path / "wide.csv").write_text("a,b\n1,2\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            await pilot.press("c")
            await pilot.pause()
            app.screen.dismiss(["not-a-column"])
            await pilot.pause()
            assert app.selected_columns is None

    run(scenario)


def test_unexpected_error_while_profiling_is_shown_not_fatal(tmp_path, monkeypatch):  # review #6
    folder = make_folder(tmp_path)

    def boom(df):
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "profile", boom)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            assert app.df is None
            assert "boom" in app.status_message

    run(scenario)


def test_columns_that_fit_scales_with_width_up_to_five():  # review #7
    assert app_module.columns_that_fit(200) == 5
    assert app_module.columns_that_fit(100) == 5
    assert app_module.columns_that_fit(60) == 3
    assert app_module.columns_that_fit(0) == 1


def marked_names(app):
    """Names of the rows that carry the opened-file dot."""
    table = app.query_one("#files", DataTable)
    return [row[2].plain.strip() for row in (table.get_row(str(r.path)) for r in app.shown_files) if "●" in row[0].plain]


def test_opened_file_gets_dot_and_green_tint_only_on_its_row(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            assert marked_names(app) == []  # nothing opened yet
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            assert marked_names(app) == ["alpha.csv"]
            await pilot.press("down")  # the cursor wins over the tint, so look at the row from beside it
            await pilot.pause()
            table = app.query_one("#files", DataTable)
            tinted = table.get_row(str(folder / "alpha.csv"))
            plain = table.get_row(str(folder / "beta.csv"))
            assert all("on #b7e4c7" in str(cell.style) for cell in tinted)
            assert not any("#b7e4c7" in str(cell.style) for cell in plain)
            await pilot.press("enter")  # open the second file (the cursor is on it)
            await settle(app, pilot)
            assert marked_names(app) == ["beta.csv"]

    run(scenario)


def test_mark_survives_a_filter_and_returns_after_it_is_cleared(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            app.query_one("#search", Input).value = "bet"  # hides the opened file
            await pilot.pause()
            assert marked_names(app) == []
            app.query_one("#search", Input).value = ""
            await pilot.pause()
            assert marked_names(app) == ["alpha.csv"]

    run(scenario)


def test_declining_the_large_file_prompt_does_not_move_the_mark(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")  # alpha opens normally
            await settle(app, pilot)
            monkeypatch.setattr(app_module, "is_large", lambda size: True)
            await pilot.press("down", "enter")
            await pilot.pause()
            await pilot.press("n")
            await settle(app, pilot)
            assert marked_names(app) == ["alpha.csv"]

    run(scenario)


def test_every_panel_has_a_border_and_a_fixed_title(tmp_path):
    folder = make_folder(tmp_path)
    titles = {"#files": "Files", "#sheets": "Sheets / Tables", "#preview-box": "Preview", "#profile-box": "Profile"}

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)

            def check():
                for selector, title in titles.items():
                    widget = app.query_one(selector)
                    assert widget.border_title == title, selector  # no file name in any title
                    assert widget.styles.border.top[0] != "", selector  # and a border is drawn

            check()
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            check()

    run(scenario)


def row_backgrounds(table, y):
    """Background colour of every segment on screen line ``y`` of the file table."""
    return [seg.style.bgcolor.name if seg.style and seg.style.bgcolor else None for seg in table.render_line(y)]


def test_opened_row_is_one_solid_tint_when_the_cursor_is_elsewhere(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            table.focus()
            await pilot.press("enter")
            await settle(app, pilot)
            await pilot.press("down")  # cursor leaves the opened file
            await pilot.pause()
            assert set(row_backgrounds(table, 1)[:-1]) == {"#b7e4c7"}  # no gaps between the cells (last piece is the table edge)

    run(scenario)


def test_cursor_on_the_opened_row_is_one_solid_cursor_colour(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            table.focus()
            await pilot.press("enter")
            await settle(app, pilot)
            colours = set(row_backgrounds(table, 1))  # the whole row, edge included
            assert "#b7e4c7" not in colours  # the cursor wins over the tint
            assert len(colours) == 1  # and the row is not a patchwork
            assert marked_names(app) == ["alpha.csv"]  # the dot stays

    run(scenario)


def test_wide_layout_has_files_beside_profile_over_sheets_with_preview_across_the_bottom(tmp_path, sample_xlsx):
    async def scenario():
        app = QtdvApp(sample_xlsx.parent, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            files, sheets, profile, preview = (
                app.query_one(sel).region for sel in ("#files", "#sheets", "#profile-box", "#preview-box")
            )
            assert files.right <= profile.x and files.right <= sheets.x  # Files on the left, the others to its right
            assert profile.bottom <= sheets.y  # Profile stacked above Sheets / Tables
            assert preview.y >= max(files.bottom, profile.bottom, sheets.bottom)  # Preview below all of them
            assert preview.width >= files.width + profile.width  # and as wide as the screen

    run(scenario)


def test_files_panel_scrolls_both_ways_when_it_needs_to(tmp_path):
    for n in range(60):
        (tmp_path / f"file_{n:02d}.csv").write_text("x\n1\n")
    deep = tmp_path / ("d" * 90)
    deep.mkdir()
    (deep / "inside.csv").write_text("x\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=1)
        async with app.run_test(size=(120, 30)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            assert table.show_vertical_scrollbar  # more files than rows
            assert table.show_horizontal_scrollbar  # the 90-character folder name is wider than the panel

    run(scenario)


LONG_NAME = "a" * 40 + ".csv"  # 44 characters: wraps into 24 + 20


def test_long_names_wrap_at_24_characters_into_taller_rows(tmp_path):
    (tmp_path / LONG_NAME).write_text("x\n1\n")
    (tmp_path / "z.csv").write_text("x\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            long_row, short_row = table.ordered_rows
            assert long_row.height == 2 and short_row.height == 1
            name_cell = table.get_row(str(tmp_path / LONG_NAME))[2].plain
            lines = name_cell.split("\n")
            assert [line.strip() for line in lines] == ["a" * 24, "a" * 16 + ".csv"]
            assert {len(line) for line in lines} == {26}  # every line padded to the full column width

    run(scenario)


def test_wrapped_row_tint_has_no_gaps_on_any_line(tmp_path):
    (tmp_path / LONG_NAME).write_text("x\n1\n")
    (tmp_path / "z.csv").write_text("x\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            table.focus()
            await pilot.press("enter")  # opens the long-named file (first row)
            await settle(app, pilot)
            await pilot.press("down")
            await pilot.pause()
            for y in (1, 2):  # both lines of the wrapped row
                assert set(row_backgrounds(table, y)[:-1]) == {"#b7e4c7"}, y

    run(scenario)


def test_file_columns_end_with_folder(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=1)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            labels = [str(column.label).strip() for column in table.ordered_columns]
            assert labels == ["", "Lvl", "Name", "Modified", "Size", "Folder"]
            row = table.get_row(str(folder / "deeper" / "gamma.csv"))
            assert row[-1].plain.strip() == "deeper"  # the last cell is the folder

    run(scenario)


def test_file_rows_alternate_in_shade(tmp_path):
    for name in ("a.csv", "b.csv", "c.csv"):
        (tmp_path / name).write_text("x\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            # the cursor is on row 0, so rows 1 and 2 (screen lines 2 and 3) show their own shades
            assert set(row_backgrounds(table, 2)[:-1]) != set(row_backgrounds(table, 3)[:-1])

    run(scenario)
