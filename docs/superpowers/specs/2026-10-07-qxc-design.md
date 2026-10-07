# qxc (Quick Excel/CSV) - Design Spec

**Author:** Jose Urena
**Created:** 2026-10-07 01:20 PM -04:00
**Status:** Draft - waiting for Jose's review
**Scope:** Phase 1 (view-only). Phases 2 and 3 are listed at the end.

---

## 1. Purpose

`qxc` is a terminal app, similar to Glow, but for table data. Jose runs it in a
folder, sees an index of spreadsheet-like files, picks one, and instantly sees a
preview and a statistical profile of the data. It is for quickly inspecting
exports (case management exports, Excel reports) without opening Excel or LibreOffice.

**Success looks like:** run `qxc`, find a file by name/type/date, and understand
its shape and data quality in a few seconds, using only the keyboard.

## 2. Stack and Rules

- **Python** with `uv` for environment and dependencies.
- **pandas** - all reading and (later) editing of data.
- **Rich** - table rendering.
- **Textual** - the app, layout, and key handling.
- **Reader engines (approved):** `openpyxl` (.xlsx/.xlsm), `odfpy` (.ods),
  `xlrd` (.xls).
- **Test tool (approved):** `pytest`.
- **Not used in Phase 1:** DuckDB. It may be added later for large CSVs, behind
  the `loader` module. It needs Jose's approval first.
- Any new library needs Jose's approval before it is added.

## 3. Supported Files

| Extension | Reader | Sheets | Named Tables |
|-----------|--------|--------|--------------|
| `.csv` | pandas | no (single table) | no |
| `.xlsx`, `.xlsm` | openpyxl | yes | yes (Excel Tables) |
| `.xls` | xlrd | yes | no |
| `.ods` | odfpy | yes | no |

## 4. Command Line

```
qxc [folder] [-r DEPTH]
```

- `folder` defaults to `.` (the current folder).
- `-r DEPTH` is the number of **subfolder levels** to scan below the folder.
  - Default is `0`: only files directly in the folder.
  - `-r 1` adds one subfolder level, `-r 3` adds three levels.
- A bare `qxc` is the same as `qxc . -r 0`.
- A level number is shown for each file: `0` means the root folder, `1` means a
  first-level subfolder, and so on.

## 5. Screen Layout (three columns)

```
+ Search / Type / From / To -----------------------------------+
+- Files (Lvl) ------+- Sheets/Tables -+- Preview -------------+
| 0 a.csv            | Sheet1          | head 10 / tail 10     |
| 1 Rpts/b.xlsx      | Sheet2  <       | first 5 / last 5 cols |
| 0 c.ods            | Table: Sales    +- Profile -------------+
|                    |                 | rows, cols, nulls,    |
|                    |                 | unique, describe()    |
+--------------------+-----------------+-----------------------+
```

- The **Sheets/Tables** column only appears for Excel and ODS files.
- **Named Tables** appear under their sheet, for `.xlsx` files only.
- Each sheet shows its size, for example `Sheet1 (1,200 x 8)`.
- On a narrow terminal the layout collapses into tabs.

## 6. Features (Phase 1)

1. **File index** with a `Lvl` column and the relative subfolder path.
2. **Search by name** - text box, case-insensitive "contains" match.
3. **Filter by type** - csv / xlsx / xls / ods, or all.
4. **Filter by date** - compares the **modified date**. Two boxes, `From` and
   `To`, in `YYYY-MM-DD`. Either can be blank (open-ended).
5. **Sheet and Table list** for Excel/ODS files (see section 3).
6. **Preview** - the first 10 and last 10 rows, with a divider row between
   them. Columns are the first 5 and last 5, with a `...` column in the middle.
   The column count adapts to the terminal width (maximum 5 + 5).
7. **Profile** - computed on the full table: number of rows, number of columns,
   per-column cardinality (unique count), per-column null count, and the pandas
   `describe()` output.
8. **Column picker (optional, last item)** - a key opens a checkbox list of
   column names, and the preview shows only the checked columns.
9. **Refresh key (`F5`)** - rescans the disk.
10. **Header shows** the full path and the level of the selected file.

Random-row preview was considered and dropped.

## 7. Modules

```
src/qxc/
  cli.py         parses the command line, starts the app
  scanner.py     finds files by depth, then filters (name, type, dates)
  loader.py      all pandas file reading: sheets, Tables, full load, 50 MB check
  profiler.py    DataFrame -> head/tail preview + stats + describe()
  ui/
    app.py       Textual app and layout
    widgets.py   file list, sheet list, preview, profile
    qxc.tcss     styling
```

- `scanner.py` has no pandas or UI code. It returns file records: name, level,
  relative path, size, modified date, type.
- `loader.py` is the only module that reads files with pandas. Editing (Phase 2)
  and a possible DuckDB path plug in here.
- `profiler.py` has no UI code. It takes a DataFrame and returns plain results.
- The UI only displays results and handles keys.
- Each folder gets a short `README.md` for humans.

## 8. Data Flow

1. Start: `scanner` reads the disk once and keeps the file list in memory.
2. Search/type/date filters work on the in-memory list, so they are instant.
   `F5` rescans the disk to pick up new or changed files.
3. Selecting a file: a background worker asks `loader` for the sheet list (and
   Tables for `.xlsx`). CSV files skip this step.
4. Selecting a sheet or Table: `loader` reads the whole table into a DataFrame.
   Files over **50 MB** first ask "Large file (X MB). Load anyway? y/n".
5. `profiler` runs once on the DataFrame. The UI draws the preview and the
   profile with Rich tables.
6. All loading runs in a Textual background worker, so the screen never freezes.
   A "loading..." message shows until it finishes.

The whole file is read because the last 10 rows and the full-table statistics
need it.

## 9. Error Handling

Problems appear as a message in the panel and never crash the app.

- File locked or open elsewhere (common with OneDrive and Excel): "File in use,
  try again".
- Corrupt or unsupported file: a short reason.
- Password-protected workbook: reported as unreadable.
- Invalid date (for example `2025-13-40`): the box turns red and that filter is
  ignored.
- Empty folder or no matches: "No files match".
- Sheet with no rows: shown as empty.

## 10. Testing

- `pytest` unit tests for:
  - `scanner`: depth numbering (`-r 0`, `-r 1`), search, type and date filters.
  - `loader`: small sample CSV, XLSX (with a Table), XLS, and ODS files.
  - `profiler`: numbers checked against known data.
- A few Textual headless tests for the main flow.
- The rest is checked by running the app by hand.

## 11. Open Items

1. `pyproject.toml` has `requires-python = ">=3.15"`, but the installed Python is
   3.14.7. Proposed change: `>=3.12`. Needs Jose's approval.
2. Final key bindings are chosen during planning.
3. Reader libraries and `pytest` are approved but not installed yet.

## 12. Later Phases (not in scope now)

- **Phase 2 - cell editing:** change a cell value and save to the file or as a
  copy. Risk: pandas can lose formatting and formulas when saving Excel files.
- **Phase 3 - structure editing:** add/delete rows and columns, rename columns.
- **Optional:** DuckDB for large CSVs, a filter by level, a recent-folders list.
