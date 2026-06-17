# Writer — port notes

Standalone source: `apps/writer/frontend/src`. Now at
`apps/suite/frontend/src/apps/writer/`, served under **`/writer`**.
See the parent `../README.md` for suite-wide conventions.

## Routes (relative to `/writer`, names namespaced `writer-*`)
Under `views/WriterLayout.vue`:
- `''` → `writer-home` (Documents list; auth-gated)
- `w/:id/:slug?` → `writer-document`, `props: true`, **`meta: { isPublic: true }`**
  (guest-reachable shared docs).
The standalone `/login` redirect route was dropped (suite gate handles auth).

## What changed vs standalone
- **No auto-import in the suite.** Writer's standalone vite used
  `unplugin-auto-import({ imports: ['vue','vue-router'] })`, so its files used
  `ref`/`computed`/`useRoute`/etc. without imports. Explicit `import` statements were
  added where needed, plus explicit `~icons/lucide/*` imports (the suite has no
  component auto-resolver). `unplugin-auto-import`/`unplugin-vue-components`/
  `tailwindcss` were intentionally **not** added as deps (the suite owns its toolchain).
- **Vuex kept as a module singleton** (`store.js`, `export default createStore`).
  The suite can't `app.use(store)` in `main.ts`, so consumers `import store from
  '@/apps/writer/store'` directly (the `useStore()` sugar was replaced). The store
  is fully functional standalone.
- `createWebHistory('/writer')` dropped. `router.ts` re-exports the shared suite router.
- **`$user`** (a global lookup fn) → `composables/useUsers().getUser`. The
  `v-focus` / `v-on-outside-click` directives and `Button`/`FormControl` are now
  imported/registered locally per component.
- **Translation** via the foundation; `routes.ts` populates `window.translatedMessages`
  via `suite.drive.api.product.get_translations`.
- **Drive coupling:** Writer vendors some Drive resources under `ui/drive/` — kept
  in-tree; their backend paths were rewritten to `suite.drive.*`.
- frappe-ui git-pin → `1.0.0-beta.9`; `@vueuse/core` pinned `^10.4.1` (writer wanted
  `^14` — use the v10 API). Heavy tiptap/yjs/docx/html2pdf stack kept lazy (Document
  view chunk ~740 kB — expected).
- Backend method paths rewritten to `suite.writer.api.*` (+ vendored `suite.drive.*`).

## Known / deferred (please review)
- Vendored breadcrumb helpers in `utils/` still compare against Drive route names
  (`'Folder'`, `'Team'`) that aren't suite routes — harmless string compares, left
  untouched rather than invent cross-app behavior. Revisit when wiring Writer↔Drive.

## Verify (Phase 6)
Log in at `suite.localhost:8004/writer`. Confirm: Documents list; open/create a doc
(`/writer/w/<id>`); editing + autosave; collaboration (yjs) if testable; comments;
export (PDF/docx); a guest opening a shared-doc link.
