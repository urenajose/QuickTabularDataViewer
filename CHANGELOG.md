# Changelog

All notable changes to qxc are listed here.
Format: https://keepachangelog.com/en/1.0.0/

## [Unreleased]

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
