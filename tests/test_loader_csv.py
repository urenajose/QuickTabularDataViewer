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


def test_extra_field_on_a_later_row_is_cut_and_reported(tmp_path):  # the us_states file
    df = load_table(write(tmp_path / "late.csv", "a,b\n1,2\n3,4,5\n6,7\n"))
    assert df.shape == (3, 2)
    assert df.values.tolist() == [[1, 2], [3, 4], [6, 7]]
    (note,) = df.attrs["notes"]
    assert "1 row" in note and "line 3" in note


def test_a_clean_file_has_no_notes(tmp_path):
    assert not load_table(write(tmp_path / "ok.csv", "a,b\n1,2\n")).attrs.get("notes")


def test_us_states_sample_file_loads():
    from pathlib import Path

    df = load_table(Path(__file__).parent / "data" / "us_states_and_abbreviations.csv")
    assert df.shape == (43, 2)
    assert "line 15" in df.attrs["notes"][0]


def test_tsv_is_split_on_tabs_and_keeps_commas_in_values(tmp_path):
    df = load_table(write(tmp_path / "a.tsv", "id\tname\n1\tSmith, Ann\n2\tBo\n"))
    assert df.columns.tolist() == ["id", "name"]
    assert df["name"].tolist() == ["Smith, Ann", "Bo"]
    assert pd.api.types.is_numeric_dtype(df["id"])


def test_tsv_keeps_leading_zeros_and_has_no_sheets(tmp_path):
    path = write(tmp_path / "a.tsv", "zip\tcity\n00501\tHoltsville\n")
    assert load_table(path)["zip"].tolist() == ["00501"]
    assert list_sheets(path) == []


def test_tsv_row_with_an_extra_field_is_cut_and_reported(tmp_path):
    df = load_table(write(tmp_path / "a.tsv", "a\tb\n1\t2\n3\t4\t5\n"))
    assert df.shape == (2, 2)
    assert "1 row had extra fields" in df.attrs["notes"][0]
