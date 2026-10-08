import pytest

from qtdv.cli import main, parse_args


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
