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
