# Sheets — port notes

Standalone source: `apps/sheets/frontend/src`. Now at
`apps/suite/frontend/src/apps/sheets/`, served under **`/sheets`**.
Ported in an earlier session (commit `Phase 5: port Sheets frontend …`). See the
parent `../README.md` and `PHASE5-PORT-CONTRACT.md` §5 (sheets) for details.

## Routes (relative to `/sheets`, names namespaced `sheets-*`)
The standalone app had **no vue-router** (it toggled Home/editor via
`history.pushState` + a `?id=` query param). That was replaced with real routes:
- `''` → `sheets-home` (listing)
- `:id` → `sheets-editor` (`?id=<name>`; `?id=new` → `/sheets/new`), `props: true`

## What changed vs standalone
- Hand-rolled routing replaced by vue-router under `/sheets`.
- frappe-ui `1.0.0-beta.3` → `1.0.0-beta.9` (incremental). Already on Vite 8 / Vue 3.5.
- The bespoke base/outDir/manifest wiring (`/assets/sheets/sheets/`) was dropped for
  the shared suite base.
- Backend method paths rewritten to `suite.sheets.api.*` and
  `suite.sheets.versioning.api` (note `services/versions.js` builds calls from a
  `PREFIX` constant — now `'suite.sheets.versioning.api'`).

## Known / deferred (please review)
- **`main.js` monkey-patches** frappe-ui defaults (overrides `FormControl` variant
  outline→subtle, mutates reka-ui Tooltip prop defaults / delayDuration). These are
  fragile across beta bumps — re-validate against beta.9.
- **Bespoke fetch wrapper** (`utils/api.js`, reads `window.csrf_token`, parses
  `_server_messages`) still exists and diverges from frappe-ui `createResource`.
  Consider standardizing on frappe-ui resources.
- `echarts ^6` + `vue-echarts ^8` vs frappe-ui's bundled echarts — confirm charts render.
- yjs/`@hocuspocus/provider` collab must share the single deduped yjs instance.

## Verify (Phase 6)
Log in at `suite.localhost:8004/sheets`. Confirm: listing; create/open a sheet
(`/sheets/<id>`, `/sheets/new`); cell editing + ops persist; charts render; version
history; collaboration if testable.
