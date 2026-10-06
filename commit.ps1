#!/bin/sh
# Commits all changes (pdf.py + forms.py etc.)

cd c:/Users/PC/academia || exit 1

# Add all changes (including new files and deletes)
git add grades/pdf.py grades/forms.py grades/urls.py grades/views.py \
       templates/grades/releve_notes.html templates/grades/saisie_notes.html

# Check what will be committed
echo "=== Files to commit ==="
git status --porcelain

# Commit with a clear message
git commit -m "Refactor PDF writer (pdf.py) — remove duplicate methods, fix infinite loop in table renderer, verify PDF output

- Remove duplicate _finish_page and _raw methods from pdf.py
- Fix infinite while rows: loop in table() by adding row_pos advancement
- Fix missing .encode('latin-1') on trailer write in render()
- Verify generated PDF has valid header, xref, EOF and object count
- Clean up temporary test/debug files

Co-authored-by: Solar Mini4 <solar-mini4@upstage.ai>" || echo "COMMIT FAILED"
