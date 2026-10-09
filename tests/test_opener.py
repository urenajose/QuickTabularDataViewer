import pytest

from qtdv import opener
from qtdv.opener import OpenError, open_in_default_program


@pytest.fixture
def book(tmp_path):
    path = tmp_path / "book name [1].xlsx"
    path.write_bytes(b"")
    return path


class Launched:
    """Stands in for subprocess.Popen and remembers the command it was given."""

    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))


def test_windows_uses_startfile(book, monkeypatch):
    seen = []
    monkeypatch.setattr(opener.sys, "platform", "win32")
    monkeypatch.setattr(opener.os, "startfile", seen.append, raising=False)
    open_in_default_program(book)
    assert seen == [str(book.resolve())]


def test_macos_uses_open_without_a_shell(book, monkeypatch):
    popen = Launched()
    monkeypatch.setattr(opener.sys, "platform", "darwin")
    monkeypatch.setattr(opener.subprocess, "Popen", popen)
    open_in_default_program(book)
    ((command, kwargs),) = popen.calls
    assert command == ["open", str(book.resolve())]  # a list, so the odd characters in the name are safe
    assert not kwargs.get("shell")


def test_linux_uses_xdg_open(book, monkeypatch):
    popen = Launched()
    monkeypatch.setattr(opener.sys, "platform", "linux")
    monkeypatch.setattr(opener.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(opener.subprocess, "Popen", popen)
    open_in_default_program(book)
    ((command, _),) = popen.calls
    assert command == ["xdg-open", str(book.resolve())]


def test_linux_without_xdg_open_says_so(book, monkeypatch):
    monkeypatch.setattr(opener.sys, "platform", "linux")
    monkeypatch.setattr(opener.shutil, "which", lambda name: None)
    with pytest.raises(OpenError, match="xdg-open"):
        open_in_default_program(book)


def test_a_missing_file_is_reported(tmp_path):
    with pytest.raises(OpenError, match="not found"):
        open_in_default_program(tmp_path / "gone.xlsx")


def test_a_launcher_failure_becomes_an_open_error(book, monkeypatch):
    def broken(command, **kwargs):
        raise OSError("no handler")

    monkeypatch.setattr(opener.sys, "platform", "darwin")
    monkeypatch.setattr(opener.subprocess, "Popen", broken)
    with pytest.raises(OpenError, match="no handler"):
        open_in_default_program(book)
