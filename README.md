# qxc - Quick Excel/CSV viewer

**Created:** 2026-10-07 01:50 PM -04:00
**Status:** Version 0.1.0 (Phase 1: view only)

`qxc` is a terminal app, similar to Glow, but for table data. Run it in a
folder, pick a spreadsheet-like file from the list, and see a preview of the
data and a statistical profile of it. It never changes your files.

## Supported files

| Type | Extensions | Sheets | Named Excel Tables |
|------|-----------|--------|--------------------|
| CSV | `.csv` | no | no |
| Excel | `.xlsx`, `.xlsm` | yes | yes |
| Old Excel | `.xls` | yes | no |
| LibreOffice Calc | `.ods` | yes (names only) | no |

## Install and run

From this folder:

```powershell
uv sync                  # install the libraries
uv run qxc               # scan the current folder
uv run qxc C:\some\folder          # scan a different folder
uv run qxc . -r 2        # also scan 2 levels of subfolders
```

### How `-r` works

`-r` is the number of **subfolder levels** to scan below the folder. The
default is `0`, which means only the files directly in the folder.

| Command | Scans |
|---------|-------|
| `qxc` or `qxc . -r 0` | the folder only |
| `qxc . -r 1` | the folder and its subfolders |
| `qxc . -r 3` | the folder and 3 levels of subfolders |

The file that is open shows a `●` in the first column and a light green row.
The cursor row keeps its normal highlight, so you can tell the two apart.

The `Lvl` column in the file list shows where each file lives: `0` is the
folder you started in, `1` is a subfolder, `2` is a subfolder inside that, and
so on. The selected file's full path and level also show in the header.

## The screen

```
+ Search / Type / From / To -----------------------------------+
+- Files (Lvl) ------+- Sheets/Tables -+- Preview -------------+
| 0 a.csv            | Sales (4 x 2)   | first 10 / last 10    |
| 1 b.xlsx           |   > Table: ...  | first 5 / last 5 cols |
| 0 c.ods            | Notes           +- Profile -------------+
|                    |                 | rows, columns, nulls, |
|                    |                 | unique, describe()    |
+--------------------+-----------------+-----------------------+
```

- **Files** - every table file found, with level, folder, modified date and size.
- **Sheets/Tables** - only shown for Excel and LibreOffice files. Named Excel
  Tables show under their sheet (`.xlsx` only). Sheet sizes show the used range.
- **Preview** - the first 10 and last 10 rows, with a `⋮` row between them. When
  a table has many columns, the first 5 and last 5 show, with a `…` column
  between them. Fewer columns show on a narrow terminal.
- **Profile** - number of rows and columns; for each column its type, null count
  and unique count; and the pandas `describe()` statistics.

## Keys

| Key | What it does |
|-----|--------------|
| `Enter` | Open the highlighted file (or sheet/Table in the sheet list) |
| `/` | Go to the search box (name contains the text, any case) |
| `t` | Cycle the file type filter: all, csv, xlsx, xls, ods |
| `d` | Go to the date boxes (`From` and `To`, as `YYYY-MM-DD`) |
| `c` | Choose which columns to show in the preview (Space = toggle, Enter = apply) |
| `p` | On a narrow terminal, switch between Preview and Profile |
| `F5` | Scan the disk again to pick up new or changed files |
| `Esc` | Go back to the file list |
| `q` | Quit |

The date filter uses each file's **modified date**. Either box can be left
empty, and both dates are included. A bad date turns the box red and is ignored.

Searching and filtering use the list that is already loaded, so they are
instant. Press `F5` to see files that were added or changed after `qxc` started.

## Large files

Files over **50 MB** ask first: `Large file (X MB). Load anyway?` Press `y` to
load or `n` to cancel. The whole file is read so the last rows and the full
statistics are correct.

## Messages you may see

| Message | What it means |
|---------|---------------|
| File in use, try again | The file is open or locked (common with Excel and OneDrive) |
| Workbook is password-protected and cannot be read | Remove the password first |
| Cannot read ... | The file is damaged or not really that type |
| No files match | The filters hide every file, or the folder has none |

## Good to know

- ID-style CSV columns with leading zeros (ZIP codes, case numbers such as
  `00123`) stay as text so the zeros are kept.
- Columns with a blank or repeated header get a name such as `Unnamed: 2` or
  `name.1`.
- Excel formulas show their last saved value.

## Project layout

See [src/qxc/README.md](src/qxc/README.md) for what each module does,
[tests/README.md](tests/README.md) for how to run the tests, and
[docs/README.md](docs/README.md) for the design and plan.

## Roadmap

1. **Phase 1 (this version):** view only.
2. **Phase 2:** edit cell values and save to the file or as a copy. Note that
   saving an Excel file with pandas can lose formatting and formulas.
3. **Phase 3:** add and delete rows and columns, and rename columns.
4. **Maybe later:** DuckDB for very large CSV files (needs approval first), and a
   filter by level.
