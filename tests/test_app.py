import asyncio

import pandas as pd
from textual.widgets import DataTable, Input, Static

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
    (folder / "table.tsv").write_text("a\tb\n1\t2\n")

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("t")  # csv
            assert {r.ext for r in app.shown_files} == {".csv"}
            await pilot.press("t")  # tsv
            assert {r.ext for r in app.shown_files} == {".tsv"}
            await pilot.press("t", "t", "t")  # xlsx, xls, ods
            assert {r.ext for r in app.shown_files} == {".ods"}
            await pilot.press("t")  # back to all
            assert len(app.shown_files) == 4

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
                    assert widget.border_title.removeprefix("▸ ") == title, selector  # no file name in any title (the focus marker is allowed)
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


def test_preview_scrolls_sideways_when_many_columns_are_chosen(tmp_path):
    names = [f"column_{n:02d}" for n in range(14)]
    (tmp_path / "wide.csv").write_text(",".join(names) + "\n" + ",".join(["some value"] * 14) + "\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(120, 40)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            app.selected_columns = names  # as if all 14 were ticked in the column picker
            app._render_views()
            await pilot.pause()
            box = app.query_one("#preview-box")
            assert box.show_horizontal_scrollbar
            assert box.max_scroll_x > 0
            assert app.query_one("#preview").region.width > box.region.width  # not squeezed to fit
            assert "column_13" in [str(c) for c in app.df.columns]

    run(scenario)


async def open_first_file(app, pilot):
    app.query_one("#files", DataTable).focus()
    await pilot.press("enter")
    await settle(app, pilot)


def focused_id(app):
    return app.focused.id if app.focused else None


def test_g_jumps_through_the_panels_and_shift_g_goes_back(tmp_path, sample_xlsx):
    async def scenario():
        app = QtdvApp(sample_xlsx.parent, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)  # a workbook, so Sheets / Tables is visible
            assert focused_id(app) == "files"
            order = []
            for _ in range(4):
                await pilot.press("g")
                order.append(focused_id(app))
            assert order == ["profile-box", "sheets", "preview-box", "files"]  # and round to the start
            await pilot.press("G")
            assert focused_id(app) == "preview-box"  # Shift+G goes the other way

    run(scenario)


def test_g_skips_the_hidden_sheets_panel_for_csv_files(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)
            order = []
            for _ in range(3):
                await pilot.press("g")
                order.append(focused_id(app))
            assert order == ["profile-box", "preview-box", "files"]

    run(scenario)


def test_the_focused_panel_is_marked_in_its_title(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)
            assert app.query_one("#files").border_title == "▸ Files"
            assert app.query_one("#preview-box").border_title == "Preview"
            await pilot.press("g")
            await pilot.pause()
            assert app.query_one("#files").border_title == "Files"
            assert app.query_one("#profile-box").border_title == "▸ Profile"

    run(scenario)


def test_g_in_the_search_box_types_a_letter(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await pilot.press("/")
            await pilot.press("g")
            assert app.query_one("#search", Input).value == "g"

    run(scenario)


def test_j_and_k_move_the_file_cursor(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            table = app.query_one("#files", DataTable)
            table.focus()
            assert table.cursor_row == 0
            await pilot.press("j")
            assert table.cursor_row == 1
            await pilot.press("k")
            assert table.cursor_row == 0

    run(scenario)


def test_hjkl_scroll_the_preview(tmp_path):
    names = [f"column_{n:02d}" for n in range(14)]
    rows = "\n".join(",".join(["some value"] * 14) for _ in range(40))
    (tmp_path / "big.csv").write_text(",".join(names) + "\n" + rows + "\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(120, 40)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)
            app.selected_columns = names
            app._render_views()
            await pilot.pause()
            box = app.query_one("#preview-box")
            box.focus()
            await pilot.pause()
            assert box.max_scroll_y > 0 and box.max_scroll_x > 0
            await pilot.press("j", "j", "j")
            await pilot.pause()
            assert box.scroll_y > 0
            await pilot.press("k", "k", "k", "k")
            await pilot.pause()
            assert box.scroll_y == 0
            await pilot.press("l", "l", "l")
            await pilot.pause()
            assert box.scroll_x > 0
            await pilot.press("h", "h", "h", "h")
            await pilot.pause()
            assert box.scroll_x == 0

    run(scenario)


def test_panel_keys_do_not_crash_while_a_pop_up_is_open(tmp_path, monkeypatch):
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
            await pilot.press("g", "G", "j", "k", "h", "l")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmLargeFile)  # still open, nothing crashed

    run(scenario)


def test_malformed_csv_row_is_cut_and_the_user_is_told(tmp_path):
    (tmp_path / "late.csv").write_text("a,b\n1,2\n3,4,5\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)
            assert app.df.shape == (2, 2)  # it loads instead of failing
            assert "extra fields" in app.status_message and "line 3" in app.status_message
            shown = app.query_one("#preview").content  # what the Preview panel is showing
            assert "extra fields" in "".join(seg.text for seg in app.console.render(shown))

    run(scenario)


def test_narrow_terminal_jumps_to_the_preview_when_a_file_is_picked(tmp_path):
    (tmp_path / "a.csv").write_text("a\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(90, 40)) as pilot:
            await settle(app, pilot)
            main = app.query_one("#main")
            assert not main.has_class("show-preview")
            await open_first_file(app, pilot)
            assert main.has_class("show-preview")  # the Preview is on screen, not the file list
            assert focused_id(app) == "preview-box"
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 40)) as pilot:  # wide: all panels are already visible
            await settle(app, pilot)
            await open_first_file(app, pilot)
            assert not app.query_one("#main").has_class("show-preview")
            assert focused_id(app) == "files"

    run(scenario)


def preview_text(app):
    return str(app.query_one("#preview", Static).render())


def test_escape_steps_back_one_layer_at_a_time_and_finally_closes_the_file(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await pilot.press("escape")  # nothing is open: nothing to close, nothing breaks
            assert app.current is None
            await open_first_file(app, pilot)
            await pilot.press("g", "g")  # focus the Preview
            assert focused_id(app) == "preview-box"
            await pilot.press("escape")  # 1st: back to the file list, the file stays open
            assert focused_id(app) == "files"
            assert app.current.name == "alpha.csv" and marked_names(app) == ["alpha.csv"]
            await pilot.press("escape")  # 2nd: the file is closed
            await settle(app, pilot)
            assert app.current is None and app.df is None and app.profile_result is None
            assert marked_names(app) == []
            assert "Select a file" in preview_text(app)
            assert app.sub_title == ""
            assert not app.query_one("#sheets").display

    run(scenario)


def test_escape_from_the_search_box_goes_to_the_file_list_first(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)
            await pilot.press("slash")
            assert focused_id(app) == "search"
            await pilot.press("escape")
            assert focused_id(app) == "files" and app.current is not None

    run(scenario)


def test_escape_on_a_narrow_terminal_leaves_the_preview_then_closes_the_file(tmp_path):
    (tmp_path / "a.csv").write_text("a\n1\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(90, 40)) as pilot:
            await settle(app, pilot)
            main = app.query_one("#main")
            await open_first_file(app, pilot)
            assert main.has_class("show-preview")
            await pilot.press("escape")  # 1st: back to the file list, the file stays open
            await pilot.pause()
            assert not main.has_class("show-preview") and focused_id(app) == "files"
            assert app.current is not None
            await pilot.press("escape")  # 2nd: close the file
            assert app.current is None and not main.has_class("show-preview")

    run(scenario)


def test_escape_closing_a_file_cancels_a_load_still_in_progress(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter", "escape")  # close it before the result arrives
            await settle(app, pilot)
            assert app.current is None and app.df is None  # the late result is ignored
            assert "Select a file" in preview_text(app)

    run(scenario)


def test_tsv_file_opens_with_columns_split_on_tabs(tmp_path):
    (tmp_path / "t.tsv").write_text("a\tb\n1\t2\n")

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)
            assert app.df.columns.tolist() == ["a", "b"] and app.sheets == []

    run(scenario)


def test_o_opens_the_highlighted_file_in_the_default_program(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    opened = []
    monkeypatch.setattr(app_module, "open_in_default_program", opened.append)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("down", "o")  # the cursor is on beta.csv
            assert opened == [folder / "beta.csv"]
            assert "beta.csv" in app.status_message and app.current is None  # opening elsewhere does not open it here

    run(scenario)


def test_o_shows_the_reason_when_the_file_cannot_be_opened(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)

    def refuse(path):
        raise app_module.OpenError("xdg-open is not installed")

    monkeypatch.setattr(app_module, "open_in_default_program", refuse)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("o")
            assert "xdg-open is not installed" in app.status_message

    run(scenario)


def test_o_with_no_files_does_nothing(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(app_module, "open_in_default_program", opened.append)

    async def scenario():
        app = QtdvApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("o")
            assert opened == [] and "No file" in app.status_message

    run(scenario)


def test_o_in_the_search_box_types_a_letter(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    opened = []
    monkeypatch.setattr(app_module, "open_in_default_program", opened.append)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await pilot.press("slash", "o")
            assert app.query_one("#search", Input).value == "o" and opened == []

    run(scenario)


def test_o_opens_the_active_file_even_when_the_cursor_is_on_another(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    opened = []
    monkeypatch.setattr(app_module, "open_in_default_program", opened.append)

    async def scenario():
        app = QtdvApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            await open_first_file(app, pilot)  # alpha.csv is now the active file
            await pilot.press("down", "o")  # the cursor moves to beta.csv, but alpha.csv is the open one
            assert opened == [folder / "alpha.csv"]

    run(scenario)
