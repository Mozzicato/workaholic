# ADR-011 — Templates are chosen first, change only the look, and carry their own fonts

**Status:** Accepted · 2026-09-19

## Context

People expect to choose how a resume looks before anything else — every resume builder opens on
a gallery. Workaholic had three templates hidden in a button row beside "Write my resume". The
references people actually asked for (a Charter-style one-line layout, the Harvard careers-office
format, the r/EngineeringResumes template, teal-accented and bold-header designs, and the
families resume.io offers: classic, ATS-first, two-column, executive, minimal) were not there.

The PDF printer runs in a container with only basic Linux fonts and is forbidden from fetching
anything. A template that names a typeface it does not carry prints in whatever is installed, so
most of these designs could not have been reproduced faithfully by naming fonts.

## Decision

1. **Eleven templates, one structure.** Eight new ones (Classic, Harvard, Engineering, Modern,
   Bold, Sidebar, Executive, Minimal) join Standard, Compact and Academic. All render the same
   document through the same HTML; a template may choose only its stylesheet, section order, one
   of three entry layouts (role-first, organisation-first, one line), one of three headers, a
   side column, contact icons and short month names. It cannot add or drop a fact. They are our
   own designs in the same families as the references, not copies of anyone's artwork.
2. **Typefaces are embedded.** Each template carries its 3–4 font faces inline as data URIs
   (Charis SIL, Tinos, Carlito, Lato, Source Sans 3, Source Serif 4, Inter — all SIL OFL or
   Apache 2.0, licences beside the files). The preview in the browser and the PDF are therefore
   identical, and the printer still fetches nothing. Cost: ~100 KB of HTML per preview; PDFs
   stay 21–33 KB because the printer subsets the fonts.
3. **Chosen first, changeable any time.** "Create" opens the gallery, then asks for a name. A
   resume remembers its template (`resumes.template`). Because a template is presentation only,
   changing it re-renders every existing draft, the PDF and the ATS check at once — no new
   draft, no model call, no lost words.
4. **The gallery shows real output.** Its images are the first page of a real PDF of a clearly
   labelled example person, printed by the same renderer
   (`apps/api/scripts/render_template_previews.py`), so a card cannot promise a look the
   download does not have.
5. **Honest labels.** Each card says what the template suits. The two-column template says
   plainly that some older ATS read columns out of order.

## Consequences

- Every template is held to the same tests: every fact reaches the page, nothing outside the page
  is referenced, the named typeface is embedded, and — the ATS test — the printed PDF's text
  reads back with every key fact. That last test caught a real problem in the Bold design: a
  name capitalised with CSS comes out of the PDF as "ADA LOVELACE", which an ATS would store. The
  name is now heavy instead of capitalised.
- Enum columns were widened to 32 characters so a new template name never needs a data rewrite;
  existing resumes keep the Standard template they were written in.
- Adding a template is a stylesheet, a spec entry and a regenerated image. Section order is
  still per template; letting a person reorder sections is a later change.
- Names with Yoruba or Igbo diacritics (ẹ, ọ, ṣ) are outside the Latin subsets embedded; those
  letters fall back to the system font in the PDF. Worth adding the extended subsets once real
  users show it matters.
