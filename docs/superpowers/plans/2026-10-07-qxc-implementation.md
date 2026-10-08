# qxc Implementation Plan

> **Note (2026-10-08):** This project was called `qxc` (Quick Excel/CSV) when this document was written. It is now `qtdv` (Quick Tabular Data Viewer). The text below is kept as written, as a record of what was built.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Created:** 2026-10-07 01:35 PM -04:00
**Goal:** Build `qxc`, a terminal app that lists CSV/Excel/ODS files in a folder, and shows a preview and a statistical profile of the selected table.

**Architecture:** Layered modules. `scanner` finds files, `loader` is the only module that reads files with pandas, `profiler` turns a DataFrame into plain results, and the Textual UI only displays results. Loading runs in background workers so the screen never freezes.

**Tech Stack:** Python (uv), pandas, Rich, Textual, openpyxl, odfpy, xlrd, pytest.

**Spec:** `docs/superpowers/specs/2026-10-07-qxc-design.md` (approved by Jose on 2026-10-07).

## Global Constraints

- Python floor: `requires-python = ">=3.12"` (installed: 3.14.7).
- Command name: `qxc`. `qxc` with no arguments means `qxc . -r 0`.
- `-r N` = number of **subfolder levels** below the folder. Default `0` (folder only). `Lvl` column: `0` = root folder.
- Supported extensions: `.csv`, `.xlsx`, `.xlsm`, `.xls`, `.ods`.
- Named Tables: `.xlsx`/`.xlsm` only.
- Preview: first 10 + last 10 rows, first 5 + last 5 columns (fewer columns when the terminal is narrow).
- Date filter compares **modified date**, `YYYY-MM-DD`, either box may be blank, both ends inclusive.
- Large-file warning above **50 MB** (`50 * 1024 * 1024` bytes), asking `y/n`.
- Approved libraries only: pandas, rich, textual, textual-dev, openpyxl, odfpy, xlrd, pytest. **Ask Jose before adding anything else** (including `pytest-asyncio`, `xlwt`, DuckDB).
- Phase 1 is view-only. Nothing in this plan writes to a user's data file.
- Jose's rules (from CLAUDE.md): back up a config/script file to `working_version_tested.<name>` before modifying it; Python uses specific `try/except`; every folder gets a plain-language `README.md`; doc timestamps use local time with offset (`-04:00` EDT / `-05:00` EST); check grammar and spelling in notes and docs; never put sensitive data (emails, passwords, client data) in logs or samples.
- **Git:** the repository root is `A:\WorkScripts\Python\Quick_Excel_CSV` (a new local repo on branch `main`, created 2026-10-07; no remote). Run git as `git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV <command>` (no global config change). Jose chose a local repo for this project, so commit steps are expected; if he says otherwise, skip them. End each commit message with:
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- Textual 8.x is newer than much public documentation. If a Textual call below fails, check the installed version's docs (`uv run python -c "import textual; print(textual.__version__)"`) and adjust the call, not the behavior.

## Review Focus

Input classes the spec implies but does not spell out, most likely first. Each has a test in the task shown.

1. **CSV ID columns with leading zeros** (ZIP codes, case numbers such as `00123`) must keep their zeros, not become `123`. Expected: stays text. *(Task 3)*
2. **Blank, duplicate, or numeric header names** must not crash the preview or profile. Expected: renamed to `Unnamed: N` / `name.1`, shown normally. *(Task 3, Task 5)*
3. **Cell text containing square brackets** such as `[red]x[/red]` or `[1]` must display literally. Rich would read them as markup. Expected: shown exactly as stored. *(Task 7)*
4. **Header-only or fully empty files** (zero rows, or zero columns) must not crash. Expected: "0 rows" shown, no error. *(Task 3, Task 5)*
5. **Fast switching** between files or sheets must not show an older file's result after a newer one was chosen. Expected: only the latest selection is displayed. *(Task 8)*

---

## File Structure

```
/
  pyproject.toml                  modify (backup first)
  main.py                         remove (backup first)
  README.md                       fill in (Task 11)
  CHANGELOG.md                    create (Task 11)
  .gitignore                      create
  src/qxc/__init__.py             version string
  src/qxc/README.md               module map for humans
  src/qxc/cli.py                  argument parsing, starts the app
  src/qxc/scanner.py              find files by depth, then filter
  src/qxc/loader.py               pandas reading, sheets, Tables, 50 MB check
  src/qxc/profiler.py             preview slice + profile numbers
  src/qxc/ui/__init__.py
  src/qxc/ui/README.md
  src/qxc/ui/app.py               Textual app, layout, workers, key actions
  src/qxc/ui/render.py            Rich renderables for preview/profile (testable without Textual)
  src/qxc/ui/screens.py           modal screens: large-file prompt, column picker
  src/qxc/ui/qxc.tcss             styling
  tests/README.md
  tests/conftest.py               sample file builders
  tests/test_*.py                 one test file per module
  tests/data/                     optional sample.xls supplied by Jose
```

Two small refinements to the spec's module list: the spec's `ui/widgets.py` becomes `ui/render.py` (Rich output, easy to test) plus `ui/screens.py` (the two pop-up screens). The "narrow terminal collapses into tabs" item is built as a `p` key that switches between Preview and Profile (Task 10).

---

### Task 1: Project setup and dependencies

**Files:**
- Backup: `working_version_tested.pyproject.toml`, `working_version_tested.main.py`
- Modify: `pyproject.toml`
- Remove: `main.py`
- Create: `.gitignore`, `src/qxc/__init__.py`, `tests/test_package.py`

**Interfaces:**
- Produces: importable package `qxc` with `qxc.__version__ == "0.1.0"`; console command `qxc` pointing at `qxc.cli:main` (written in Task 6); `uv run pytest` works.

- [ ] **Step 1: Back up the existing files (Jose's safe-modification rule)**

Run (PowerShell, in `A:\WorkScripts\Python\Quick_Excel_CSV`):
```powershell
Copy-Item pyproject.toml working_version_tested.pyproject.toml
Copy-Item main.py working_version_tested.main.py
```
Expected: both backup files exist.

- [ ] **Step 2: Write the new `pyproject.toml`**

Replace the whole file with:
```toml
[project]
name = "quick-excel-csv"
version = "0.1.0"
description = "qxc - browse and profile CSV, Excel and LibreOffice Calc files in the terminal"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "pandas>=3.0.6",
    "rich>=15.0.0",
    "textual>=8.2.8",
    "textual-dev>=1.8.0",
]

[project.scripts]
qxc = "qxc.cli:main"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "qxc"

[tool.pytest.ini_options]
testpaths = ["tests"]
```
(`uv_build` is uv's own build tool. It is needed so that `qxc` installs as a command. It is not a library your code imports.)

- [ ] **Step 2b: Add the approved libraries**

Run:
```powershell
uv add openpyxl odfpy xlrd
uv add --dev pytest
```
Expected: `pyproject.toml` now lists the three readers under `dependencies` and `pytest` under `[dependency-groups] dev`; `uv.lock` updated.

- [ ] **Step 3: Remove the stub `main.py` and create the package**

```powershell
Remove-Item main.py
New-Item -ItemType Directory -Force src\qxc\ui, tests\data | Out-Null
```
Create `src/qxc/__init__.py`:
```python
"""qxc - browse and profile CSV, Excel and LibreOffice Calc files in the terminal."""

__version__ = "0.1.0"
```
Create `src/qxc/ui/__init__.py` (empty file).
Create `.gitignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Write the smoke test**

`tests/test_package.py`:
```python
import qxc


def test_package_has_version():
    assert qxc.__version__ == "0.1.0"
```

- [ ] **Step 5: Run it**

Run: `uv run pytest -v`
Expected: `1 passed`. If `uv` reports a Python version problem, stop and tell Jose.

- [ ] **Step 6: Commit** (only if Jose approved commits)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add pyproject.toml uv.lock .gitignore src tests working_version_tested.pyproject.toml working_version_tested.main.py docs
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "chore: set up qxc package, dependencies and approved spec/plan"
```

---

### Task 2: Scanner (find and filter files)

**Files:**
- Create: `src/qxc/scanner.py`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Produces:
  - `SUPPORTED_EXTENSIONS: frozenset[str]`
  - `FileRecord` (frozen dataclass): `path: Path`, `name: str`, `level: int`, `rel_dir: str` (`""` for root, else posix path like `2025/q1`), `size: int` (bytes), `modified: datetime`, `ext: str` (lower case, with dot)
  - `scan(folder: Path | str, depth: int = 0) -> list[FileRecord]` - raises `ValueError` if `depth < 0`, `NotADirectoryError` if folder is missing
  - `parse_date(text: str) -> date | None` - blank gives `None`, bad text raises `ValueError`
  - `filter_files(records, name="", exts=None, date_from=None, date_to=None) -> list[FileRecord]`

- [ ] **Step 1: Write the failing tests**

`tests/test_scanner.py`:
```python
import os
from datetime import date, datetime

import pytest

from qxc.scanner import filter_files, parse_date, scan


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "a.csv").write_text("x\n1\n")
    (tmp_path / "Notes.txt").write_text("not a table")
    (tmp_path / "~$lock.xlsx").write_bytes(b"")  # Excel lock file, must be ignored
    sub = tmp_path / "2025"
    sub.mkdir()
    (sub / "b.xlsx").write_bytes(b"")
    deep = sub / "q1"
    deep.mkdir()
    (deep / "c.ods").write_bytes(b"")
    return tmp_path


def names(records):
    return sorted(r.name for r in records)


def test_depth_zero_lists_only_root_files(tree):
    records = scan(tree, depth=0)
    assert names(records) == ["a.csv"]
    assert records[0].level == 0
    assert records[0].rel_dir == ""


def test_depth_one_adds_one_subfolder_level(tree):
    records = scan(tree, depth=1)
    assert names(records) == ["a.csv", "b.xlsx"]
    b = next(r for r in records if r.name == "b.xlsx")
    assert b.level == 1
    assert b.rel_dir == "2025"


def test_depth_two_reaches_second_level(tree):
    records = scan(tree, depth=2)
    c = next(r for r in records if r.name == "c.ods")
    assert c.level == 2
    assert c.rel_dir == "2025/q1"


def test_unsupported_and_lock_files_are_ignored(tree):
    assert "Notes.txt" not in names(scan(tree, depth=2))
    assert "~$lock.xlsx" not in names(scan(tree, depth=2))


def test_negative_depth_is_rejected(tree):
    with pytest.raises(ValueError):
        scan(tree, depth=-1)


def test_missing_folder_is_rejected(tmp_path):
    with pytest.raises(NotADirectoryError):
        scan(tmp_path / "nope")


def test_name_filter_is_case_insensitive_contains(tree):
    records = scan(tree, depth=2)
    assert names(filter_files(records, name="B.X")) == ["b.xlsx"]
    assert names(filter_files(records, name="")) == names(records)


def test_type_filter(tree):
    records = scan(tree, depth=2)
    assert names(filter_files(records, exts={".csv"})) == ["a.csv"]
    assert names(filter_files(records, exts={".csv", ".ods"})) == ["a.csv", "c.ods"]


def test_date_filter_is_inclusive_and_open_ended(tree):
    old = tree / "a.csv"
    stamp = datetime(2024, 3, 10, 15, 0).timestamp()
    os.utime(old, (stamp, stamp))
    records = scan(tree, depth=0)
    assert len(filter_files(records, date_from=date(2024, 3, 10), date_to=date(2024, 3, 10))) == 1
    assert len(filter_files(records, date_to=date(2024, 3, 9))) == 0
    assert len(filter_files(records, date_from=date(2024, 3, 11))) == 0
    assert len(filter_files(records, date_from=date(2024, 1, 1))) == 1


def test_parse_date():
    assert parse_date("2025-01-31") == date(2025, 1, 31)
    assert parse_date("  2025-01-31 ") == date(2025, 1, 31)
    assert parse_date("") is None
    assert parse_date("   ") is None
    with pytest.raises(ValueError):
        parse_date("2025-13-40")
    with pytest.raises(ValueError):
        parse_date("last week")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_scanner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qxc.scanner'`.

- [ ] **Step 3: Write `src/qxc/scanner.py`**

```python
"""Find table files in a folder and filter them.

This module never reads file contents and has no UI or pandas code.
It only looks at names, sizes and dates.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SUPPORTED_EXTENSIONS = frozenset({".csv", ".xlsx", ".xlsm", ".xls", ".ods"})


@dataclass(frozen=True)
class FileRecord:
    """One file found by the scanner."""

    path: Path
    name: str
    level: int  # 0 = the root folder, 1 = first subfolder level, ...
    rel_dir: str  # "" for the root folder, otherwise e.g. "2025/q1"
    size: int  # bytes
    modified: datetime
    ext: str  # lower case, with the dot, e.g. ".csv"


def scan(folder: Path | str, depth: int = 0) -> list[FileRecord]:
    """List supported files in ``folder`` and ``depth`` subfolder levels below it.

    Folders that cannot be read (permissions) and files that disappear while
    scanning are skipped. Excel lock files (``~$name.xlsx``) are ignored.
    """
    if depth < 0:
        raise ValueError("depth must be 0 or greater")
    root = Path(folder)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    records: list[FileRecord] = []

    def walk(directory: Path, level: int) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return
        for entry in entries:
            try:
                if entry.is_dir():
                    if level < depth:
                        walk(entry, level + 1)
                    continue
                ext = entry.suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS or entry.name.startswith("~$"):
                    continue
                stat = entry.stat()
            except OSError:
                continue
            rel = "" if level == 0 else directory.relative_to(root).as_posix()
            records.append(
                FileRecord(
                    path=entry,
                    name=entry.name,
                    level=level,
                    rel_dir=rel,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    ext=ext,
                )
            )

    walk(root, 0)
    return records


def parse_date(text: str) -> date | None:
    """Turn ``YYYY-MM-DD`` into a date. Blank text gives ``None``; bad text raises ``ValueError``."""
    text = text.strip()
    if not text:
        return None
    return datetime.strptime(text, "%Y-%m-%d").date()


def filter_files(
    records: Iterable[FileRecord],
    name: str = "",
    exts: set[str] | frozenset[str] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[FileRecord]:
    """Keep records whose name contains ``name`` (any case), type is in ``exts``,
    and modified date is between ``date_from`` and ``date_to`` (both inclusive)."""
    needle = name.strip().lower()
    result = []
    for rec in records:
        if needle and needle not in rec.name.lower():
            continue
        if exts is not None and rec.ext not in exts:
            continue
        modified_day = rec.modified.date()
        if date_from is not None and modified_day < date_from:
            continue
        if date_to is not None and modified_day > date_to:
            continue
        result.append(rec)
    return result
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_scanner.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/scanner.py tests/test_scanner.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: add file scanner with depth, name, type and date filters"
```

---

### Task 3: Loader - CSV reading and column cleanup

**Files:**
- Create: `src/qxc/loader.py`
- Test: `tests/test_loader_csv.py`

**Interfaces:**
- Produces (used by Tasks 4, 8):
  - `LARGE_FILE_BYTES: int` = `50 * 1024 * 1024`
  - `is_large(size_bytes: int) -> bool` (strictly greater than the limit)
  - `LoaderError(Exception)` - message is safe to show to the user
  - `SheetInfo` (frozen dataclass): `name: str`, `rows: int | None = None`, `cols: int | None = None`, `tables: tuple[str, ...] = ()`
  - `clean_columns(df: pd.DataFrame) -> pd.DataFrame`
  - `load_table(path, sheet: str | None = None, table: str | None = None) -> pd.DataFrame` (CSV branch here; Excel/ODS branches in Task 4)
  - `list_sheets(path) -> list[SheetInfo]` (CSV returns `[]`; other types in Task 4)

- [ ] **Step 1: Write the failing tests**

`tests/test_loader_csv.py`:
```python
import pandas as pd
import pytest

from qxc.loader import LARGE_FILE_BYTES, LoaderError, is_large, list_sheets, load_table


def write(path, text, encoding="utf-8"):
    path.write_bytes(text.encode(encoding))
    return path


def test_basic_csv_infers_numbers(tmp_path):
    df = load_table(write(tmp_path / "a.csv", "id,name,score\n1,Ann,9.5\n2,Bo,7\n"))
    assert df.shape == (2, 3)
    assert pd.api.types.is_numeric_dtype(df["id"])
    assert pd.api.types.is_numeric_dtype(df["score"])
    assert df["name"].tolist() == ["Ann", "Bo"]


def test_leading_zero_ids_stay_text(tmp_path):  # Review Focus 1
    df = load_table(write(tmp_path / "z.csv", "zip,qty\n00123,1\n01234,2\n"))
    assert df["zip"].tolist() == ["00123", "01234"]
    assert pd.api.types.is_numeric_dtype(df["qty"])


def test_plain_zero_is_still_numeric(tmp_path):
    df = load_table(write(tmp_path / "z.csv", "n\n0\n5\n"))
    assert pd.api.types.is_numeric_dtype(df["n"])


def test_utf8_bom_is_stripped_from_first_header(tmp_path):
    df = load_table(write(tmp_path / "b.csv", "id,name\n1,Ann\n", encoding="utf-8-sig"))
    assert list(df.columns) == ["id", "name"]


def test_cp1252_file_is_readable(tmp_path):
    df = load_table(write(tmp_path / "c.csv", "name\nJosé\n", encoding="cp1252"))
    assert df["name"].tolist() == ["José"]


def test_odd_headers_are_cleaned(tmp_path):  # Review Focus 2
    df = load_table(write(tmp_path / "h.csv", "a,a,,3\n1,2,3,4\n"))
    assert len(set(df.columns)) == 4
    assert all(isinstance(c, str) for c in df.columns)
    assert df.shape == (1, 4)


def test_empty_file_gives_empty_frame(tmp_path):  # Review Focus 4
    df = load_table(write(tmp_path / "e.csv", ""))
    assert df.shape == (0, 0)


def test_header_only_file_has_zero_rows(tmp_path):  # Review Focus 4
    df = load_table(write(tmp_path / "h.csv", "a,b\n"))
    assert df.shape == (0, 2)


def test_csv_has_no_sheets(tmp_path):
    assert list_sheets(write(tmp_path / "a.csv", "a\n1\n")) == []


def test_unsupported_extension_raises(tmp_path):
    with pytest.raises(LoaderError):
        load_table(write(tmp_path / "a.txt", "x"))


def test_is_large_boundary():
    assert not is_large(LARGE_FILE_BYTES)
    assert is_large(LARGE_FILE_BYTES + 1)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_loader_csv.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qxc.loader'`.

- [ ] **Step 3: Write `src/qxc/loader.py` (CSV part; Excel branches raise "unsupported" until Task 4)**

```python
"""Read table files with pandas.

This is the only module that opens data files. It hides the differences
between CSV, Excel and LibreOffice Calc files from the rest of the app.
Phase 1 is read-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

LARGE_FILE_BYTES = 50 * 1024 * 1024
_LEADING_ZERO = re.compile(r"^0\d")
_OLE_MAGIC = b"\xd0\xcf\x11\xe0"  # an .xlsx that starts like this is encrypted
_XLSX_EXTS = (".xlsx", ".xlsm")


class LoaderError(Exception):
    """A problem reading a file. The message is written for the user to read."""


@dataclass(frozen=True)
class SheetInfo:
    """A sheet in a workbook. ``rows``/``cols`` are the used range, when known."""

    name: str
    rows: int | None = None
    cols: int | None = None
    tables: tuple[str, ...] = ()


def is_large(size_bytes: int) -> bool:
    """True when a file is over the 50 MB warning limit."""
    return size_bytes > LARGE_FILE_BYTES


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make every column name a unique, non-blank string."""
    used: set[str] = set()
    names: list[str] = []
    for position, col in enumerate(df.columns):
        blank = col is None or (isinstance(col, float) and pd.isna(col)) or not str(col).strip()
        base = f"Unnamed: {position}" if blank else str(col).strip()
        name, n = base, 0
        while name in used:
            n += 1
            name = f"{base}.{n}"
        used.add(name)
        names.append(name)
    df.columns = names
    return df


def _infer_types(df: pd.DataFrame) -> pd.DataFrame:
    """Turn all-text CSV columns into numbers when that is safe.

    A column stays text if any value starts with 0 followed by a digit
    (``00123``), so ZIP codes and case numbers keep their leading zeros.
    """
    for col in df.columns:
        values = df[col].dropna()
        if values.empty or values.str.match(_LEADING_ZERO).any():
            continue
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() == df[col].notna().sum():
            df[col] = converted
    return df


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return _infer_types(pd.read_csv(path, dtype=str, encoding=encoding))
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
        except pd.errors.ParserError as exc:
            raise LoaderError(f"Cannot parse CSV: {exc}") from exc
    raise LoaderError(f"Unknown text encoding: {last_error}")


def _wrap(path: Path, exc: Exception) -> LoaderError:
    """Turn a low-level exception into a message a person can act on."""
    if isinstance(exc, PermissionError):
        return LoaderError("File in use, try again")
    if "encrypted" in str(exc).lower() or (path.suffix.lower() in _XLSX_EXTS and _looks_encrypted(path)):
        return LoaderError("Workbook is password-protected and cannot be read")
    return LoaderError(f"Cannot read {path.name}: {type(exc).__name__}: {exc}")


def _looks_encrypted(path: Path) -> bool:
    try:
        with open(path, "rb") as handle:
            return handle.read(4) == _OLE_MAGIC
    except OSError:
        return False


def list_sheets(path: Path | str) -> list[SheetInfo]:
    """Sheets (and, for .xlsx, named Tables) in a file. CSV files have none."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".csv":
        return []
    try:
        if ext in _XLSX_EXTS:
            return _xlsx_sheets(path)
        if ext == ".xls":
            return _xls_sheets(path)
        if ext == ".ods":
            return _ods_sheets(path)
    except LoaderError:
        raise
    except Exception as exc:  # reader libraries raise many different types
        raise _wrap(path, exc) from exc
    raise LoaderError(f"Unsupported file type: {ext or path.name}")


def load_table(path: Path | str, sheet: str | None = None, table: str | None = None) -> pd.DataFrame:
    """Read a whole table into a DataFrame.

    ``sheet`` picks a sheet (first sheet when omitted). ``table`` picks a named
    Excel Table on that sheet (.xlsx only).
    """
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            df = _read_csv(path)
        elif table is not None and ext in _XLSX_EXTS:
            df = _read_xlsx_table(path, sheet, table)
        elif ext in _XLSX_EXTS:
            df = pd.read_excel(path, sheet_name=sheet or 0, engine="openpyxl")
        elif ext == ".xls":
            df = pd.read_excel(path, sheet_name=sheet or 0, engine="xlrd")
        elif ext == ".ods":
            df = pd.read_excel(path, sheet_name=sheet or 0, engine="odf")
        else:
            raise LoaderError(f"Unsupported file type: {ext or path.name}")
    except LoaderError:
        raise
    except Exception as exc:  # reader libraries raise many different types
        raise _wrap(path, exc) from exc
    return clean_columns(df)


# Excel / ODS readers are added in Task 4.
def _xlsx_sheets(path: Path) -> list[SheetInfo]:
    raise LoaderError("Excel support not built yet")


def _xls_sheets(path: Path) -> list[SheetInfo]:
    raise LoaderError("Excel support not built yet")


def _ods_sheets(path: Path) -> list[SheetInfo]:
    raise LoaderError("Excel support not built yet")


def _read_xlsx_table(path: Path, sheet: str | None, table: str) -> pd.DataFrame:
    raise LoaderError("Excel support not built yet")
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_loader_csv.py -v`
Expected: all PASS. If `test_odd_headers_are_cleaned` fails because pandas already renamed the columns, keep the test, it should still pass. If the `str.match` call fails on a pandas string dtype, report the exact error before changing the approach.

- [ ] **Step 5: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/loader.py tests/test_loader_csv.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: add CSV loader with encoding fallback and leading-zero protection"
```

---

### Task 4: Loader - Excel, ODS and named Tables

**Files:**
- Modify: `src/qxc/loader.py` (replace the four placeholder functions at the bottom)
- Create: `tests/conftest.py`
- Test: `tests/test_loader_excel.py`

**Interfaces:**
- Consumes: everything from Task 3.
- Produces: working `list_sheets` / `load_table` for `.xlsx`, `.xlsm`, `.xls`, `.ods`. Named Tables only for `.xlsx`/`.xlsm`. Sheet size is the **used range** (xlsx, xls only; `None` for ods).

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import pandas as pd
import pytest
from openpyxl import Workbook
from openpyxl.worksheet.table import Table


@pytest.fixture
def sample_xlsx(tmp_path):
    """Workbook with sheet 'Sales' (holding Table 'SalesTable'), 'Notes', and an empty 'Blank'."""
    wb = Workbook()
    sales = wb.active
    sales.title = "Sales"
    sales.append(["id", "amount"])
    sales.append([1, 10.5])
    sales.append([2, 20.0])
    sales.append([3, None])
    sales.add_table(Table(displayName="SalesTable", ref="A1:B4"))
    notes = wb.create_sheet("Notes")
    notes.append(["note"])
    notes.append(["hello"])
    wb.create_sheet("Blank")
    path = tmp_path / "book.xlsx"
    wb.save(path)
    return path


@pytest.fixture
def sample_ods(tmp_path):
    path = tmp_path / "book.ods"
    with pd.ExcelWriter(path, engine="odf") as writer:
        pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_excel(writer, sheet_name="First", index=False)
        pd.DataFrame({"c": [3]}).to_excel(writer, sheet_name="Second", index=False)
    return path
```

- [ ] **Step 2: Write the failing tests**

`tests/test_loader_excel.py`:
```python
from pathlib import Path

import pytest

from qxc.loader import LoaderError, list_sheets, load_table

SAMPLE_XLS = Path(__file__).parent / "data" / "sample.xls"


def test_xlsx_sheets_sizes_and_tables(sample_xlsx):
    sheets = {s.name: s for s in list_sheets(sample_xlsx)}
    assert list(sheets) == ["Sales", "Notes", "Blank"]
    assert (sheets["Sales"].rows, sheets["Sales"].cols) == (4, 2)
    assert sheets["Sales"].tables == ("SalesTable",)
    assert sheets["Notes"].tables == ()
    assert (sheets["Blank"].rows, sheets["Blank"].cols) == (0, 0)


def test_xlsx_load_sheet_and_default_sheet(sample_xlsx):
    assert load_table(sample_xlsx, sheet="Notes").shape == (1, 1)
    assert load_table(sample_xlsx).shape == (3, 2)  # first sheet


def test_xlsx_load_named_table(sample_xlsx):
    df = load_table(sample_xlsx, sheet="Sales", table="SalesTable")
    assert df.shape == (3, 2)
    assert list(df.columns) == ["id", "amount"]


def test_xlsx_missing_table_is_a_loader_error(sample_xlsx):
    with pytest.raises(LoaderError):
        load_table(sample_xlsx, sheet="Sales", table="Nope")


def test_ods_sheets_and_load(sample_ods):
    assert [s.name for s in list_sheets(sample_ods)] == ["First", "Second"]
    assert list_sheets(sample_ods)[0].tables == ()
    assert load_table(sample_ods, sheet="First").shape == (2, 2)


def test_password_protected_xlsx_message(tmp_path):
    path = tmp_path / "locked.xlsx"
    path.write_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * 64)
    with pytest.raises(LoaderError, match="password"):
        list_sheets(path)


def test_corrupt_xlsx_is_a_loader_error(tmp_path):
    path = tmp_path / "bad.xlsx"
    path.write_bytes(b"this is not a zip file")
    with pytest.raises(LoaderError):
        list_sheets(path)
    with pytest.raises(LoaderError):
        load_table(path)


@pytest.mark.skipif(not SAMPLE_XLS.exists(), reason="Jose has not supplied tests/data/sample.xls")
def test_xls_reads():
    sheets = list_sheets(SAMPLE_XLS)
    assert sheets
    assert not load_table(SAMPLE_XLS, sheet=sheets[0].name).empty
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_loader_excel.py -v`
Expected: FAIL with `LoaderError: Excel support not built yet`.

- [ ] **Step 4: Replace the placeholder functions at the bottom of `loader.py`**

Delete the four placeholder functions and the "added in Task 4" comment, and put this in their place:
```python
def _xlsx_sheets(path: Path) -> list[SheetInfo]:
    from openpyxl import load_workbook

    # Not read-only mode: named Tables are only available in normal mode.
    workbook = load_workbook(path, data_only=True)
    try:
        sheets = []
        for ws in workbook.worksheets:
            is_blank = ws.max_row == 1 and ws.max_column == 1 and ws["A1"].value is None
            rows, cols = (0, 0) if is_blank else (ws.max_row, ws.max_column)
            sheets.append(SheetInfo(ws.title, rows, cols, tuple(ws.tables.keys())))
        return sheets
    finally:
        workbook.close()


def _xls_sheets(path: Path) -> list[SheetInfo]:
    import xlrd

    book = xlrd.open_workbook(path, on_demand=True)
    try:
        return [SheetInfo(s.name, s.nrows, s.ncols) for s in (book.sheet_by_index(i) for i in range(book.nsheets))]
    finally:
        book.release_resources()


def _ods_sheets(path: Path) -> list[SheetInfo]:
    # Sizes are not available without reading each sheet, so only names are listed.
    with pd.ExcelFile(path, engine="odf") as workbook:
        return [SheetInfo(name) for name in workbook.sheet_names]


def _read_xlsx_table(path: Path, sheet: str | None, table: str) -> pd.DataFrame:
    from openpyxl import load_workbook

    workbook = load_workbook(path, data_only=True)
    try:
        ws = workbook[sheet] if sheet else workbook.worksheets[0]
        if table not in ws.tables:
            raise LoaderError(f"Table '{table}' not found on sheet '{ws.title}'")
        rows = [[cell.value for cell in row] for row in ws[ws.tables[table].ref]]
    finally:
        workbook.close()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0]).infer_objects()
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_loader_excel.py tests/test_loader_csv.py -v`
Expected: all PASS; the `.xls` test shows as SKIPPED until Jose adds a tiny `tests/data/sample.xls` (no real client data). Say so in the task report.

- [ ] **Step 6: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/loader.py tests/conftest.py tests/test_loader_excel.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: read xlsx, xls and ods files, sheets and named Tables"
```

---

### Task 5: Profiler (preview slice and statistics)

**Files:**
- Create: `src/qxc/profiler.py`
- Test: `tests/test_profiler.py`

**Interfaces:**
- Consumes: any `pd.DataFrame` with unique string column names (guaranteed by `clean_columns`).
- Produces:
  - `Preview` (frozen dataclass): `head: pd.DataFrame`, `tail: pd.DataFrame` (empty when all rows fit in `head`), `gap_after: int | None` (the `...` column goes after this many columns; `None` = no gap), `hidden_cols: int`, `total_rows: int`, `total_cols: int`
  - `build_preview(df, n_rows=10, n_cols=5, columns=None) -> Preview` - `columns` (a list of names) overrides the first/last split
  - `Profile` (frozen dataclass): `rows: int`, `cols: int`, `columns: pd.DataFrame` (index = column name; columns `dtype`, `nulls`, `unique`), `describe: pd.DataFrame` (the `describe(include="all")` result, stats as rows)
  - `profile(df) -> Profile`

- [ ] **Step 1: Write the failing tests**

`tests/test_profiler.py`:
```python
import numpy as np
import pandas as pd

from qxc.profiler import build_preview, profile


def frame(rows, cols):
    return pd.DataFrame({f"c{i}": range(rows) for i in range(cols)})


def test_small_table_shows_everything_once():
    p = build_preview(frame(15, 4))
    assert len(p.head) == 15 and p.tail.empty
    assert p.gap_after is None and p.hidden_cols == 0


def test_exactly_twenty_rows_has_no_duplicates():
    p = build_preview(frame(20, 2))
    assert len(p.head) == 20 and p.tail.empty


def test_large_table_gets_head_and_tail():
    p = build_preview(frame(100, 2))
    assert p.head["c0"].tolist() == list(range(10))
    assert p.tail["c0"].tolist() == list(range(90, 100))
    assert p.total_rows == 100


def test_wide_table_keeps_first_and_last_columns():
    p = build_preview(frame(3, 20))
    assert list(p.head.columns) == ["c0", "c1", "c2", "c3", "c4", "c15", "c16", "c17", "c18", "c19"]
    assert p.gap_after == 5 and p.hidden_cols == 10 and p.total_cols == 20


def test_column_count_adapts():
    p = build_preview(frame(3, 20), n_cols=2)
    assert list(p.head.columns) == ["c0", "c1", "c18", "c19"]
    assert p.gap_after == 2


def test_chosen_columns_override_the_split():
    p = build_preview(frame(3, 20), columns=["c7", "c3"])
    assert list(p.head.columns) == ["c7", "c3"]
    assert p.gap_after is None and p.hidden_cols == 18


def test_empty_frames_do_not_crash():  # Review Focus 4
    for df in (pd.DataFrame(), pd.DataFrame({"a": [], "b": []})):
        p = build_preview(df)
        assert p.total_rows == 0
        prof = profile(df)
        assert prof.rows == 0


def test_profile_numbers():
    df = pd.DataFrame({"n": [1.0, 2.0, np.nan, 2.0], "s": ["a", "b", "b", None]})
    prof = profile(df)
    assert (prof.rows, prof.cols) == (4, 2)
    assert prof.columns.loc["n", "nulls"] == 1
    assert prof.columns.loc["n", "unique"] == 2
    assert prof.columns.loc["s", "nulls"] == 1
    assert prof.columns.loc["s", "unique"] == 2
    assert prof.describe.loc["count", "n"] == 3
    assert prof.describe.loc["mean", "n"] == (1 + 2 + 2) / 3


def test_profile_handles_mixed_and_cleaned_headers():  # Review Focus 2
    df = pd.DataFrame({"Unnamed: 0": [1, 2], "a": ["x", 3], "a.1": [None, None]})
    prof = profile(df)
    assert list(prof.columns.index) == ["Unnamed: 0", "a", "a.1"]
    assert prof.columns.loc["a.1", "nulls"] == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_profiler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qxc.profiler'`.

- [ ] **Step 3: Write `src/qxc/profiler.py`**

```python
"""Turn a DataFrame into plain results for the screen.

No file reading and no UI code lives here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Preview:
    """The slice of a table that the preview panel shows."""

    head: pd.DataFrame
    tail: pd.DataFrame  # empty when every row already fits in ``head``
    gap_after: int | None  # put a "..." column after this many columns
    hidden_cols: int
    total_rows: int
    total_cols: int


@dataclass(frozen=True)
class Profile:
    """Facts about a whole table."""

    rows: int
    cols: int
    columns: pd.DataFrame  # index = column name; columns: dtype, nulls, unique
    describe: pd.DataFrame  # describe(include="all"), statistics as rows


def build_preview(
    df: pd.DataFrame,
    n_rows: int = 10,
    n_cols: int = 5,
    columns: Sequence[str] | None = None,
) -> Preview:
    """First/last ``n_rows`` rows and first/last ``n_cols`` columns of ``df``.

    ``columns`` shows exactly those columns instead of the first/last split.
    """
    total_rows, total_cols = df.shape
    gap_after: int | None = None
    if columns is not None:
        view = df.loc[:, list(columns)]
    elif total_cols > 2 * n_cols:
        keep = list(range(n_cols)) + list(range(total_cols - n_cols, total_cols))
        view = df.iloc[:, keep]
        gap_after = n_cols
    else:
        view = df
    hidden = total_cols - view.shape[1]

    if total_rows <= 2 * n_rows:
        head, tail = view, view.iloc[0:0]
    else:
        head, tail = view.head(n_rows), view.tail(n_rows)
    return Preview(head, tail, gap_after, hidden, total_rows, total_cols)


def profile(df: pd.DataFrame) -> Profile:
    """Row/column counts, per-column type, null count and unique count, and ``describe()``."""
    columns = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "nulls": df.isna().sum(),
            "unique": df.nunique(dropna=True),
        }
    )
    try:
        described = df.describe(include="all") if df.shape[1] else pd.DataFrame()
    except ValueError:  # pandas refuses to describe some empty frames
        described = pd.DataFrame()
    return Profile(df.shape[0], df.shape[1], columns, described)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_profiler.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/profiler.py tests/test_profiler.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: add preview slicing and table profiling"
```

---

### Task 6: Command line

**Files:**
- Create: `src/qxc/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `qxc.ui.app.QxcApp(folder: Path, depth: int)` (built in Task 8; imported lazily so this task passes before it exists).
- Produces: `parse_args(argv=None) -> argparse.Namespace` with `.folder: str` (default `"."`) and `.depth: int` (default `0`); `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:
```python
import pytest

from qxc.cli import main, parse_args


def test_defaults_are_current_folder_and_depth_zero():
    args = parse_args([])
    assert args.folder == "." and args.depth == 0


def test_folder_and_depth_are_read():
    args = parse_args(["some/folder", "-r", "3"])
    assert args.folder == "some/folder" and args.depth == 3


def test_negative_depth_is_rejected():
    with pytest.raises(SystemExit):
        parse_args(["-r", "-1"])


def test_non_number_depth_is_rejected():
    with pytest.raises(SystemExit):
        parse_args(["-r", "abc"])


def test_missing_folder_returns_error_code(tmp_path, capsys):
    assert main([str(tmp_path / "nope")]) == 2
    assert "not a folder" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qxc.cli'`.

- [ ] **Step 3: Write `src/qxc/cli.py`**

```python
"""Command line entry point for qxc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _depth(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a whole number") from None
    if value < 0:
        raise argparse.ArgumentTypeError("depth must be 0 or greater")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Read ``qxc [folder] [-r DEPTH]``."""
    parser = argparse.ArgumentParser(
        prog="qxc",
        description="Browse and profile CSV, Excel and LibreOffice Calc files in the terminal.",
    )
    parser.add_argument("folder", nargs="?", default=".", help="folder to scan (default: current folder)")
    parser.add_argument(
        "-r",
        "--depth",
        type=_depth,
        default=0,
        metavar="DEPTH",
        help="subfolder levels to scan below the folder (default: 0 = the folder only)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Start the app. Returns the process exit code."""
    args = parse_args(argv)
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"qxc: not a folder: {folder}", file=sys.stderr)
        return 2
    from qxc.ui.app import QxcApp  # imported here so --help stays fast

    QxcApp(folder, args.depth).run()
    return 0
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_cli.py -v` then `uv run qxc --help`
Expected: tests PASS; help text shows `folder` and `-r DEPTH`.

- [ ] **Step 5: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/cli.py tests/test_cli.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: add qxc command line with -r depth"
```

---

### Task 7: Rich rendering of preview and profile

**Files:**
- Create: `src/qxc/ui/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `Preview`, `Profile` from Task 5.
- Produces:
  - `render_preview(preview: Preview) -> rich.table.Table`
  - `render_profile(profile: Profile) -> rich.console.Group`
  Both only build Rich objects. They never print and never import Textual.

- [ ] **Step 1: Write the failing tests**

`tests/test_render.py`:
```python
import pandas as pd
from rich.console import Console

from qxc.profiler import build_preview, profile
from qxc.ui.render import render_preview, render_profile


def text_of(renderable, width=140):
    console = Console(record=True, width=width, force_terminal=False)
    console.print(renderable)
    return console.export_text()


def test_preview_shows_head_divider_and_tail():
    df = pd.DataFrame({"n": range(100)})
    out = text_of(render_preview(build_preview(df)))
    assert "100 rows" in out
    assert " 0 " in out and "99" in out
    assert "50" not in out  # middle rows are hidden


def test_preview_shows_gap_column_for_wide_tables():
    df = pd.DataFrame({f"c{i}": [i] for i in range(20)})
    out = text_of(render_preview(build_preview(df)), width=250)
    assert "c0" in out and "c19" in out and "c10" not in out
    assert "…" in out


def test_square_brackets_are_shown_literally():  # Review Focus 3
    df = pd.DataFrame({"[red]col[/red]": ["[bold]x[/bold]", "[1]"]})
    out = text_of(render_preview(build_preview(df)))
    assert "[red]col[/red]" in out
    assert "[bold]x[/bold]" in out
    assert "[1]" in out


def test_nulls_are_marked():
    df = pd.DataFrame({"a": [1.0, None]})
    assert "null" in text_of(render_preview(build_preview(df)))


def test_empty_table_renders():  # Review Focus 4
    out = text_of(render_preview(build_preview(pd.DataFrame())))
    assert "0 rows" in out


def test_profile_lists_columns_and_stats():
    df = pd.DataFrame({"n": [1.0, 2.0, None], "s": ["a", "b", "b"]})
    out = text_of(render_profile(profile(df)))
    assert "3 rows" in out and "2 columns" in out
    assert "nulls" in out and "unique" in out
    assert "mean" in out


def test_profile_of_empty_table_renders():  # Review Focus 4
    out = text_of(render_profile(profile(pd.DataFrame())))
    assert "0 rows" in out
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qxc.ui.render'`.

- [ ] **Step 3: Write `src/qxc/ui/render.py`**

```python
"""Turn preview and profile results into Rich tables.

Every cell and header is wrapped in ``Text`` so that data such as ``[red]``
is shown literally instead of being read as Rich markup.
"""

from __future__ import annotations

import pandas as pd
from rich.console import Group
from rich.table import Table
from rich.text import Text

from qxc.profiler import Preview, Profile

GAP = "…"
DIVIDER = "⋮"


def _cell(value) -> Text:
    if value is None or (not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)):
        return Text("null", style="dim italic")
    if isinstance(value, float):
        return Text(f"{value:,.6g}")
    return Text(str(value))


def render_preview(preview: Preview) -> Table:
    """Head rows, a divider, then tail rows, with a ``…`` column where columns were hidden."""
    caption = f"{preview.hidden_cols} columns hidden" if preview.hidden_cols else None
    table = Table(
        title=Text(f"{preview.total_rows:,} rows × {preview.total_cols:,} columns"),
        caption=caption,
        header_style="bold cyan",
    )
    names = list(preview.head.columns)
    for position, name in enumerate(names, start=1):
        table.add_column(Text(str(name)), no_wrap=True, overflow="ellipsis", max_width=20)
        if preview.gap_after == position:
            table.add_column(Text(GAP), justify="center", no_wrap=True)

    def add_rows(frame: pd.DataFrame) -> None:
        for row in frame.itertuples(index=False):
            cells: list[Text] = []
            for position, value in enumerate(row, start=1):
                cells.append(_cell(value))
                if preview.gap_after == position:
                    cells.append(Text(GAP, style="dim"))
            table.add_row(*cells)

    add_rows(preview.head)
    if len(preview.tail):
        width = len(names) + (1 if preview.gap_after else 0)
        table.add_row(*[Text(DIVIDER, style="dim")] * width)
        add_rows(preview.tail)
    return table


def render_profile(profile: Profile) -> Group:
    """Summary line, a per-column table, and the ``describe()`` table."""
    summary = Text(f"{profile.rows:,} rows · {profile.cols:,} columns", style="bold")

    columns = Table(title="Columns", header_style="bold cyan")
    for heading in ("Column", "dtype", "nulls", "unique"):
        columns.add_column(Text(heading), no_wrap=True, overflow="ellipsis", max_width=24)
    for name, row in profile.columns.iterrows():
        columns.add_row(Text(str(name)), Text(row["dtype"]), Text(f"{row['nulls']:,}"), Text(f"{row['unique']:,}"))

    parts: list = [summary, columns]
    stats = profile.describe.T.dropna(axis=1, how="all")
    if not stats.empty:
        described = Table(title="describe()", header_style="bold cyan")
        described.add_column(Text("Column"), no_wrap=True, overflow="ellipsis", max_width=24)
        for stat in stats.columns:
            described.add_column(Text(str(stat)), justify="right", no_wrap=True)
        for name, row in stats.iterrows():
            described.add_row(Text(str(name)), *[_cell(value) for value in row])
        parts.append(described)
    return Group(*parts)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_render.py -v`
Expected: all PASS. If `" 0 " in out` fails because of table border characters, change the assertion to `"0" in out` and keep the `"50" not in out` check; the point of the test is that middle rows are hidden.

- [ ] **Step 5: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/ui/render.py tests/test_render.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: render preview and profile as Rich tables"
```

---

### Task 8: Textual app - file list, filters, open a file

**Files:**
- Create: `src/qxc/ui/app.py`, `src/qxc/ui/screens.py`, `src/qxc/ui/qxc.tcss`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `scan`, `filter_files`, `parse_date`, `FileRecord` (Task 2); `list_sheets`, `load_table`, `is_large`, `LoaderError`, `SheetInfo` (Tasks 3-4); `build_preview`, `profile` (Task 5); `render_preview`, `render_profile` (Task 7).
- Produces:
  - `QxcApp(folder: Path, depth: int = 0)`, a Textual `App`. State attributes used by tests: `records`, `visible`, `current`, `df`, `profile_result`, `selected_columns`, `type_index`.
  - `ConfirmLargeFile(size_bytes: int)`: a `ModalScreen[bool]`; `y` returns `True`, `n`/`escape` returns `False`.
  - Widget ids: `#search`, `#type`, `#date-from`, `#date-to`, `#files` (DataTable), `#sheets` (OptionList), `#preview`, `#profile`, `#status`, `#main`.
  - Keys: `/` search, `d` dates, `t` cycle type, `F5` refresh, `Escape` back to the file list, `q` quit. (`c` and `p` come in Tasks 9 and 10.)
  - A file opens with **Enter** (not on every arrow press), so moving through a long list never triggers a load.

UI tests run the app headless. They use `asyncio.run(...)` so no extra test library is needed.

- [ ] **Step 1: Write the failing tests**

`tests/test_app.py`:
```python
import asyncio

import pandas as pd
from textual.widgets import DataTable, Input

from qxc.ui import app as app_module
from qxc.ui.app import QxcApp
from qxc.ui.screens import ConfirmLargeFile


def run(scenario):
    asyncio.run(scenario())


async def settle(app, pilot):
    await app.workers.wait_for_complete()
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


def make_folder(tmp_path):
    (tmp_path / "alpha.csv").write_text("x,y\n1,2\n3,4\n")
    (tmp_path / "beta.csv").write_text("name\nAnn\n")
    sub = tmp_path / "deeper"
    sub.mkdir()
    (sub / "gamma.csv").write_text("a\n1\n")
    return tmp_path


def test_lists_files_at_requested_depth(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        for depth, expected in ((0, 2), (1, 3)):
            app = QxcApp(folder, depth=depth)
            async with app.run_test(size=(160, 50)) as pilot:
                await settle(app, pilot)
                assert app.query_one("#files", DataTable).row_count == expected

    run(scenario)


def test_search_filters_the_list(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QxcApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#search", Input).value = "alp"
            await pilot.pause()
            assert [r.name for r in app.visible] == ["alpha.csv"]
            app.query_one("#search", Input).value = "zzz"
            await pilot.pause()
            assert app.query_one("#files", DataTable).row_count == 0

    run(scenario)


def test_type_key_cycles_filter(tmp_path):
    folder = make_folder(tmp_path)
    (folder / "book.ods").write_bytes(b"")

    async def scenario():
        app = QxcApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("t")  # csv
            assert {r.ext for r in app.visible} == {".csv"}
            await pilot.press("t", "t", "t")  # xlsx, xls, ods
            assert {r.ext for r in app.visible} == {".ods"}
            await pilot.press("t")  # back to all
            assert len(app.visible) == 3

    run(scenario)


def test_bad_date_marks_the_box_and_is_ignored(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QxcApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            box = app.query_one("#date-from", Input)
            box.value = "2025-13-40"
            await pilot.pause()
            assert box.has_class("invalid")
            assert len(app.visible) == 2
            box.value = "2000-01-01"
            await pilot.pause()
            assert not box.has_class("invalid")

    run(scenario)


def test_enter_opens_file_and_fills_preview_and_profile(tmp_path):
    folder = make_folder(tmp_path)

    async def scenario():
        app = QxcApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            assert app.current.name == "alpha.csv"
            assert app.df.shape == (2, 2)
            assert app.profile_result.rows == 2

    run(scenario)


def test_empty_folder_shows_no_files(tmp_path):
    async def scenario():
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            assert app.query_one("#files", DataTable).row_count == 0

    run(scenario)


def test_corrupt_file_shows_error_not_crash(tmp_path):
    (tmp_path / "bad.xlsx").write_bytes(b"not a zip")

    async def scenario():
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            assert app.df is None

    run(scenario)


def test_large_file_asks_before_loading(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    monkeypatch.setattr(app_module, "is_large", lambda size: True)

    async def scenario():
        app = QxcApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmLargeFile)
            await pilot.press("n")
            await settle(app, pilot)
            assert app.df is None
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("y")
            await settle(app, pilot)
            assert app.df is not None

    run(scenario)


def test_stale_result_is_ignored(tmp_path):  # Review Focus 5
    folder = make_folder(tmp_path)

    async def scenario():
        app = QxcApp(folder, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            current = app.visible[0]
            app.current = current
            app._token = 5
            stale = pd.DataFrame({"old": [1]})
            app._show_table(4, current, None, None, stale, app_module.profile(stale))
            assert app.df is None  # token 4 is older than 5, so ignored
            fresh = pd.DataFrame({"new": [1]})
            app._show_table(5, current, None, None, fresh, app_module.profile(fresh))
            assert list(app.df.columns) == ["new"]

    run(scenario)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qxc.ui.app'`.

- [ ] **Step 3: Write `src/qxc/ui/screens.py`** (large-file prompt now; column picker added in Task 9)

```python
"""Pop-up screens for qxc."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label


class ConfirmLargeFile(ModalScreen[bool]):
    """Ask before loading a file over the 50 MB limit. ``y`` loads it, ``n`` or Escape cancels."""

    BINDINGS = [
        ("y", "answer(True)", "Load anyway"),
        ("n", "answer(False)", "Cancel"),
        ("escape", "answer(False)", "Cancel"),
    ]

    def __init__(self, size_bytes: int) -> None:
        super().__init__()
        self.size_mb = size_bytes / (1024 * 1024)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Large file ({self.size_mb:,.1f} MB). Load anyway?")
            yield Label("Press y to load, n to cancel")

    def action_answer(self, answer: bool) -> None:
        self.dismiss(answer)
```

- [ ] **Step 4: Write `src/qxc/ui/qxc.tcss`**

```css
#filters { height: 3; }
#search { width: 1fr; }
#type { width: 14; content-align: center middle; }
#date-from, #date-to { width: 22; }
Input.invalid { border: tall red; }

#main { height: 1fr; }
#files { width: 2fr; }
#sheets { width: 30; }
#right { width: 3fr; }
#preview-box, #profile-box { height: 1fr; border: round $primary; }

#status { height: 1; padding: 0 1; color: $text-muted; }

ConfirmLargeFile { align: center middle; }
#dialog { width: 50; height: auto; padding: 1 2; border: thick $warning; background: $surface; }
```

- [ ] **Step 5: Write `src/qxc/ui/app.py`**

```python
"""The qxc Textual application: layout, background loading and key actions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from qxc.loader import LoaderError, SheetInfo, is_large, list_sheets, load_table
from qxc.profiler import Profile, build_preview, profile
from qxc.scanner import FileRecord, filter_files, parse_date, scan
from qxc.ui.render import render_preview, render_profile
from qxc.ui.screens import ConfirmLargeFile

# (label, extensions) in the order the ``t`` key cycles through them
TYPE_CHOICES: list[tuple[str, frozenset[str] | None]] = [
    ("all", None),
    ("csv", frozenset({".csv"})),
    ("xlsx", frozenset({".xlsx", ".xlsm"})),
    ("xls", frozenset({".xls"})),
    ("ods", frozenset({".ods"})),
]
SEP = "\x1f"  # separates parts of an option id; cannot appear in a sheet name
COLUMN_WIDTH = 15  # rough width of one preview column, used to pick how many fit


def human_size(size: int) -> str:
    """12345 -> '12.1 KB'."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:,.0f} {unit}" if unit == "B" else f"{value:,.1f} {unit}"
        value /= 1024
    return f"{size} B"


class QxcApp(App):
    """Browse table files in a folder and see a preview and profile of each."""

    TITLE = "qxc"
    CSS_PATH = "qxc.tcss"
    BINDINGS = [
        ("slash", "focus_search", "Search"),
        ("d", "focus_dates", "Dates"),
        ("t", "cycle_type", "Type"),
        ("f5", "refresh", "Refresh"),
        ("escape", "focus_files", "Files"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, folder: Path, depth: int = 0) -> None:
        super().__init__()
        self.folder = Path(folder)
        self.depth = depth
        self.records: list[FileRecord] = []
        self.visible: list[FileRecord] = []
        self.type_index = 0
        self.current: FileRecord | None = None
        self.sheets: list[SheetInfo] = []
        self.df: pd.DataFrame | None = None
        self.profile_result: Profile | None = None
        self.selected_columns: list[str] | None = None
        self._token = 0  # bumped on every new selection so old results can be ignored

    # ---------------------------------------------------------------- layout
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="filters"):
            yield Input(placeholder="Search name…", id="search")
            yield Static("Type: all", id="type")
            yield Input(placeholder="From YYYY-MM-DD", id="date-from")
            yield Input(placeholder="To YYYY-MM-DD", id="date-to")
        with Horizontal(id="main"):
            yield DataTable(id="files", cursor_type="row")
            yield OptionList(id="sheets")
            with Vertical(id="right"):
                with VerticalScroll(id="preview-box"):
                    yield Static("Select a file and press Enter", id="preview")
                with VerticalScroll(id="profile-box"):
                    yield Static("", id="profile")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#files", DataTable)
        table.add_columns("Lvl", "Name", "Folder", "Modified", "Size")
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
        self.visible = filter_files(
            self.records,
            name=self.query_one("#search", Input).value,
            exts=exts,
            date_from=self._read_date("#date-from"),
            date_to=self._read_date("#date-to"),
        )
        table = self.query_one("#files", DataTable)
        table.clear()
        for rec in self.visible:
            table.add_row(
                str(rec.level),
                rec.name,
                rec.rel_dir or ".",
                f"{rec.modified:%Y-%m-%d %H:%M}",
                human_size(rec.size),
                key=str(rec.path),
            )
        if self.records:
            self._set_status(f"{len(self.visible)} of {len(self.records)} files · depth {self.depth}")
        else:
            self._set_status("No files match" if self.depth == 0 else "No files found")

    def on_input_changed(self, event: Input.Changed) -> None:
        self.apply_filters()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(Text(message))

    # --------------------------------------------------------------- actions
    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_focus_dates(self) -> None:
        self.query_one("#date-from", Input).focus()

    def action_focus_files(self) -> None:
        self.query_one("#files", DataTable).focus()

    def action_cycle_type(self) -> None:
        self.type_index = (self.type_index + 1) % len(TYPE_CHOICES)
        self.query_one("#type", Static).update(Text(f"Type: {TYPE_CHOICES[self.type_index][0]}"))
        self.apply_filters()

    def action_refresh(self) -> None:
        self._set_status("Scanning…")
        self.rescan()

    # ----------------------------------------------------------- open a file
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value
        record = next((r for r in self.visible if str(r.path) == key), None)
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
        self.current = record
        self.df = None
        self.profile_result = None
        self.selected_columns = None
        self.sheets = []
        self.sub_title = f"{record.path}  ·  Lvl {record.level}"
        self.query_one("#sheets", OptionList).display = False
        self.query_one("#preview", Static).update(Text("Loading…", style="dim"))
        self.query_one("#profile", Static).update("")
        self._load_sheets(self._token, record)

    @work(thread=True, exclusive=True, group="load")
    def _load_sheets(self, token: int, record: FileRecord) -> None:
        try:
            sheets = list_sheets(record.path)
        except LoaderError as exc:
            self.call_from_thread(self._show_error, token, str(exc))
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
        self.query_one("#preview", Static).update(Text("Loading…", style="dim"))
        self._load_table(self._token, record, sheet, table)

    @work(thread=True, exclusive=True, group="table")
    def _load_table(self, token: int, record: FileRecord, sheet: str | None, table: str | None) -> None:
        try:
            df = load_table(record.path, sheet, table)
            result = profile(df)
        except LoaderError as exc:
            self.call_from_thread(self._show_error, token, str(exc))
            return
        self.call_from_thread(self._show_table, token, record, sheet, table, df, result)

    # --------------------------------------------------------------- results
    def _show_error(self, token: int, message: str) -> None:
        if token != self._token:
            return
        self.df = None
        self.profile_result = None
        self.query_one("#preview", Static).update(Text(message, style="bold red"))
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
        self._set_status(f"{record.name}{where} · {len(df):,} rows")

    def _columns_that_fit(self) -> int:
        width = self.query_one("#preview-box").size.width or 80
        return max(1, min(5, (width // COLUMN_WIDTH) // 2))

    def _render_views(self) -> None:
        if self.df is None or self.profile_result is None:
            return
        preview = build_preview(self.df, 10, self._columns_that_fit(), self.selected_columns)
        self.query_one("#preview", Static).update(render_preview(preview))
        self.query_one("#profile", Static).update(render_profile(self.profile_result))

    def on_resize(self) -> None:
        self._render_views()
```

- [ ] **Step 6: Run to verify pass**

Run: `uv run pytest tests/test_app.py -v`
Expected: all PASS. Textual API names (`DataTable.RowSelected`, `OptionList.OptionSelected`, `Static.update`, `workers.wait_for_complete`) may differ slightly in the installed version. If one fails, read the error, check the installed Textual docs, and fix the call while keeping the test's intent.

- [ ] **Step 7: Run it by hand**

Run: `uv run qxc` in a folder that contains a CSV, then `uv run qxc . -r 2`.
Expected: files list; Enter opens a file; preview and profile fill in. Report anything that looks wrong rather than guessing.

- [ ] **Step 8: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/ui tests/test_app.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: add Textual app with file list, filters, sheets, preview and profile"
```

---

### Task 9: Column picker

**Files:**
- Modify: `src/qxc/ui/screens.py` (add `ColumnPicker`), `src/qxc/ui/app.py` (binding `c`, action, callback), `src/qxc/ui/qxc.tcss`
- Test: `tests/test_app.py` (append)

**Interfaces:**
- Consumes: `QxcApp.df`, `QxcApp.selected_columns`, `build_preview` (Task 5).
- Produces: `ColumnPicker(all_columns: list[str], checked: set[str])`, a `ModalScreen[list[str] | None]` using a checkbox list. Enter confirms and returns the checked names in the table's original order (an empty selection means "back to the default"); Escape cancels and returns `None`. Key `c` opens it.

- [ ] **Step 1: Append the failing tests to `tests/test_app.py`**

```python
from qxc.ui.screens import ColumnPicker


def test_column_picker_limits_preview_columns(tmp_path):
    (tmp_path / "wide.csv").write_text("a,b,c,d\n1,2,3,4\n")

    async def scenario():
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, ColumnPicker)
            app.screen.dismiss(["b", "d"])
            await pilot.pause()
            assert app.selected_columns == ["b", "d"]

    run(scenario)


def test_column_picker_empty_result_resets_to_default(tmp_path):
    (tmp_path / "wide.csv").write_text("a,b\n1,2\n")

    async def scenario():
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("enter")
            await settle(app, pilot)
            app.selected_columns = ["a"]
            await pilot.press("c")
            await pilot.pause()
            app.screen.dismiss([])
            await pilot.pause()
            assert app.selected_columns is None

    run(scenario)


def test_c_does_nothing_before_a_file_is_open(tmp_path):
    (tmp_path / "a.csv").write_text("a\n1\n")

    async def scenario():
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 50)) as pilot:
            await settle(app, pilot)
            app.query_one("#files", DataTable).focus()
            await pilot.press("c")
            await pilot.pause()
            assert not isinstance(app.screen, ColumnPicker)

    run(scenario)
```
- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_app.py -k column_picker -v`
Expected: FAIL with `ImportError: cannot import name 'ColumnPicker'`.

- [ ] **Step 3: Add `ColumnPicker` to `screens.py`**

Add these imports at the top: `from textual.widgets import Label, SelectionList` (replace the existing `Label` import line). Append:
```python
class ColumnPicker(ModalScreen["list[str] | None"]):
    """Checkbox list of column names. Enter confirms, Escape cancels.

    Returns the checked names in the table's original order, ``[]`` when none
    are checked (meaning "use the default view"), or ``None`` when cancelled.
    """

    BINDINGS = [("enter", "confirm", "Apply"), ("escape", "cancel", "Cancel")]

    def __init__(self, all_columns: list[str], checked: set[str]) -> None:
        super().__init__()
        self.all_columns = all_columns
        self.checked = checked

    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            yield Label("Choose columns (space = toggle, Enter = apply, Esc = cancel)")
            yield SelectionList[str](*[(name, name, name in self.checked) for name in self.all_columns])

    def action_confirm(self) -> None:
        chosen = set(self.query_one(SelectionList).selected)
        self.dismiss([name for name in self.all_columns if name in chosen])

    def action_cancel(self) -> None:
        self.dismiss(None)
```

- [ ] **Step 4: Wire it into `app.py`**

Add `("c", "pick_columns", "Columns"),` to `BINDINGS`, import `ColumnPicker` from `qxc.ui.screens`, and add these methods to `QxcApp`:
```python
    def action_pick_columns(self) -> None:
        if self.df is None:
            return
        shown = build_preview(self.df, 10, self._columns_that_fit(), self.selected_columns).head.columns
        names = [str(c) for c in self.df.columns]

        def after(chosen: list[str] | None) -> None:
            if chosen is None:
                return
            self.selected_columns = chosen or None
            self._render_views()

        self.push_screen(ColumnPicker(names, set(shown)), after)
```
Append to `qxc.tcss`:
```css
ColumnPicker { align: center middle; }
#picker { width: 60; height: 70%; padding: 1 2; border: thick $primary; background: $surface; }
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_app.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/ui tests/test_app.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: add column picker for the preview"
```

---

### Task 10: Narrow terminal layout

**Files:**
- Modify: `src/qxc/ui/app.py`, `src/qxc/ui/qxc.tcss`
- Test: `tests/test_app.py` (append)

**Interfaces:**
- Produces: when the terminal is narrower than 110 columns, `#main` gets the CSS class `narrow` and only one of Preview/Profile shows; key `p` toggles which one (class `show-profile`). On wide terminals both show and `p` does nothing visible.

- [ ] **Step 1: Append the failing test**

```python
def test_narrow_terminal_uses_one_panel_and_p_toggles(tmp_path):
    (tmp_path / "a.csv").write_text("a\n1\n")

    async def scenario():
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(90, 40)) as pilot:
            await settle(app, pilot)
            main = app.query_one("#main")
            assert main.has_class("narrow")
            assert not main.has_class("show-profile")
            await pilot.press("p")
            assert main.has_class("show-profile")
        app = QxcApp(tmp_path, depth=0)
        async with app.run_test(size=(160, 40)) as pilot:
            await settle(app, pilot)
            assert not app.query_one("#main").has_class("narrow")

    run(scenario)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_app.py -k narrow -v`
Expected: FAIL (`narrow` class never set).

- [ ] **Step 3: Implement**

In `app.py` add `("p", "toggle_panel", "Preview/Profile"),` to `BINDINGS`, add this action, and replace `on_resize`:
```python
    def action_toggle_panel(self) -> None:
        self.query_one("#main").toggle_class("show-profile")

    def on_resize(self) -> None:
        self.query_one("#main").set_class(self.size.width < 110, "narrow")
        self._render_views()
```
Append to `qxc.tcss`:
```css
#main.narrow #profile-box { display: none; }
#main.narrow.show-profile #profile-box { display: block; }
#main.narrow.show-profile #preview-box { display: none; }
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest -v`
Expected: the whole suite PASSES (`.xls` test may show SKIPPED).

- [ ] **Step 5: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add src/qxc/ui tests/test_app.py
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "feat: collapse preview/profile into one panel on narrow terminals"
```

---

### Task 11: Documentation, changelog, logs and final check

**Files:**
- Create/modify: `README.md`, `src/qxc/README.md`, `src/qxc/ui/README.md`, `tests/README.md`, `docs/README.md`, `CHANGELOG.md`
- Append: `A:\WorkScripts\session_log.md`

**Interfaces:** none. Documents everything built in Tasks 1-10.

- [ ] **Step 1: Write the plain-language README files**

Each README starts with a **Created:** line with a local timestamp and offset. Write them for a person who has not seen the code. Check spelling and grammar (Jose's rule).

- `README.md` (project root): what qxc is (one paragraph); install and run (`uv sync`, `uv run qxc`, `uv run qxc <folder> -r 2`); the `-r` depth rule with the `Lvl` example (`0` = folder, `1` = first subfolder); the screen layout; a key table (`/` search, `d` dates, `t` type, `Enter` open, `c` columns, `p` switch Preview/Profile on narrow screens, `F5` refresh, `Esc` back to the list, `q` quit); supported file types and what works for each (Tables = `.xlsx` only; sheet sizes unavailable for `.ods`); the 50 MB warning; "view-only in Phase 1"; links to the spec and plan; the phase roadmap.
- `src/qxc/README.md`: one short paragraph per module (`cli`, `scanner`, `loader`, `profiler`, `ui/`) saying what it does, what it depends on, and that only `loader` reads files.
- `src/qxc/ui/README.md`: what `app.py`, `render.py`, `screens.py`, `qxc.tcss` each do; why rendering is separate from the app (so it can be tested); how background loading and the "ignore stale results" token work, in plain words.
- `tests/README.md`: how to run tests (`uv run pytest -v`), what each test file covers, why UI tests use `asyncio.run`, and the optional `tests/data/sample.xls` (a tiny file with no real client data) that enables the `.xls` test.
- `docs/README.md`: list the spec and plan with their dates and what each is for.

- [ ] **Step 3: Write `CHANGELOG.md`** (keepachangelog.com format)

```markdown
# Changelog

All notable changes to qxc are listed here. Format: https://keepachangelog.com/en/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-10-07
### Added
- `qxc [folder] [-r DEPTH]` command with a three-column terminal layout.
- File index with level, folder, modified date and size.
- Search by name, filter by file type, filter by modified-date range.
- Support for CSV, XLSX/XLSM, XLS and ODS files; sheet list and named Excel Tables (XLSX only).
- Preview of first/last 10 rows and first/last 5 columns, with an optional column picker.
- Profile: rows, columns, nulls, unique counts and `describe()`.
- Warning before loading files over 50 MB.
```
(Use the real completion date if it differs from 2026-10-07.)

- [ ] **Step 4: Full verification (evidence before claiming done)**

Run: `uv run pytest -v`
Expected: all tests PASS (`.xls` SKIPPED unless Jose supplied a sample). Paste the summary line into the report.

Run by hand and report what you saw: `uv run qxc`, `uv run qxc . -r 2`, `uv run qxc A:\nope` (expect "not a folder" and exit code 2), a real CSV, a real `.xlsx` with more than one sheet, an `.ods` file, and (if available) a file over 50 MB. Do not claim any of these worked unless you ran them.

- [ ] **Step 5: Log the work**

Append a dated entry (local time with offset) to `A:\WorkScripts\session_log.md` listing: files created/modified, libraries added (`openpyxl`, `odfpy`, `xlrd`, `pytest`, all approved by Jose), the `requires-python` change from `>=3.15` to `>=3.12` with the reason, the backups made, and the decisions from the spec. Redact any sensitive data. Grammar and spelling check.

- [ ] **Step 6: Commit** (if approved)

```bash
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV add .
git -c safe.directory=A:/WorkScripts/Python/Quick_Excel_CSV -C A:/WorkScripts/Python/Quick_Excel_CSV commit -m "docs: add READMEs and changelog for qxc 0.1.0"
```

---

## Self-Review

**Spec coverage**

| Spec item | Task |
|---|---|
| 4 Command line, `-r` depth, default 0, bare `qxc` | 6 (`parse_args`), 2 (`scan`) |
| 5 Three-column layout, sheets column only for Excel/ODS, narrow collapse | 8, 10 |
| 6.1 File index with `Lvl` and relative path | 8 (`apply_filters`), 2 |
| 6.2 Search by name | 2, 8 |
| 6.3 Type filter | 2, 8 (`t` key) |
| 6.4 Modified-date filter, `YYYY-MM-DD`, blank allowed, red on bad input | 2, 8 |
| 6.5 Sheets and named Tables (`.xlsx` only), sheet size | 4, 8 |
| 6.6 Preview head/tail 10, columns first/last 5, `...` column | 5, 7, 8 |
| 6.7 Profile: rows, columns, cardinality, nulls, `describe()` | 5, 7 |
| 6.8 Column picker | 9 |
| 6.9 `F5` refresh | 8 |
| 6.10 Header shows full path and level | 8 (`sub_title`) |
| 8 Background loading, 50 MB prompt | 3 (`is_large`), 8 |
| 9 Error handling (locked, corrupt, password, bad date, no matches, empty sheet) | 3, 4, 8 |
| 10 Testing with pytest + headless Textual tests | 2-10 |
| 11.1 `requires-python` change | 1 |
| READMEs for humans, changelog | 11 |

**Known differences from the spec (to confirm with Jose)**
1. `ui/widgets.py` is split into `ui/render.py` and `ui/screens.py`.
2. "Collapse into tabs" on narrow screens is a `p` toggle between Preview and Profile.
3. Sheet size is the **used range** (so it can include the header row) and is shown for `.xlsx` and `.xls`; `.ods` sheets show names only because pandas cannot give a size without reading each sheet.
4. A file opens with Enter, not on every arrow key.
5. The `.xls` test is skipped until Jose supplies a tiny `sample.xls`, because creating one needs `xlwt`, which is not an approved library.
6. Excel lock files (`~$name.xlsx`) are ignored by the scanner (not in the spec; added because they would otherwise show up as unreadable files).

**Placeholder scan:** none. Every code step contains the code.

**Type consistency checked:** `FileRecord`, `SheetInfo`, `Preview`, `Profile` field names and the function signatures `scan`, `filter_files`, `parse_date`, `list_sheets`, `load_table`, `is_large`, `build_preview`, `profile`, `render_preview`, `render_profile`, `QxcApp(folder, depth)`, `ConfirmLargeFile(size_bytes)`, `ColumnPicker(all_columns, checked)` match between the tasks that define them and the tasks that use them. `_show_table(token, record, sheet, table, df, result)` matches its test.
