# Drive — port notes

Standalone source: `apps/drive/frontend/src`. Now at
`apps/suite/frontend/src/apps/drive/`, served under **`/drive`**.
See the parent `../README.md` for suite-wide conventions. This was the largest
frappe-ui migration of the 7 (`0.1.269` → `1.0.0-beta.9`).

## Routes (relative to `/drive`, names namespaced `drive-*`)
Under `views/DriveLayout.vue`: `drive-Home('')`, `drive-Teams`, `drive-Recents`,
`drive-Favourites`, `drive-Shared`, `drive-Inbox`, `drive-Trash`, `drive-Documents`,
`drive-Presentations`, `drive-Attachments`, `drive-Setup`, `drive-Signup`,
`drive-Team(t/:team)`, `drive-Folder(d/:entityName)`, `drive-File(f/:entityName)`,
`g/:entityName`, and `drive-Document(w/:entityName)` which **redirects to `/writer`**,
plus legacy redirects. **`isPublic`** (guest-shared links): `drive-Signup`, `g`,
`drive-Team`, `drive-File`, `drive-Folder`, `drive-Document`, and the redirects.

## What changed vs standalone
- **`socket.js`** reads `window.socketio_port` (was a `common_site_config.json` import).
- `createWebHistory('/drive')` dropped. `router.ts` re-exports the shared router and
  adds a `drive-*`-scoped `beforeEach`/`afterEach` (recent-team, active-entity, current-route).
- **Vuex kept as a module singleton** — all 21 `useStore()` sites now `import store from
  '@/apps/drive/store'`.
- **`app.use(FrappeUI)` dropped** (suite doesn't install the plugin). Drive used **no**
  Options-API `resources: {}` blocks except one dead one, which was removed — so
  `resourcesPlugin` isn't needed. `$call`/`$resources`/`$socket` were not used.
- **The global `setConfig('resourceFetcher', …)` error-suppression override was removed**
  (it would have clobbered every other app's fetcher). See deferred note below.
- `app.config.unwrapInjectedRef = true` deleted (dead under Vue 3.5).
- **`emitter` and `socket`** are provided by `DriveLayout` (`provide(...)`); the global
  `emitter` property is gone. `v-on-outside-click`/`v-focus` directives and
  `Button`/`FormControl` are registered/imported locally.
- **Translation** via the foundation; `routes.ts` populates `window.translatedMessages`
  via `suite.drive.api.product.get_translations`.
- **Deps added:** `@headlessui/vue`, `@headlessui-float/vue`, `dropzone`, `vue-sonner`,
  `sass`, `access-key-label-polyfill`. `@vueuse/core`+`@vueuse/components` pinned `^10.4.1`
  (the `^13.1` components major was dropped); `reka-ui` `^2.6`; `lucide-vue-next` `^1.0`.
  `dropzone` (CJS) built cleanly. No `radix-vue` (already on reka-ui).
- Backend method paths rewritten to `suite.drive.api.*` / `suite.drive.www.*` /
  `suite.drive.utils.*`.

## Known / deferred (please review)
- **Global error-suppression removed:** the standalone re-set the global fetcher to
  swallow errors where `err.messages[0]` existed. Dropped (can't override the shared
  fetcher). Resources that relied on silent swallowing may now surface toasts/console
  errors — most drive resources define their own `onError`; restore per-resource (or a
  drive-local fetch wrapper) if needed.
- **`utils/getIconUrl.js`** returns `/assets/drive/images/icons/*.svg` (a backend
  static path). If the suite backend serves these under `/assets/suite/...`, repoint.

## Verify (Phase 6)
Log in at `suite.localhost:8004/drive`. Confirm: file/folder listing + navigation;
upload (dropzone); create folder/doc; move/rename/share; trash + restore; preview
(PDF/image/video); a guest opening a public share link; the **`File` doctype override**
behaves; `/drive/w/<id>` redirects into Writer.
