# Slides — port notes

Standalone source: `apps/slides/frontend/src`. Now at
`apps/suite/frontend/src/apps/slides/`, served under **`/slides`**.
Ported in an earlier session (commit `Phase 5: port Slides frontend …`). See the
parent `../README.md` and `PHASE5-PORT-CONTRACT.md` §5 (slides) for details.

## Routes (relative to `/slides`, names namespaced `slides-*`)
- `''` → `slides-home`
- `presentation/new` → `slides-editor-new`
- `presentation/:presentationId/:slug?` → `slides-editor`
- `presentation/view/...` → redirects to `slides-editor`
- `slideshow/:presentationId/:slug?` → `slides-slideshow`
- `not-permitted` → `slides-not-permitted`

## What changed vs standalone
- `createWebHistory`/standalone router dropped; routes are relative under `/slides`.
  `router.ts` installs a `slides-*`-scoped guard on the shared router (maintains
  `previousRoute`, gates the editor on per-presentation access level).
- frappe-ui `1.0.0-beta.3` → `1.0.0-beta.9`; the big toolchain jump was **Vite 4 → 8**
  (Node baseline, plugin-vue, build target). Module-scoped Pinia stores kept.
- Backend method paths rewritten to `suite.slides.*` — note the standalone
  `slides.slides.doctype.presentation.*` collapsed to **`suite.slides.doctype.presentation.*`**
  (one module level removed); `slides.api.file.*` → `suite.slides.api.file.*`.

## Known / deferred (please review)
- Slides emitted a custom `service-worker.js` (intercepting `/private/files/`) from
  the standalone build; under the suite outDir/base this needs re-checking at runtime.
- CJS deps (`feather-icons`, `lowlight`, `interactjs`, `debug`) — re-validate pre-bundling.

## Verify (Phase 6)
Log in at `suite.localhost:8004/slides`. Confirm: home lists presentations; create a
new presentation; editor (add/edit/move slides, elements, media upload); slideshow
mode; the access-level gate (edit/view/not-permitted) behaves.
