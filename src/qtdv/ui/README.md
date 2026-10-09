# qtdv screen code

**Created:** 2026-10-07 01:50 PM -04:00

| File | Job |
|------|-----|
| `app.py` | The Textual app: lays out the screen, handles keys, and starts background loading. |
| `render.py` | Turns preview and profile results into Rich tables. It has no Textual code, so it is easy to test. |
| `screens.py` | The two pop-ups: the large-file question (`y`/`n`) and the column picker. |
| `qtdv.tcss` | Colors, sizes and the three-panel layout (Files over Sheets and Profile, Preview on the right) and the narrow-terminal rules. |

## Why drawing is separate from the app

`render.py` only builds Rich tables from plain results. Tests can print those
tables and check the text without starting the whole app.

## Background loading, in plain words

Reading a big workbook can take seconds. `app.py` does the reading in a
background worker so the screen stays responsive and shows `Loading…`.

If you choose another file or sheet while an earlier one is still loading, the
earlier result is thrown away. Each selection gets a number (`_token`). When a
result arrives with an old number, the app ignores it. That way you never see
the previous file's data after choosing a new one.

## Things to know when changing this code

- Names such as `visible` are already used by Textual, so the app calls its
  filtered list `shown_files`.
- Cell text and column names are always wrapped in Rich `Text`, so data like
  `[red]` shows exactly as written.
- The column picker uses its own checklist (`_Checklist`) so Enter applies the
  choice. The built-in list uses Enter to toggle an item.
