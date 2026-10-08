import pandas as pd
import pytest

from qtdv.loader import LARGE_FILE_BYTES, LoaderError, is_large, list_sheets, load_table


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


def test_long_digit_ids_with_blanks_stay_text(tmp_path):  # review #2
    df = load_table(write(tmp_path / "id.csv", "id,x\n1234567890123456,1\n,2\n"))
    assert df["id"].iloc[0] == "1234567890123456"


def test_ragged_row_is_not_shifted(tmp_path):  # review #9
    df = load_table(write(tmp_path / "r.csv", "a,b\n1,2,3,4\n"))
    assert df.iloc[0].tolist() == [1, 2]
