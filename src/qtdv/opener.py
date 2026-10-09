"""Open a file in the program the operating system uses for it.

Windows, macOS and Linux each have their own way to do this, so this module is
the only place that knows about them. It uses only the standard library.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class OpenError(Exception):
    """The file could not be opened. The message is written for the user to read."""


def open_in_default_program(path: Path | str) -> None:
    """Ask the operating system to open ``path`` in its default program.

    Returns as soon as the request is sent; it does not wait for the program.
    """
    path = Path(path)
    if not path.is_file():
        raise OpenError(f"File not found: {path.name}")
    target = str(path.resolve())
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]  # exists on Windows only
        elif sys.platform == "darwin":
            _launch(["open", target])
        else:
            if shutil.which("xdg-open") is None:
                raise OpenError("Cannot open it here: xdg-open is not installed")
            _launch(["xdg-open", target])
    except OSError as exc:
        raise OpenError(f"Cannot open {path.name}: {exc}") from exc


def _launch(command: list[str]) -> None:
    """Start a helper program without a shell and without tying it to the terminal."""
    subprocess.Popen(  # noqa: S603 - a list of arguments, never a shell string
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
