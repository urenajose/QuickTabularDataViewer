"""Find table files in a folder and filter them.

This module never reads file contents and has no UI or pandas code.
It only looks at names, sizes and dates.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SUPPORTED_EXTENSIONS = frozenset({".csv", ".tsv", ".xlsx", ".xlsm", ".xls", ".ods"})


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
