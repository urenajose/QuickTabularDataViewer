# Changelog

All notable changes to qtdv are listed here.
Format: https://keepachangelog.com/en/1.0.0/

## [Unreleased]

### Removed

- The `describe()` table and `Profile.describe`. The Profile panel keeps the row
  and column counts and the per-column type, null count and unique count.

### Changed

- Long file names in the Files panel wrap at 24 characters, so the Folder,
  Modified and Size columns fit on screen. The row grows taller and the tint
  covers every line.
- New layout: Files on top left, Sheets / Tables and Profile below it, and the
  Preview in its own column on the right. On a narrow terminal the `p` key now
  switches between the Preview and the left-hand panels.
- The Files and Sheets / Tables panels now have a border and a title, like
  Preview and Profile. The Preview and Profile titles no longer show the file name.
- The project is renamed from `qxc` (Quick Excel/CSV) to `qtdv` (Quick Tabular
  Data Viewer). The command is now `qtdv`, the Python package is `qtdv`, and the
  old `qxc` command is removed.

### Fixed

- The opened-file tint now fills the whole row. Before, only the text was tinted,
  so it looked like patches of green over the cursor colour.
- While the cursor is on the opened file, the cursor colour is shown on its own
  (the `●` stays). The tint comes back when the cursor moves away.
- The app class was still called `QxcApp`; it is now `QtdvApp`.

### Added

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
