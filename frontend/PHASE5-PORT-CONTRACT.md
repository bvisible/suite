# Phase 5 — Per-App Port Contract

This document is the contract a **per-app port agent** implements against the
unified Frappe Suite SPA skeleton in `apps/suite/frontend/`. The skeleton is the
serial "foundation" barrier; the 7 per-app UI ports (drive, slides, writer,
sheets, meet, mail, calendar) happen **later, in parallel, against this skeleton**.

Do not change shared infra (`vite.config.ts`, `tailwind.config.js`,
`postcss.config.js`, `package.json`, `src/main.ts`, `src/router/index.ts`,
`src/boot/*`, `src/stores/root.ts`, `src/shell/*`, `src/apps/registry.ts`)
unless coordinating a foundation change. Your work is confined to
`src/apps/<app>/`.

---

## 1. Register your route module

Each app owns a URL **prefix** (preserved from the standalone app):

| app | prefix |
|-----------|-------------|
| drive | `/drive` |
| slides | `/slides` |
| writer | `/writer` |
| sheets | `/sheets` |
| meet | `/meet` |
| mail | `/mail` |
| calendar | `/calendar` |

The single suite router (`src/router/index.ts`) lazy-loads
`src/apps/<app>/routes.ts` on first navigation into the prefix and mounts the
exported `routes` array **under** that prefix.

- Export `export const routes: RouteRecordRaw[]` (and a default export).
- Paths are **relative** to the prefix — NO leading slash. The `''` (empty)
  path is the app index.
- Keep views lazy: `component: () => import('@/apps/<app>/views/Foo.vue')` so
  heavy app-only deps stay code-split out of the shared shell bundle.

```ts
// src/apps/drive/routes.ts
import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  { path: '', name: 'drive-home', component: () => import('@/apps/drive/views/Home.vue') },
  { path: 'folder/:id', name: 'drive-folder', component: () => import('@/apps/drive/views/Folder.vue'), props: true },
]
export default routes
```

Name routes with an app prefix (`drive-*`, `mail-*`) to avoid collisions in the
single router. The app registry (`src/apps/registry.ts`) is the source of truth
for prefixes and the launcher tiles — you should not need to edit it.

## 2. Where files go

```
src/apps/<app>/
  routes.ts        # the contract entry point (required)
  views/           # route-level pages (lazy-loaded)
  components/      # app-local components
  composables/     # use* composables
  stores/          # app-local Pinia stores (namespaced: defineStore('<app>-...'))
```

App-local Pinia stores MUST namespace their id, e.g.
`defineStore('drive-files', ...)`, to avoid collisions with the shared
`suite-session` / `suite-root` stores.

## 3. Unified frappe-ui import conventions

- frappe-ui is pinned to **1.0.0-beta.9** (published). Replace every git-commit
  pin and local-source alias with bare `frappe-ui` imports.
- Resources: `import { createResource, createListResource, call } from 'frappe-ui'`.
- Icons: frappe-ui sprite via `frappe-ui/icons` + `unplugin-icons`; standalone
  icons via `lucide-vue-next` (pinned `^0.543.0`). Do not add a second lucide major.
- Tailwind tokens: ONE design-token source (`tailwind.config.js` with the
  `frappe-ui/tailwind` preset). Use the ink/surface/outline tokens, not hex.
- Do NOT register your own Vite/Tailwind/PostCSS config — the suite has one of each.

## 4. API base & session

- `src/main.ts` calls `configureFrappeUI()` once →
  `setConfig('resourceFetcher', frappeRequest)`. All resources hit the Frappe
  site serving the SPA (`suite.localhost`, dev backend on **:8004**) at
  `/api/method/...`. CSRF comes from `window.csrf_token` (injected by the Jinja
  `index.html` / `suite.html`).
- Auth: use the shared `useSessionStore` from `@/boot/session`
  (`isLoggedIn`, `login`, `logout`). The router's `beforeEach` already redirects
  guests to `/login`. Drop per-app session stores / bespoke fetch wrappers
  (e.g. sheets' `utils/api.js`, `window.csrf_token` parsers) in favor of these.
- Assets are served at `/assets/suite/frontend/...`; re-point any hardcoded
  `/assets/<oldapp>/frontend/` URLs, PWA `start_url`, and service-worker scopes.

## 5. Per-app breaking-change risks

These are carried verbatim from the dependency resolution (`_resolved.json`).
Re-verify each during your port.

### drive
- frappe-ui 0.1.269 → 1.0.0-beta.9 is the major API jump: `createResource`/`createListResource`/`call` signatures, `setConfig('resourceFetcher', frappeRequest)`, `resourcesPlugin`/`FrappeUIProvider`, and toast APIs must be re-verified across `store.js`, `main.js` and all resource definitions.
- 0.1.269 depends on radix-vue ^1.5.3 while beta.9 standardizes on reka-ui ^2.5; Drive already pulls reka-ui 2.4 directly, so component import paths/prop APIs must converge on the single reka-ui ^2.6.0 the suite pins (dedupe to one copy or runtime context errors).
- Mixed @vueuse versions (core ^10.3 + components ^13.1) is fragile; beta.9 peers @vueuse/core ^10.4.1, so the suite must dedupe @vueuse/core to ^10.4.1 and drop the ^13.1 components major (or it will load two @vueuse copies).
- TipTap 3.11 + full Yjs/ProseMirror collab stack must be unified to the suite's @tiptap ^3.26 (matching what beta.9 bundles) with resolve.dedupe:['yjs','@tiptap/pm'] to avoid duplicate ProseMirror/Yjs singletons that silently break collaboration.
- Vite/Tailwind already on 8 + v3.4.19 so those upgrades are done; remaining work is folding Drive's frappe-ui/vite plugin options (frappeProxy, lucideIcons, jinjaBootData, buildConfig.indexHtmlPath) and frappe-ui/drive subpath export into the single suite vite config; export-map changes in beta.9 may break vite-helpers.ts local-link aliases.
- lucide-vue-next 0.543 vs frappe-ui beta.9 lucide-static ^1.16 + unplugin-icons — reconcile icon resolution under one auto-import/components.d.ts to avoid name collisions.
- app.config.unwrapInjectedRef = true is a dead Vue 2.7/early-3 compat no-op under Vue 3.5; drop it during consolidation.
- CJS deps (html2pdf.js, dropzone 6 beta) rely on optimizeDeps.include + commonjsOptions interop; verify Rolldown-based Vite 8 pre-bundles them in the merged config.

### slides
- Already on frappe-ui 1.0.0-beta.3; bump to beta.9 is small but spans 6 betas — re-verify createResource/createDocumentResource/call, FrappeUIProvider/resourcesPlugin, setConfig('resourceFetcher') and toast.create signatures used across module-singleton stores and App.vue.
- Vite 4 → 8 is the big jump (skips 5/6/7): requires Node 20.19+/22.12+, @vitejs/plugin-vue ^4 → ^6, and build.target 'es2015'/tsconfig ES6 must be raised to the suite default (esnext/es2022).
- optimizeDeps.include CJS deps (feather-icons, lowlight, interactjs, debug) need re-validation under Vite 8 stricter ESM/CJS pre-bundling.
- Custom service-worker.js emitted to www and registered from site root '/' to intercept /private/files/ — asset hashing/base handling under Vite 8 + new suite outDir/base must be re-checked; service-worker scope assumptions tied to per-app paths.
- CommonJS config bits (tailwindPlugins.js scrollbar plugin via require/module.exports) in a type:module package must be folded into the ONE suite Tailwind config.
- unplugin auto-imports/components and @vitejs/plugin-vue must move in lockstep to the suite-pinned versions; regenerated d.ts files may surface name collisions.
- Strict tsconfig + mixed untyped .js stores may surface stricter type/lint failures after toolchain bump.

### writer
- frappe-ui pinned to a raw git commit (pkg ~0.1.211, lockfile a different commit) → published 1.0.0-beta.9: major jump with renamed/removed exports (FormControl, Button, setConfig, frappeRequest, pageMetaPlugin, useList/useCall/createResource); audit every import in main.ts and resources.
- Stale install: package.json declares Vite ^8 + plugin-vue ^6.0.5 but node_modules still has Vite 4.5.14 / plugin-vue 4.6.2 — a real Vite 8 install is required; outDir computed via path.basename and build.target 'esnext' must be replaced by the suite's static config.
- reka-ui ^2.6.0 + @vueuse/core ^14.0.0 here CONFLICT with beta.9's reka-ui ^2.5 / @vueuse/core ^10.4.1 peers — must downgrade @vueuse/core to ^10.4.1 for the suite (the ^14 major is the sharpest single-dep conflict across all apps) and dedupe reka-ui to one ^2.6.0 copy.
- Heavy CRDT/editor stack (yjs, y-prosemirror, prosemirror-*, tiptap 3) depends on resolve.dedupe + optimizeDeps.include; Vite 8 dep-optimizer changes can reintroduce duplicate yjs/prosemirror and break collaboration — unify @tiptap to ^3.26.
- unplugin-auto-import 0.15.0 / unplugin-vue-components 30.0.0 are too old for Vite 8 — must adopt the suite-pinned unplugin-auto-import ^19.3 / unplugin-vue-components ^32.
- Tailwind stays v3 but config currently scans node_modules/frappe-ui drive paths and has a text-size/leading safelist — fold into the single suite Tailwind config.
- Vuex 4 (src/store.ts) vs suite direction toward Pinia: getters.isLoggedIn guard + cookie-based user must be migrated if the suite shell standardizes on Pinia.
- Leftover Drive coupling: server.allowedHosts hardcodes 'drive.localhost' and main.ts/tailwind import drive-specific resources (@/ui/drive/js/resources, allUsers, drive.api.product.get_translations) — must be de-coupled during consolidation.
- /w/:id route redirect target and createWebHistory('/writer') base must be re-pointed under the suite route namespace.

### sheets
- Already on frappe-ui ^1.0.0-beta.3 and Vite 8 / Vue 3.5; bump to beta.9 is incremental BUT main.js carries fragile monkey-patches (overrides FormControl default variant outline->subtle, mutates reka-ui Tooltip prop defaults / delayDuration) that can break on any further beta prop-shape change — re-validate against beta.9.
- Registers frappe-ui components globally (CommandPalette/Autocomplete/Select/Checkbox/KeyboardShortcut); any rename/removal in beta.9 breaks these imports.
- frappeuiPlugin runs with frappeProxy:false, jinjaBootData:false, buildConfig:false and hand-managed Vite base '/assets/sheets/sheets/' + manifest:true read by sheets/www/sheets.py — the suite must move to the shared base '/assets/suite/frontend/' and a single manifest/indexHtml strategy; the bespoke base/outDir/manifest wiring is the odd-one-out and must be reconciled.
- Both yarn.lock and package-lock.json are committed; suite must drop package-lock.json and standardize on yarn.
- echarts ^6 + vue-echarts ^8 here vs frappe-ui beta.9 bundling echarts ^5.6 — version-range conflict; suite pins echarts ^6 and must dedupe so frappe-ui's charts and Sheets charts share one echarts major (verify frappe-ui charts render on echarts 6, else alias).
- No vue-router (hand-rolled history.pushState + ?id=); if the suite shell mandates vue-router with a shared base, Sheets routing must be rewritten.
- Bespoke fetch wrapper (utils/api.js, window.csrf_token, _server_messages parsing) diverges from frappe-ui createResource; suite-wide standardization on frappe-ui resources would require reworking services and use* composables.
- @hocuspocus/provider ^4.1 + yjs ^13.6 collab must dedupe yjs with the Writer/Drive Yjs stack to a single instance.

### meet
- frappe-ui 0.1.271 → 1.0.0-beta.9 is a major API rewrite: createResource/createListResource signatures, setConfig('resourceFetcher'), resourcesPlugin/pageMetaPlugin registration, and global component imports (Button, Dialog, FormControl) may be renamed/removed.
- frappe-ui/vite plugin frontendRoute / __FRONTEND_ROUTE__ injection drives the router base ('${__FRONTEND_ROUTE__}/'); beta.9 plugin option restructuring could change/remove this define, breaking the dynamic base — the suite must set a stable route base instead.
- Vite already 8.0.2 + plugin-vue 6.x and Vue 3.5.16, so those targets are met; but build.target 'es2015' must be raised, and the custom noiseSuppressionAudioWorkletVitePlugin + frappeui plugin must be confirmed Vite 8/Rolldown compatible in the merged config.
- Pinia 3.0.4 here matches the suite Pinia pin — Meet/Mail/Calendar share Pinia, reinforcing Pinia as the suite store; Drive/Writer Vuex stores are the divergent ones to migrate.
- index.html references /src/main.js while the real entry is src/main.ts (relies on frappe-ui/vite rewrite); a plugin change in beta.9 could break entry resolution — make the suite entry explicit.
- Direct import of socketio_port from sites/common_site_config.json (outside frontend root) depends on server.fs.allow; stricter Vite 8 fs defaults could block it — add to the suite fs.allow.
- Bleeding-edge typecheck (@typescript/native-preview tsgo + vue-tsgo on TS 6 preview) should be realigned to the suite's vue-tsc ^3.2 / typescript ^5.9.
- reka-ui 2.6 must dedupe with frappe-ui beta.9's reka-ui ^2.5 to one copy.
- mediasoup-client / @mediapipe / noise-suppression worklet are Meet-only heavy deps — keep code-split/lazy so they don't bloat the shared suite bundle.

### mail
- Package manager is bun (Mail + Calendar) vs yarn (other 5) — biggest tooling decision: suite standardizes on yarn, so Mail's bun.lockb must be dropped and re-resolved under yarn; verify no bun-specific scripts/resolutions.
- frappe-ui pinned to git commit #21e0818 (pkg 0.1.278) → published 1.0.0-beta.9: FrappeUIProvider, spritePlugin, frappe-ui/icons, frappe-ui/vite, frappe-ui/tailwind import paths and createResource cache API may shift; vite.config.ts plugin options (frappeProxy, lucideIcons, jinjaBootData, frappeTypes, buildConfig) likely need rewrite.
- Vite 5.4.21 → 8 jump: Node baseline rises and @vitejs/plugin-vue is pinned ancient ^2.0.0 — must bump to ^6; propsDestructure:true is a transitional SFC option whose default may change under newer plugin-vue.
- vite-plugin-pwa ^1.0.1 injectManifest + custom sw.ts and Firebase ^12 FCM service worker registered at /assets/mail/frontend/sw.js — fragile across Vite majors; under the suite the SW asset path moves to /assets/suite/frontend/ and must be re-validated, and PWA scope/start_url ('/mail') re-pointed.
- @vueuse/core ^10.4.1 here matches beta.9 peer — good; but must dedupe against Writer's ^14 and Drive's mixed versions to the single ^10.4.1 the suite pins.
- Tailwind v3.4.18 fine for beta.9 (still ships v3 plugins); fold into the one suite Tailwind config.
- Hardcoded build outputs (../mail/public/frontend, ../mail/www/mail.html) and /mail route base + /assets/mail/frontend/ URLs must be re-pointed to the suite namespace.
- prosemirror-state/view are deduped for frappe-ui tiptap — extend the suite dedupe list to cover Mail's editor.

### calendar
- Package manager is bun → must move to suite yarn (drop bun.lockb, re-resolve).
- frappe-ui pinned to git commit #3ba6ef5 (NOT a published semver) → 1.0.0-beta.9: exports/API (FrappeUIProvider, createResource, setConfig, frappeRequest, pageMetaPlugin) and frappe-ui/vite + frappe-ui/tailwind subpath contracts may change.
- vite.config.ts aliases frappe-ui to a sibling source path ../frappe-ui/src/index.ts when present (monorepo local link) — consolidating into the single suite app must REPLACE this alias with the pinned npm 1.0.0-beta.9, or builds resolve to a stale github tarball/source.
- Vite already 8.0.3 + plugin-vue ^6.0.5 + Vue 3.5.31 — targets met; but the frappeui() buildConfig API (outDir/baseUrl/indexHtmlPath/jinjaBootData/frappeProxy/frappeTypes) is frappe-ui-version-specific and differs in beta.9; unplugin-* (3.x/19.x/22.x) must align to the suite pins.
- Heavy cross-app coupling to 'mail': calls mail.api.* (get_user_info, get_branding), redirects to /mail/login and /app/login?redirect-to=/calendar, localStorage key 'mail-account-id' — consolidating must reconcile these mail-namespaced endpoints/routes/keys within the suite.
- frappeTypes plugin generates types from mail doctypes (identity, user_account) at build time and needs a reachable Frappe bench — decide whether the suite keeps build-time type generation.
- Router base '/calendar' and /assets/calendar_app/frontend/ output paths are app-name specific; merging into suite changes route prefix and asset URLs.
- lucide-vue-next ^1.0.0 here vs Drive/Slides on lucide-vue-next 0.5x — major version split; pick one lucide-vue-next for the suite (and reconcile with frappe-ui beta.9 lucide-static ^1.16 + unplugin-icons).
- frappe-ui github pin pulls radix-vue 1.x AND reka-ui 2.x transitively plus echarts 5 / @vueuse 10 — must collapse to the single reka-ui ^2.6 / echarts ^6 / @vueuse ^10.4.1 the suite pins.
- vue-router runtime is ^4.1.6 (frappe-ui peer) while lockfile shows 5.0.4 from the unplugin file-based-router package — ensure the suite uses runtime vue-router 4, not the unplugin one.

---

## 6. Acceptance checklist per port

- [ ] `src/apps/<app>/routes.ts` exports `routes` (relative paths, lazy components).
- [ ] All views/components/composables/stores live under `src/apps/<app>/`.
- [ ] No new top-level config; uses the shared vite/tailwind/postcss/tsconfig.
- [ ] frappe-ui imported bare (no git pin / local alias); resources via `createResource`/`call`.
- [ ] Session via `@/boot/session`; no per-app CSRF/fetch wrappers.
- [ ] Heavy deps lazy/code-split; no duplicate vue/vue-router/yjs/@tiptap/pm/reka-ui/@vueuse copies.
- [ ] App store ids namespaced `<app>-*`; route names namespaced `<app>-*`.
- [ ] Old asset/route/SW paths re-pointed to `/assets/suite/frontend/` and the app prefix.
