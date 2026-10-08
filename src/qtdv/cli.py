"""Command line entry point for qtdv."""

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
    """Read ``qtdv [folder] [-r DEPTH]``."""
    parser = argparse.ArgumentParser(
        prog="qtdv",
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
        print(f"qtdv: not a folder: {folder}", file=sys.stderr)
        return 2
    from qtdv.ui.app import QxcApp  # imported here so --help stays fast

    QxcApp(folder, args.depth).run()
    return 0
