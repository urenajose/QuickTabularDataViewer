# TODO

**Created:** 2026-10-09 06:20 PM -04:00

Things that are waiting for a decision or that were put off on purpose.

## Waiting for a decision

- [ ] `tests/data/5677d895bf4e48a9a34bf4e4d9ef1291.xlsx` is untracked on purpose.
      Check that it holds no real client data before it is added to git. If it
      does, add private test files to `.gitignore` instead.
- [ ] Delete the local backup branch `backup/pre-rewrite-2026-10-08` when it is
      no longer needed.

## Planned

- [ ] Phase 2: edit cell values in `.csv` and `.tsv` files only. Save to the file
      or as a copy.
- [ ] Phase 3: add and delete rows and columns, and rename columns, in `.csv` and
      `.tsv` files only.
- Excel and LibreOffice files (`.xlsx`, `.xlsm`, `.xls`, `.ods`) stay view-only.
  They can be opened in the default program with `o`.

## Put off (minor)

- [ ] The encoding fallback reads a large file again for each encoding it tries.
- [ ] Every keystroke in the search box rebuilds the whole file table.
- [ ] A semicolon-delimited CSV loads as one column.
- [ ] An `.ods` file is parsed twice (once for the sheet list, once for the data).
- [ ] ZIP codes in `.xlsx` files lose their leading zeros (Excel stores them as numbers).
- [ ] `textual-dev` is a runtime dependency; it should be a development one.
- [ ] `.ods` sheets show no row and column sizes in the Sheets / Tables panel.
- [ ] Profile rows are not shaded (left off on purpose; add only if asked).

## Decided (for the record)

- `tests/data/us_states_and_abbreviations.csv` keeps its damaged line 15 on purpose,
  as an example of a malformed row.
