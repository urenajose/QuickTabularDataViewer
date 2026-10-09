"""The qtdv Textual application: layout, background loading and key actions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from rich.cells import cell_len
from rich.console import Group
from rich.measure import Measurement
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import DataTable, Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from qtdv.loader import LoaderError, SheetInfo, is_large, list_sheets, load_table
from qtdv.opener import OpenError, open_in_default_program
from qtdv.profiler import Profile, build_preview, profile
from qtdv.scanner import FileRecord, filter_files, parse_date, scan
from qtdv.ui.render import render_preview, render_profile
from qtdv.ui.screens import ColumnPicker, ConfirmLargeFile

# (label, extensions) in the order the ``t`` key cycles through them
TYPE_CHOICES: list[tuple[str, frozenset[str] | None]] = [
    ("all", None),
    ("csv", frozenset({".csv"})),
    ("tsv", frozenset({".tsv"})),
    ("xlsx", frozenset({".xlsx", ".xlsm"})),
    ("xls", frozenset({".xls"})),
    ("ods", frozenset({".ods"})),
]
SEP = "\x1f"  # separates parts of an option id; cannot appear in a sheet name
PANEL_ORDER = ("files", "profile-box", "sheets", "preview-box")  # the order g walks through the panels
PANEL_TITLES = {"#files": "Files", "#sheets": "Sheets / Tables", "#preview-box": "Preview", "#profile-box": "Profile"}
NAME_COLUMN = 2  # index of "Name" in FILE_COLUMNS
NAME_WRAP_WIDTH = 24  # long file names wrap at this many characters
FILE_COLUMNS = ("", "Lvl", "Name", "Modified", "Size", "Folder")
OPENED_STYLE = "black on #b7e4c7"  # light green tint for the file that is open
COLUMN_WIDTH = 10  # rough width of one preview column, used to pick how many fit


def columns_that_fit(width: int) -> int:
    """How many columns to show at each end of the preview (1 to 5)."""
    return max(1, min(5, (width // COLUMN_WIDTH) // 2))


def human_size(size: int) -> str:
    """12345 -> '12.1 KB'."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:,.0f} {unit}" if unit == "B" else f"{value:,.1f} {unit}"
        value /= 1024
    return f"{size} B"


class QtdvApp(App):
    """Browse table files in a folder and see a preview and profile of each."""

    TITLE = "Quick Tabular Data Viewer"
    CSS_PATH = "qtdv.tcss"
    BINDINGS = [
        ("slash", "focus_search", "Search"),
        ("d", "focus_dates", "Dates"),
        ("t", "cycle_type", "Type"),
        ("c", "pick_columns", "Columns"),
        ("p", "toggle_panel", "Preview/Files"),
        ("g", "panel(1)", "Next panel"),
        Binding("G", "panel(-1)", "Prev panel", show=False),  # not listed in the footer to keep it short
        Binding("j", "move('down')", "Down", show=False),  # not listed in the footer to keep it short
        Binding("k", "move('up')", "Up", show=False),  # not listed in the footer to keep it short
        Binding("h", "move('left')", "Left", show=False),  # not listed in the footer to keep it short
        Binding("l", "move('right')", "Right", show=False),  # not listed in the footer to keep it short
        ("o", "open_external", "Open in app"),
        ("f5", "refresh", "Refresh"),
        ("escape", "back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, folder: Path, depth: int = 0) -> None:
        super().__init__()
        self.folder = Path(folder)
        self.depth = depth
        self.records: list[FileRecord] = []
        self.shown_files: list[FileRecord] = []
        self.type_index = 0
        self.current: FileRecord | None = None
        self._column_keys: list = []
        self._widths: list[int] = []
        self._cursor_record: FileRecord | None = None  # the file the cursor is on
        self.sheets: list[SheetInfo] = []
        self.df: pd.DataFrame | None = None
        self.profile_result: Profile | None = None
        self.selected_columns: list[str] | None = None
        self.status_message = ""
        self._token = 0  # bumped on every new selection so old results can be ignored

    # ---------------------------------------------------------------- layout
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="filters"):
            yield Input(placeholder="Search name…", id="search")
            yield Static("Type: all", id="type")
            yield Input(placeholder="From YYYY-MM-DD", id="date-from")
            yield Input(placeholder="To YYYY-MM-DD", id="date-to")
        with Vertical(id="main"):
            with Horizontal(id="top"):
                yield DataTable(id="files", cursor_type="row", cell_padding=0, zebra_stripes=True)  # padding lives inside the cells so the tint has no gaps
                with Vertical(id="side"):
                    with ScrollableContainer(id="profile-box"):
                        yield Static("", id="profile")
                    yield OptionList(id="sheets")
            with ScrollableContainer(id="preview-box"):
                yield Static("Select a file and press Enter", id="preview")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#files", DataTable)
        for selector, title in PANEL_TITLES.items():
            self.query_one(selector).border_title = title
        self.query_one("#sheets", OptionList).display = False
        table.focus()
        self.rescan()

    # -------------------------------------------------------------- scanning
    @work(thread=True, exclusive=True, group="scan")
    def rescan(self) -> None:
        """Read the disk again (runs in the background)."""
        try:
            records = scan(self.folder, self.depth)
        except (OSError, ValueError) as exc:
            self.call_from_thread(self._set_status, f"Cannot scan folder: {exc}")
            return
        self.call_from_thread(self._set_records, records)

    def _set_records(self, records: list[FileRecord]) -> None:
        self.records = records
        self.apply_filters()

    # ------------------------------------------------------------- filtering
    def _read_date(self, selector: str):
        box = self.query_one(selector, Input)
        try:
            value = parse_date(box.value)
        except ValueError:
            box.add_class("invalid")
            return None
        box.remove_class("invalid")
        return value

    def apply_filters(self) -> None:
        """Re-filter the in-memory list (instant; does not touch the disk)."""
        _, exts = TYPE_CHOICES[self.type_index]
        self.shown_files = filter_files(
            self.records,
            name=self.query_one("#search", Input).value,
            exts=exts,
            date_from=self._read_date("#date-from"),
            date_to=self._read_date("#date-to"),
        )
        table = self.query_one("#files", DataTable)
        self._fill_table(table)
        self._set_files_status()

    def _set_files_status(self) -> None:
        if self.shown_files:
            self._set_status(f"{len(self.shown_files)} of {len(self.records)} files · depth {self.depth}")
        else:
            self._set_status("No files match")

    @staticmethod
    def _row_values(rec: FileRecord, opened: bool) -> list[str]:
        return [
            "●" if opened else "",
            str(rec.level),
            rec.name,
            f"{rec.modified:%Y-%m-%d %H:%M}",
            human_size(rec.size),
            rec.rel_dir or ".",
        ]

    def _fill_table(self, table: DataTable) -> None:
        """Rebuild the file table. Column widths are worked out here so every cell can fill its column."""
        labels = FILE_COLUMNS  # the first column holds the opened-file dot
        rows = [self._row_values(rec, rec == self.current) for rec in self.shown_files]
        self._widths = [max([cell_len(label)] + [cell_len(row[i]) for row in rows]) for i, label in enumerate(labels)]
        self._widths[NAME_COLUMN] = min(self._widths[NAME_COLUMN], NAME_WRAP_WIDTH)  # long names wrap
        table.clear(columns=True)  # columns too, so widths shrink again after a filter
        self._cursor_record = None
        self._column_keys = [table.add_column(self._pad(label, w)) for label, w in zip(labels, self._widths)]
        for rec in self.shown_files:
            table.add_row(*self._row_cells(rec), key=str(rec.path), height=None)  # height=None: as tall as the longest cell
        self._sync_cursor()

    @staticmethod
    def _wrap(value: str, width: int) -> list[str]:
        """Cut ``value`` into pieces that are at most ``width`` cells wide."""
        lines, line = [], ""
        for char in value:
            if line and cell_len(line + char) > width:
                lines.append(line)
                line = ""
            line += char
        return lines + [line]

    @classmethod
    def _pad(cls, value: str, width: int) -> str:
        """One cell: each line wrapped to ``width`` and padded with a space on each side."""
        return "\n".join(f" {line}{' ' * (width - cell_len(line))} " for line in cls._wrap(value, width))

    def _row_cells(self, rec: FileRecord) -> list[Text]:
        """Cells for one row. The opened file gets a dot and a light green tint.

        Each cell is padded to its full column width (the table itself adds no padding), so the tint
        runs unbroken across the row. A cell shorter than the tallest one gets blank lines, so the tint
        also covers the extra lines of a wrapped name. While the cursor is on the opened row the tint
        is left off, so the cursor colour is not mixed with it.
        """
        opened = rec == self.current
        style = OPENED_STYLE if opened and rec != self._cursor_record else ""
        cells = [self._pad(v, w).split("\n") for v, w in zip(self._row_values(rec, opened), self._widths)]
        height = max(len(lines) for lines in cells)
        blank = [" " * (w + 2) for w in self._widths]
        # Text so names such as "Report [final].csv" are not read as markup
        return [Text("\n".join(lines +[blank[i]] * (height - len(lines))), style=style) for i, lines in enumerate(cells)]

    def _restyle_rows(self, *records: FileRecord | None) -> None:
        """Redraw the given rows in place, so the cursor does not move."""
        table = self.query_one("#files", DataTable)
        for rec in records:
            if rec is None or rec not in self.shown_files:
                continue
            for column_key, cell in zip(self._column_keys, self._row_cells(rec)):
                table.update_cell(str(rec.path), column_key, cell)

    def _sync_cursor(self) -> None:
        """Remember which file the cursor is on and redraw the rows whose look depends on it."""
        table = self.query_one("#files", DataTable)
        previous = self._cursor_record
        row = table.cursor_row
        self._cursor_record = self.shown_files[row] if 0 <= row < len(self.shown_files) else None
        self._restyle_rows(previous, self._cursor_record)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._sync_cursor()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.apply_filters()

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.query_one("#status", Static).update(Text(message))

    # --------------------------------------------------------------- actions
    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_dates(self) -> None:
        self.query_one("#date-from", Input).focus()

    def action_back(self) -> None:
        """Escape steps back one layer: leave the narrow Preview, then return to the file list, then close the file."""
        if len(self.screen_stack) > 1:
            return  # a pop-up is open and handles its own Escape
        main = self.query_one("#main")
        files = self.query_one("#files", DataTable)
        if main.has_class("show-preview"):
            main.remove_class("show-preview")
            files.focus()
        elif self.focused is not files:
            files.focus()
        else:
            self._close_file()

    def _close_file(self) -> None:
        """Forget the open file: clear the panels and the mark, and ignore any load still running."""
        if self.current is None:
            return
        self._token += 1  # a result that arrives late belongs to the closed file
        previous, self.current = self.current, None
        self._restyle_rows(previous)
        self.df = None
        self.profile_result = None
        self.selected_columns = None
        self.sheets = []
        self.sub_title = ""
        self.query_one("#sheets", OptionList).display = False
        self.query_one("#profile", Static).update("")
        self._show_preview(Text("Select a file and press Enter"))
        self._set_files_status()

    def action_cycle_type(self) -> None:
        self.type_index = (self.type_index + 1) % len(TYPE_CHOICES)
        self.query_one("#type", Static).update(Text(f"Type: {TYPE_CHOICES[self.type_index][0]}"))
        self.apply_filters()

    def action_panel(self, step: int) -> None:
        """Move focus to the next (``1``) or previous (``-1``) panel. Hidden panels are skipped."""
        if len(self.screen_stack) > 1:
            return  # a pop-up is open; the panels are behind it
        panels = [w for w in (self.query_one(f"#{name}") for name in PANEL_ORDER) if w.display and w.region.width > 0]
        if not panels:
            return
        focused = self.focused
        if focused in panels:
            target = panels[(panels.index(focused) + step) % len(panels)]
        else:  # focus is somewhere else, such as the search box: enter the cycle at its start or end
            target = panels[0] if step > 0 else panels[-1]
        target.focus()

    def action_move(self, direction: str) -> None:
        """Vim-style movement in whatever has focus: lists move their cursor, panels scroll."""
        widget = self.focused
        if widget is None or isinstance(widget, Input):
            return
        cursor = getattr(widget, f"action_cursor_{direction}", None)  # DataTable and OptionList rows
        if cursor is not None and direction in ("up", "down"):
            cursor()
        else:
            getattr(widget, f"action_scroll_{direction}", lambda: None)()

    def _mark_focus(self) -> None:
        """Put a ``▸`` in the title of the panel that has focus."""
        for selector, title in PANEL_TITLES.items():
            widget = self.query_one(selector)
            widget.border_title = f"▸ {title}" if widget is self.focused else title

    def on_descendant_focus(self, event) -> None:
        self.call_after_refresh(self._mark_focus)

    def on_descendant_blur(self, event) -> None:
        self.call_after_refresh(self._mark_focus)

    def action_toggle_panel(self) -> None:
        self.query_one("#main").toggle_class("show-preview")

    def action_open_external(self) -> None:
        """Open the file under the cursor in the program the operating system uses for it."""
        record = self._cursor_record
        if record is None:
            self._set_status("No file to open")
            return
        try:
            open_in_default_program(record.path)
        except OpenError as exc:
            self._set_status(str(exc))
        else:
            self._set_status(f"Sent {record.name} to the default program")

    def action_refresh(self) -> None:
        self._set_status("Scanning…")
        self.rescan()

    def action_pick_columns(self) -> None:
        if self.df is None:
            return
        shown = build_preview(self.df, 10, self._columns_that_fit(), self.selected_columns).head.columns
        names = [str(c) for c in self.df.columns]

        def after(chosen: list[str] | None) -> None:
            if chosen is None or self.df is None:
                return
            if not set(chosen) <= {str(c) for c in self.df.columns}:
                return  # the table changed while the picker was open
            self.selected_columns = chosen or None
            self._render_views()

        self.push_screen(ColumnPicker(names, set(shown)), after)

    # ----------------------------------------------------------- open a file
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value
        record = next((r for r in self.shown_files if str(r.path) == key), None)
        if record is not None:
            self.open_file(record)

    def open_file(self, record: FileRecord) -> None:
        """Start opening a file; ask first when it is over 50 MB."""
        if is_large(record.size):

            def after(confirmed: bool | None) -> None:
                if confirmed:
                    self._start_open(record)

            self.push_screen(ConfirmLargeFile(record.size), after)
        else:
            self._start_open(record)

    def _start_open(self, record: FileRecord) -> None:
        self._token += 1
        previous, self.current = self.current, record
        self._restyle_rows(previous, record)
        self.df = None
        self.profile_result = None
        self.selected_columns = None
        self.sheets = []
        self.sub_title = f"{record.path}  ·  Lvl {record.level}"
        self.query_one("#sheets", OptionList).display = False
        self._show_preview(Text("Loading…", style="dim"))
        self.query_one("#profile", Static).update("")
        self._jump_to_preview_when_narrow()
        self._load_sheets(self._token, record)

    def _jump_to_preview_when_narrow(self) -> None:
        """On a narrow terminal only one panel fits, so show the Preview once a file is picked."""
        main = self.query_one("#main")
        if main.has_class("narrow"):
            main.add_class("show-preview")
            self.call_after_refresh(self.query_one("#preview-box").focus)  # it is hidden until the layout refreshes

    @work(thread=True, exclusive=True, group="load")
    def _load_sheets(self, token: int, record: FileRecord) -> None:
        try:
            sheets = list_sheets(record.path)
        except LoaderError as exc:
            self.call_from_thread(self._show_error, token, str(exc))
            return
        except Exception as exc:  # one bad file must never stop the app
            self.call_from_thread(self._show_error, token, f"Unexpected error: {type(exc).__name__}: {exc}")
            return
        self.call_from_thread(self._show_sheets, token, record, sheets)

    def _show_sheets(self, token: int, record: FileRecord, sheets: list[SheetInfo]) -> None:
        if token != self._token:
            return
        self.sheets = sheets
        option_list = self.query_one("#sheets", OptionList)
        if not sheets:  # CSV: no sheet step
            self._load_target(record, None, None)
            return
        options = []
        for sheet in sheets:
            size = f" ({sheet.rows:,} × {sheet.cols:,})" if sheet.rows is not None else ""
            options.append(Option(Text(f"{sheet.name}{size}"), id=f"s{SEP}{sheet.name}"))
            for table in sheet.tables:
                options.append(Option(Text(f"   ▸ Table: {table}"), id=f"t{SEP}{sheet.name}{SEP}{table}"))
        option_list.clear_options()
        option_list.add_options(options)
        option_list.display = True
        self._load_target(record, sheets[0].name, None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if self.current is None or event.option.id is None:
            return
        parts = event.option.id.split(SEP)
        if parts[0] == "s":
            self._token += 1
            self._load_target(self.current, parts[1], None)
        elif parts[0] == "t":
            self._token += 1
            self._load_target(self.current, parts[1], parts[2])

    def _load_target(self, record: FileRecord, sheet: str | None, table: str | None) -> None:
        self.df = None  # the old table is no longer current
        self.profile_result = None
        self.selected_columns = None
        self._show_preview(Text("Loading…", style="dim"))
        self._load_table(self._token, record, sheet, table)

    @work(thread=True, exclusive=True, group="table")
    def _load_table(self, token: int, record: FileRecord, sheet: str | None, table: str | None) -> None:
        try:
            df = load_table(record.path, sheet, table)
            result = profile(df)
        except LoaderError as exc:
            self.call_from_thread(self._show_error, token, str(exc))
            return
        except Exception as exc:  # one bad file must never stop the app
            self.call_from_thread(self._show_error, token, f"Unexpected error: {type(exc).__name__}: {exc}")
            return
        self.call_from_thread(self._show_table, token, record, sheet, table, df, result)

    # --------------------------------------------------------------- results
    def _show_error(self, token: int, message: str) -> None:
        if token != self._token:
            return
        self.df = None
        self.profile_result = None
        self._show_preview(Text(message, style="bold red"))
        self.query_one("#profile", Static).update("")
        self._set_status(message)

    def _show_table(self, token, record, sheet, table, df, result) -> None:
        if token != self._token or record != self.current:
            return  # an older selection finished late; ignore it
        self.df = df
        self.profile_result = result
        self.selected_columns = None
        self._render_views()
        where = f" › {sheet}" if sheet else ""
        where += f" › {table}" if table else ""
        notes = "".join(f" · ⚠ {note}" for note in df.attrs.get("notes", []))
        self._set_status(f"{record.name}{where} · {len(df):,} rows{notes}")

    def _columns_that_fit(self) -> int:
        return columns_that_fit(self.query_one("#preview-box").size.width or 80)

    def _show_preview(self, renderable, scroll: bool = False) -> None:
        """Show something in the Preview. A table (``scroll=True``) gets its natural width, so a wide one
        scrolls sideways instead of being squeezed. Short messages keep the default width and wrap."""
        widget = self.query_one("#preview", Static)
        if scroll:
            console = self.app.console
            natural = Measurement.get(console, console.options.update(max_width=10_000), renderable).maximum
            widget.styles.width = max(natural, 1)
        else:
            widget.styles.width = "auto"
        widget.update(renderable)

    def _render_views(self) -> None:
        if self.df is None or self.profile_result is None:
            return
        try:
            preview = build_preview(self.df, 10, self._columns_that_fit(), self.selected_columns)
            shown = render_preview(preview)
            notes = [Text(f"⚠ {note}", style="yellow") for note in self.df.attrs.get("notes", [])]
            self._show_preview(Group(*notes, shown) if notes else shown, scroll=True)
            self.query_one("#profile", Static).update(render_profile(self.profile_result))
        except Exception as exc:  # show the problem instead of closing the app
            message = f"Cannot display this table: {type(exc).__name__}: {exc}"
            self._show_preview(Text(message, style="bold red"))
            self._set_status(message)

    def on_resize(self) -> None:
        self.query_one("#main").set_class(self.size.width < 110, "narrow")
        self._render_views()
