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
