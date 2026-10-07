import asyncio

import pandas as pd
from textual.widgets import DataTable, Input

from qxc.ui import app as app_module
from qxc.ui.app import QxcApp
from qxc.ui.screens import ColumnPicker, ConfirmLargeFile


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
            app = QxcApp(folder, depth=depth)
            async with app.run_test(size=(160, 50)) as pilot:
                await settle(app, pilot)
                assert app.query_one("#files", DataTable).row_count == expected

    run(scenario)


def test_search_filters_the_list(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QxcApp(folder, depth=0)
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
        app = QxcApp(folder, depth=0)
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
        app = QxcApp(folder, depth=0)
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
        app = QxcApp(folder, depth=0)
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
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            assert app.query_one("#files", DataTable).row_count == 0

    run(scenario)


def test_corrupt_file_shows_error_not_crash(tmp_path):
    (tmp_path / "bad.xlsx").write_bytes(b"not a zip")

    async def scenario():
        app = QxcApp(tmp_path, depth=0)
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
        app = QxcApp(folder, depth=0)
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
        app = QxcApp(folder, depth=0)
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
        app = QxcApp(tmp_path, depth=0)
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
        app = QxcApp(tmp_path, depth=0)
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
        app = QxcApp(tmp_path, depth=0)
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
        app = QxcApp(tmp_path, depth=0)
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
