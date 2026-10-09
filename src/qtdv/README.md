# qtdv package - what each file does

**Created:** 2026-10-07 01:50 PM -04:00

The code is split into small pieces. Each piece does one job, so you can
understand it without reading the others.

| File | Job | Uses |
|------|-----|------|
| `cli.py` | Reads the command line (`qtdv [folder] [-r DEPTH]`) and starts the app. | the app |
| `scanner.py` | Finds table files in a folder down to the chosen depth, and filters them by name, type and modified date. It never opens a file. | nothing else |
| `loader.py` | **The only file that reads data files.** Lists sheets and named Tables, loads a table into a pandas DataFrame, and knows the 50 MB limit. | pandas, openpyxl, odfpy, xlrd |
| `opener.py` | Opens a file in the operating system's default program (Windows, macOS, Linux). Used by the `o` key. | the standard library only |
| `profiler.py` | Turns a DataFrame into plain results: the preview slice (first/last rows and columns) and the profile (rows, columns, nulls, unique counts). | pandas |
| `ui/` | Everything you see on screen. See [ui/README.md](ui/README.md). | the files above |

## How the pieces connect

```
cli  ->  ui (app)
          |-- scanner   (which files exist)
          |-- loader    (read one file)
          |-- profiler  (summarize the table)
          `-- render    (draw the summary with Rich)
```

The UI asks `scanner`, `loader` and `profiler` for results and only displays
them. This is why Phase 2 (editing) can be added in `loader.py` without
rewriting the screen.

## Rules the code follows

- Reading is the only thing it does in Phase 1. Your files are never changed.
- Problems become a short message on screen (`LoaderError`), never a crash.
- Column names are cleaned so they are always unique, non-blank text.
