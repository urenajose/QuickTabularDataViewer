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

- `us_states_and_abbreviations.csv` - a public list of US states. Line 15 is
  damaged on purpose (an unquoted comma inside a note makes it three fields), so
  it tests that a malformed row is cut and reported instead of failing.
