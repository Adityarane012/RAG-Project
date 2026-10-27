# Reports

- `HF_Model_Finder_Report_Simple.docx` / `.pdf` (13 pages): plain-language version with the team details on the cover, 12 references and UML diagrams (PlantUML sources in `source/uml`; the other editions still contain the older drawn diagrams).
- `HF_Model_Finder_Report_Short.docx` / `.pdf` (18 pages): the condensed report to submit. Cover, abstract, contents, six chapters,
  45 IEEE references and two appendices.
- `HF_Model_Finder_Capstone_Report.docx` / `.pdf` (104 pages): the full edition, following the capstone template in detail.

Fill in the highlighted placeholders on the cover (programme, stream, roll number, SAP ID, mentor, academic year) and confirm the
author name. Contents page numbers are static text; update them by hand after editing, or rebuild.

## Rebuild

```bash
EDITION=simple python report/source/build.py   # 12-page plain-language edition (source/src_simple)
EDITION=short python report/source/build.py    # 18-page edition (chapters in source/src_short)
python report/source/build.py                  # full edition (chapters in source/src)
```

Needs python-docx, matplotlib, LibreOffice (`soffice`) and poppler (`pdftotext`). Chapters are a small markdown dialect (`::: fig`,
`::: table`, `::: code`, `::: algo`, `[@key]` citations, `@fig:key` cross-references). References are in `source/refs.py`, numbered by
first citation; code listings are copied from the repository files and line ranges in their captions.
