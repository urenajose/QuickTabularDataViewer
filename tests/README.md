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
| `test_profiler.py` | The preview slice and the profile numbers. |
| `test_render.py` | The Rich tables, including data that contains square brackets. |
| `test_cli.py` | The command line. |
| `test_app.py` | The screen, run without a real terminal (headless). |
| `test_package.py` | The package imports. |

## Notes

- The screen tests use `asyncio.run(...)` so no extra test library is needed.
- Test files are built in temporary folders. No real client data is used.
- `conftest.py` builds the sample `.xlsx` and `.ods` files.

## Optional: the `.xls` test

The `.xls` test is skipped until a small sample file exists at:

`tests\data\sample.xls`

Use a tiny file with a few rows and **no real client data**. Creating `.xls`
files from code needs a library that has not been approved, so this one file is
supplied by hand.
