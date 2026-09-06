# Module 10 — Cycle Plan / Timeline Generator

The clinic's existing **Timeline Generator** (`github.com/dr-patsama/timeline-generator`,
OPU / FET / ORA / IUI, protocols: Antagonist · PPOS · Mild · Natural · Luteal stimulation ·
DuoStim) is embedded unchanged as the first piece of the Cycle Plan layer.

| | Before | Now |
|---|---|---|
| Storage | JSON/JPG/PDF files in `~/Documents/เอกสารคนไข้/SAVED TIMELINE` | PostgreSQL `cycle_timelines` (JSONB) + files on `uploads/timelines/<id>/` |
| Patient link | none | auto-linked to EMR patient by HN (`patient_id`), re-linkable later |
| Auth | none (localhost only) | FCMS JWT + RBAC, PDPA audit log |
| Libraries | CDN (needs internet) | vendored under `/timeline/vendor` — works offline on the NAS |
| URL | `http://localhost:8012` | `http://<nas>:8000/timeline` |

## Wire contract (unchanged for the UI)
- `GET  /api/v1/timeline/list[?hn=]` → array of generator documents
- `POST /api/v1/timeline/save` `{type: json|jpg|pdf|delete, filename, content, id}`

## REST for other modules
- `GET /api/v1/timeline/?hn=&patient_id=&cycle_type=&q=`
- `GET /api/v1/timeline/{id}` (full document) · `GET /api/v1/timeline/files/{file_id}`
- `POST /api/v1/timeline/{id}/link-patient`

## Updating the generator
`index.html` is the upstream file with two mechanical edits (vendored `<script src>` and the
FCMS fetch bridge injected before the main `text/babel` block). To pull a new upstream version,
copy `index.html` over and re-apply those two edits — everything else is untouched.

## Next (Cycle Plan v2)
Expand `document.timelineInputs` + rendered visits into `cycles` / `cycle_days` rows so lab
results, TVUS, dispensing, OR bookings and the patient app can attach to a specific cycle day.
