# Changelog

All notable changes to qtdv are listed here.
Format: https://keepachangelog.com/en/1.0.0/

## [Unreleased]

### Removed

- The `describe()` table and `Profile.describe`. The Profile panel keeps the row
  and column counts and the per-column type, null count and unique count.

### Changed

- `o` now opens the active file (the one marked `●`) instead of the file under the
  cursor. With no file open it still opens the file under the cursor. The Preview's top
  line shows the hint `o: open in default program` next to the row and column count.
- `Esc` now steps back one layer at a time: it leaves the narrow-screen Preview, then
  returns to the file list, then closes the open file (Preview, Profile, Sheets and
  the `●` mark are cleared). A pop-up still closes on `Esc`.
- The Preview keeps its natural width and scrolls sideways when the table is wider
  than the panel (for example when many columns are chosen in the picker).
- Long column names in the Profile are cut at 12 characters with `…`.
- The Preview rows alternate in shade, like the Files rows.
- The Files rows alternate in shade, so a row is easier to follow across the screen.
- Files columns are now Lvl, Name, Modified, Size and Folder, so Folder is last.
- Long file names in the Files panel wrap at 24 characters, so the Folder,
  Modified and Size columns fit on screen. The row grows taller and the tint
  covers every line.
- New layout: Files on the left with Profile above Sheets / Tables to its right,
  and the Preview across the full width at the bottom. Every panel scrolls
  when its content does not fit. On a narrow terminal the `p` key now
  switches between the Preview and the other panels.
- The Files and Sheets / Tables panels now have a border and a title, like
  Preview and Profile. The Preview and Profile titles no longer show the file name.
- The project is renamed from `qxc` (Quick Excel/CSV) to `qtdv` (Quick Tabular
  Data Viewer). The command is now `qtdv`, the Python package is `qtdv`, and the
  old `qxc` command is removed.

### Fixed

- A CSV with a row that has more fields than the header (for example an unquoted
  comma inside a note) failed with "Cannot parse CSV". It now opens, the extra
  values are cut, and a yellow warning with the first line number shows above the
  Preview and in the status line.
- The opened-file tint now fills the whole row. Before, only the text was tinted,
  so it looked like patches of green over the cursor colour.
- While the cursor is on the opened file, the cursor colour is shown on its own
  (the `●` stays). The tint comes back when the cursor moves away.
- The app class was still called `QxcApp`; it is now `QtdvApp`.

### Added

- `o` opens the file under the cursor in the default program of the operating system
  (Windows, macOS and Linux), so Excel and Calc files can be edited where they belong.
  The new `opener.py` module does this with the standard library only.
- `.tsv` (tab-separated) files are listed and opened like CSV files, with their own
  `tsv` choice in the Type filter (`t`). Rows with extra fields are cut and reported
  the same way as in CSV files.
- On a narrow terminal, picking a file now jumps straight to the Preview
  (use `p` or `Esc` to go back to the file list).
- Vim keys `h` `j` `k` `l` move the cursor or scroll inside the panel that has focus.
- `g` and `Shift+G` jump between the panels. The panel with focus has a brighter
  border and a `▸` in its title.
- The `.xls` test now runs against `tests/data/file_example_XLS_50.xls`.
- The opened file is marked with a `●` in the first column and a light green
  row tint, so it is clear which file is open and which row the cursor is on.
- The Preview and Profile panel titles show the opened file's name.

## [0.1.0] - 2026-10-07

### Added

- `qxc [folder] [-r DEPTH]` command with a three-column terminal layout.
- File index with level, folder, modified date and size.
- Search by name, filter by file type, and filter by modified-date range.
- Support for CSV, XLSX/XLSM, XLS and ODS files, with a sheet list and named
  Excel Tables (XLSX only).
- Preview of the first and last 10 rows and the first and last 5 columns, with
  an optional column picker.
- Profile with rows, columns, null counts, unique counts and `describe()`.
- Warning before loading files over 50 MB.
- A `p` key to switch between Preview and Profile on narrow terminals.

### Changed

- `requires-python` lowered from `>=3.15` to `>=3.12`.
