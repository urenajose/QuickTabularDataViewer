# Tests

**Created:** 2026-10-07 01:50 PM -04:00

Run all tests from the project folder:

```powershell
uv run pytest -v
```

| File | What it checks |
|------|----------------|
| `test_scanner.py` | Depth numbering (`-r 0`, `-r 1`, ...), name, type and date filters, ignored files. |
| `test_loader_csv.py` | CSV reading: encodings, leading zeros, odd headers, empty files. |
| `test_loader_excel.py` | `.xlsx`, `.ods` and `.xls` reading, sheets, named Tables, locked and damaged files. |
| `test_opener.py` | Opening a file in the default program on each system (the launchers are faked, nothing really opens). |
| `test_profiler.py` | The preview slice and the profile numbers. |
| `test_render.py` | The Rich tables, including data that contains square brackets. |
| `test_cli.py` | The command line, including `-ra` for all levels. |
| `test_app.py` | The screen, run without a real terminal (headless). |
| `test_package.py` | The package imports. |

## Notes

- The screen tests use `asyncio.run(...)` so no extra test library is needed.
- Test files are built in temporary folders. No real client data is used.
- `conftest.py` builds the sample `.xlsx` and `.ods` files.

## The `.xls` test

The `.xls` test reads `tests/data/file_example_XLS_50.xls`, a public sample
file with made-up names and data (no real client data). If the file is missing,
the test is skipped. Creating `.xls` files from code needs a library that has
not been approved, so this file is supplied by hand.

## Other sample files in `tests\data`

- `us_states_and_abbreviations.csv` - a public list of US states with a `Notes` column. It is an
  example of bad rows: every data row ends with a stray comma (the header does not), so every row has
  one field too many. That makes 43 warnings, which shows the "first 10 listed, then `10+`" message.
  Florida also has an unquoted comma inside its note (two extra fields). Texas has a comma inside
  quotes (`"""Austin, South-Central"""`, where `""` stands for one quote mark), which stays part of
  the value.
- `5677d895bf4e48a9a34bf4e4d9ef1291.xlsx` - public HUD data (veteran homelessness counts by state;
  the first sheet names its source on huduser.gov). It has 23 sheets, so it is a good file for trying
  the Sheets / Tables panel, a pivot sheet and wide tables.
- `file_example_XLS_50.tsv` and `file_example_XLS_50.txt` - the public `file_example_XLS_50` sample as
  tab-separated text. Only the `.tsv` is listed by qtdv; the `.txt` copy is not a supported type.
- `file_example_XLS_50_password.xlsx` - the same sample saved with a password, to try the
  "Workbook is password-protected and cannot be read" message.
