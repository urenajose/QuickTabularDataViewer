"""Pop-up screens for qxc."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, SelectionList


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


class _Checklist(SelectionList[str]):
    """A checklist where Space toggles an item and Enter applies the choice.

    The built-in list uses Enter to toggle, which would leave the pop-up open.
    """

    BINDINGS = [("enter", "apply", "Apply")]

    def action_apply(self) -> None:
        self.screen.action_confirm()


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
            # Text(...) so names such as [/] are shown literally instead of read as markup
            yield _Checklist(*[(Text(name), name, name in self.checked) for name in self.all_columns])

    def action_confirm(self) -> None:
        chosen = set(self.query_one(_Checklist).selected)
        self.dismiss([name for name in self.all_columns if name in chosen])

    def action_cancel(self) -> None:
        self.dismiss(None)
