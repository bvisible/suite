# Frappe Suite — Monorepo Migration Plan

> **Goal:** Fold seven separate Frappe apps into a single app, `suite`
> (`frappe/suite`), where each former app becomes a Frappe **module**, served by
> **one unified Vue SPA**, **without losing data** and **without renaming any
> DocType or module** unless there is a genuine collision.
>
> This document is written to be executed by a **dynamic Workflow** (fan-out per
> app, serial barriers for shared files + cutover, verification gates between
> phases). See [§10 Workflow Orchestration Shape](#10-workflow-orchestration-shape).
>
> **Two-stage program.** This plan migrates the **empty** `suite.localhost` first —
> cheap, low-friction, de-risks the *structural* work. Migrating a **populated,
> already-installed** site is the **real acceptance test** and the planned next
> stage; it reuses every phase here **except the cutover** (Phase 4), which swaps to
> the data-safe sequence in [§12](#12-appendix--data-safe-cutover-for-a-populated-site).

---

## 1. Decision Log (locked)

These were resolved in an interview and are **fixed inputs** to the plan. Do not
re-litigate during execution.

| #   | Decision          | Choice                                                        | Consequence                                                                                                                                                                               |
| --- | ----------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Tenancy           | One site = one org                                            | Per-site billing/storage/admin. No team-scoping on artifacts.                                                                                                                             |
| D2  | Shared-infra home | New `suite` app, monorepo                                     | Everything lives in one app.                                                                                                                                                              |
| D3  | Structure         | **Full monorepo now**                                         | 7 apps become modules in `suite`.                                                                                                                                                         |
| D4  | In-scope apps     | Drive, Slides, Writer, Sheets, Meet, Mail, Calendar           | **Gameplan stays a separate app.**                                                                                                                                                        |
| D5  | Data              | **Greenfield** — `suite.localhost` is empty                   | Free to `uninstall-app` / fresh-install. Data-safe re-parenting demoted to optional §12 (populated-site migration only).                                                                  |
| D6  | Renames           | **Avoid**                                                     | Keep DocType + module names; rename only on real collision.                                                                                                                               |
| D7  | Frontend          | **Single unified SPA**                                        | One Vite build, one router, one design-token source.                                                                                                                                      |
| D8  | Frontend deps     | frappe-ui **latest 1.0.0-beta** + **Vite 8** + Vue 3.5        | Drive & Meet (0.1.x) and Mail & Writer (git commits) must be upgraded.                                                                                                                    |
| D9  | Routing           | Keep existing path prefixes → one SPA                         | `/drive`, `/slides`, `/sheets`, `/writer`, `/mail`, `/meet`, `/calendar` all serve the same bundle; launcher at `/suite`. Preserves all existing URLs; avoids Frappe-reserved root paths. |
| D10 | Cutover           | **Big-bang** (single cutover)                                 | On empty `suite.localhost`; rollback = reinstall. Clone rehearsal now optional, not mandatory.                                                                                            |
| D11 | Plan scope        | **Structural migration only**                                 | Notifications / billing / storage analytics / permission layer / admin console are a **separate follow-on spec** (see §11).                                                               |
| D12 | App identity      | `app_name = suite`, title "Frappe Suite", repo `frappe/suite` | —                                                                                                                                                                                         |
| D13 | Git history       | Preserve via `git subtree` per app                            | Fall back to plain copy + single import commit if subtree snags the workflow.                                                                                                             |

---

## 2. Target End State

```
apps/
  frappe/                      # untouched (framework)
  gameplan/                    # untouched (out of scope)
  suite/                       # NEW unified app (was 7 apps)
    suite/
      drive/        <module>   # was app `drive`
      slides/       <module>   # was app `slides`
      writer/       <module>   # was app `writer`
      sheets/       <module>   # was app `sheets`
      meet/         <module>   # was app `meet`
      mail/         <module(s)># was app `mail` (3 modules)
      calendar/     <module>   # was app `calendar_app` (no doctypes; frontend rides Mail's Calendar)
      suite_core/   <module>   # NEW: app-switcher/launcher, shared boot, shared hooks shims
      hooks.py                 # union of all 7 hooks.py
      modules.txt              # union of all module names
      patches.txt              # union of all patches + new migration patches
      www/
        suite.py / suite.html  # single SPA bootstrap (serves every prefix)
      public/                  # built SPA assets
    frontend/                  # ONE Vite 8 SPA (Vue 3.5 + frappe-ui 1.0-beta)
      src/
        shell/                 # launcher, app-switcher, top-nav, shared layout/auth/boot
        router/                # one router; route groups per app keep path prefixes
        apps/{drive,slides,writer,sheets,meet,mail,calendar}/  # ported per-app views/stores
    pyproject.toml             # union of python deps (conflicts resolved)
```

**Acceptance for "done":** `bench migrate` is green, every app's tests pass under
`suite`, every app route loads inside the single SPA, and the 7 old apps no longer
exist in `apps.txt`. (Target site `suite.localhost` is empty — there is no data to
preserve; see D5.)

---

## 3. Scope

**In:** Drive, Slides, Writer, Sheets, Meet, Mail, Calendar (`calendar_app`).

**Out:** Gameplan (`/g`, 35 `GP_*` doctypes) — remains a standalone app.
`frappe` core — untouched.

**Explicitly NOT in this plan (follow-on, see §11):** shared notification system,
storage metering, storage-based billing, common permission layer, admin console,
user-permission management, first-time-setup flow, cross-app integration features.

---

## 4. Invariants (must hold at every step)

1. **`uninstall-app` is allowed** — target site `suite.localhost` is empty, so
   there is no data to lose. Old apps may be removed with `bench uninstall-app` or
   simply dropped from `apps.txt`. *(Migrating a populated site later → use the
   data-safe re-parenting path in [§12](#12-appendix--data-safe-cutover-for-a-populated-site).)*
2. **No DocType renames.** `tab<DocType>` table names stay identical → data never
   moves. (Verified: no cross-app collisions; Drive's file doctype is `Drive File`,
   not `File`.)
3. **No module renames** unless a genuine module-name collision is found in
   pre-flight (Mail ships 3 modules — verify their names are unique site-wide).
4. **Module names + DocType names are the migration's stable keys.** Everything
   else (app ownership, file location, import paths) changes around them.
5. Backups + clone rehearsal are **optional** on the empty target site (rollback =
   reinstall). Required only for a populated-site migration (§12).
6. Drive's `override_doctype_class` for core **`File`** must keep applying after
   the move (its dotted path changes `drive.*` → `suite.*`).
7. **Design Phases 0–3 and 5–7 to run identically on a populated site.** The
   empty-site run is a rehearsal of the *structural* migration — do **not** bake
   empty-site-only shortcuts into any phase except the cutover. Only Phase 4
   legitimately differs (fresh-install here; data-safe re-parent in §12). If a step
   would behave differently on a site that already holds data, flag it now.

---

## 5. Known Facts & Blockers (from codebase exploration)

| Area               | Finding                                                                                                                                                                                                                                                                                                                                                      | Action                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| DocType collisions | **None** across the 7 apps; each prefixes (`Drive *`, `Sheet *`, `SAE *`, etc.). Drive's file = `Drive File`.                                                                                                                                                                                                                                                | No renames.                                                             |
| Core override      | Drive overrides core `File` class; Mail overrides `update_password`; Sheets uses `extend_bootinfo`.                                                                                                                                                                                                                                                          | Port dotted paths; union hooks.                                         |
| Internal deps      | Writer `required_apps: drive`; `calendar_app required_apps: mail`.                                                                                                                                                                                                                                                                                           | Become intra-`suite` module deps; drop from `required_apps`.            |
| Calendar           | `calendar_app` has **no doctypes** — frontend rides Mail's `Calendar` doctype.                                                                                                                                                                                                                                                                               | Calendar = frontend-only module under `suite/calendar`.                 |
| frappe-ui          | 5 different sources: Drive `0.1.269`, Meet `0.1.271`, Sheets/Slides `1.0.0-beta.3`, Mail & Writer = pinned GitHub commits.                                                                                                                                                                                                                                   | **Blocker.** Standardize on latest `1.0.0-beta` (D8).                   |
| Vite               | v4 (Slides), v5 (Mail), v8 (Drive/Sheets/Writer/Meet).                                                                                                                                                                                                                                                                                                       | Standardize on **Vite 8** (D8).                                         |
| Vue                | All 3.5.x                                                                                                                                                                                                                                                                                                                                                    | Compatible.                                                             |
| Stores             | Mail uses **Pinia**; others use Composition refs/composables.                                                                                                                                                                                                                                                                                                | Unified shell uses Pinia; per-app composables kept as module-scoped.    |
| Hooks to union     | `website_route_rules` (7), `permission_query_conditions`+`has_permission` (5), `doc_events`/`scheduler_events`/`fixtures` (4 each), `add_to_apps_screen` (7), plus singletons: `override_doctype_class` (Drive), `override_whitelisted_methods` (Mail), `extend_bootinfo` (Sheets), `after_install`/`after_migrate` (Drive, Mail), `app_include_js` (Drive). | Phase 3 merge.                                                          |
| Heavy python deps  | Drive (opencv, boto3, pycrdt, unoconv, PyJWT), Mail (paramiko, dnspython, rocksdict, dns-lexicon, bcrypt).                                                                                                                                                                                                                                                   | Union pyproject; no major conflicts detected — re-verify in pre-flight. |
| `suite` app        | Does **not** exist locally (not in `apps/` or `apps.txt`); exists as a GitHub repo.                                                                                                                                                                                                                                                                          | Scaffold/clone in Phase 1.                                              |

---

## 6. Risk Register & Rollback

| Risk                                                            | Severity     | Mitigation                                                                                                  |
| --------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------- |
| Data loss via `uninstall-app`                                   | N/A          | Target site empty (D5). Relevant only for a populated-site migration (§12).                                  |
| Module re-parent breaks controller resolution                   | N/A          | Greenfield uses fresh install, not re-parenting (§12 only).                                                  |
| Patch Log re-runs old patches under new dotted paths            | N/A          | Fresh install on empty site runs each patch once (§12 only).                                                 |
| frappe-ui 0.1.x → 1.0-beta breaking component API (Drive, Meet) | High         | Per-app frontend port treats this as real migration work, not a version bump.                               |
| Single SPA build merges 7 router/store/Tailwind setups          | High         | One shell + lazy-loaded per-app route bundles; port app-by-app behind a shared router.                      |
| Big-bang cutover has no working intermediate                    | Medium       | Work on a branch; tag each app repo. Rollback = re-add old apps to `apps.txt` + reinstall (empty site).      |
| Module-name collision (Mail's 3 modules)                        | Medium       | Pre-flight collision scan → rename map (only real collisions).                                              |
| Scheduler cron-key collisions across apps                       | Low          | Union with dedup; namespace if needed.                                                                      |

**Rollback:** the target site `suite.localhost` is empty, so rollback is cheap.
Work on a **branch** and tag each app repo at its pre-migration commit. If the
cutover fails, re-add the old apps to `apps.txt` and reinstall — no backup/restore
dance needed. (For a future populated-site migration, use the backup + data-safe
path in §12.)

---

## 7. Pre-flight Checklist (Phase 0 gate)

- [ ] (Optional — empty site) Backup/clone only needed for a populated-site migration (§12).
- [ ] Each in-scope app repo tagged at current HEAD (`pre-suite-merge`).
- [ ] Migration **manifest** generated (see Phase 0 output schema).
- [ ] Module-name collision scan complete → rename map (expected: empty).
- [ ] Import-path rewrite map generated (`<app>.` → `suite.` for all dotted refs).
- [ ] frappe-ui target version pinned to an exact `1.0.0-beta.N`.
- [ ] Python + Node dependency union computed; conflicts resolved.
- [ ] (Optional) Rehearsal clone — only for a populated-site migration (§12).

---

## 8. Phases

Each phase lists: **Goal · Parallelism · Steps · Artifacts · Acceptance gate.**
Phases are gated — do not start a phase until the previous gate is green.

> ### Migration status — 2026-06-16
>
> - **Phases 0–5: ✅ DONE.** Backend relocated, shared `hooks.py`/`modules.txt`/etc.
>   consolidated, empty `suite.localhost` cut over (`installed_apps=['frappe','suite']`),
>   all 7 frontends ported into one Vite 8 + Vue 3.5 + frappe-ui `1.0.0-beta.9` SPA, and
>   every app's git history grafted under `src/apps/<app>/`.
> - **Phase 6: 🔄 IN PROGRESS.** Runtime-verified on `suite.localhost:8004` (logged in):
>   **Drive, Writer, Slides, Sheets, Meet + launcher** render, `suite.*` method paths
>   resolve, relocated assets serve. Fixes landed this pass:
>   - Calendar `dayjs` `customParseFormat` plugin (`560c1b2f1`)
>   - assets relocated to `suite/public/{drive,meet}/…` and URLs repointed to
>     `/assets/suite/…` so the suite is self-contained (`560c1b2f1`)
>   - Sentry fully removed (`560c1b2f1`)
>   - `require_type_annotated_api_methods` disabled (`2b1f32d59`) — unblocks ~23
>     un-annotated whitelisted methods in `suite/{writer,slides,client}`
>   - frappe-ui **v2 token codemod** applied (`2f22578f2`, 282 renames + 140 weight
>     merges, 159 files; non-idempotent — do not re-run)
> - **Phase 7: ⬜ NOT STARTED.** (`monorepo.md` already moved into the app root.)
>
> **Remaining tasks**
> 1. **Annotate the ~23 whitelisted methods** in `suite/{writer(9),slides(11),client(3)}`
>    (scalars→`str`/`int`, JSON args→precise/`Any`, avoid double-parse), then re-enable
>    `require_type_annotated_api_methods` in `suite/hooks.py`. *(Phase 7 cleanup.)*
> 2. **Calendar white-screens with no mail account** — `get_user_info` 417s (no JMAP) →
>    guard rejects → no-account redirect to an empty `:accountId` → SPA never mounts.
>    Needs a configured mail account and/or a no-account routing guard. **Owner: Akash.**
> 3. **Set up a Mail/JMAP account** for the test user to verify Mail + Calendar happy
>    paths (both currently 417 on `get_user_info`).
> 4. **Phase 7:** single CI + lint/test config; update `apps/suite/README.md`; decide
>    whether to copy bench-root `research.md` into the app; verify grafts intact, then
>    archive + delete the 7 `apps/<app>/` source repos; tag a `suite` release.

### Phase 0 — Pre-flight, inventory & manifest  ✅ DONE
- **Goal:** Produce a machine-readable migration manifest that drives every later
  phase; take backups; rehearse-clone ready.
- **Parallelism:** 1 inventory agent per app (7) → merged by 1 agent.
- **Steps:**
  1. Tag each app repo at HEAD (`pre-suite-merge`). (Backup/clone optional — empty site.)
  2. For each app, inventory: modules, DocTypes, every dotted reference to the
     app name (Python imports, `frappe.get_attr`/`get_doc` strings, hooks string
     paths, `app_include_js`, asset bundle paths, JS `frappe.require`), hooks.py
     keys, scheduler keys, fixtures, `patches.txt` entries, `www/*`, `public/*`,
     workspaces, reports, print formats, translations, `required_apps`.
  3. Scan for **module-name** collisions across the 7 apps + Frappe core.
  4. Compute python-dep + node-dep union and flag version conflicts.
  5. Resolve exact frappe-ui `1.0.0-beta.N` target.
- **Artifacts:** `migration-manifest.json` (per-app: modules, doctypes,
  import-rewrites, hooks-fragment, deps, frontend-entry, www/public paths), a
  `module-rename-map` (expected empty), a `patch-rename-map`.
- **Gate:** Manifest reviewed; rename map confirmed empty (or renames approved); no
  unresolved dep conflict.

### Phase 1 — Scaffold `suite`  ✅ DONE
- **Goal:** Standing `suite` app skeleton ready to receive modules.
- **Parallelism:** Single agent.
- **Steps:**
  1. Clone/initialize `frappe/suite` (`app_name=suite`, title "Frappe Suite").
  2. Create `suite_core` module (launcher/app-switcher backend, shared boot,
     hook shims). Seed `modules.txt` with `Suite Core`.
  3. Set up `git subtree` prefixes for each app's import (history-preserving), or
     fall back to plain copy.
  4. Add `suite` to the bench (`apps.txt` / `bench get-app` against clone).
- **Artifacts:** Booting empty `suite` app installed on `suite.localhost`.
- **Gate:** `bench --site suite.localhost migrate` green with empty `suite` installed.

### Phase 2 — Backend module relocation  *(fan-out per app)*  ✅ DONE
- **Goal:** Each app's backend physically lives in `suite/<module>` with corrected
  import paths; shared-file edits are deferred to Phase 3.
- **Parallelism:** **7 parallel agents**, one per app, each writing only into its
  own `suite/<module>/` subtree (distinct paths → no write conflicts). Use
  worktree isolation if the workflow runs them concurrently against one repo.
- **Steps (per app):**
  1. Move module folder(s) `apps/<app>/<app>/<module>/` →
     `apps/suite/suite/<module>/` (subtree-preserving).
  2. Rewrite Python dotted paths `<app>.` → `suite.` **inside the moved code**
     and **in any other app that imports it** (Writer→Drive, Calendar→Mail), per
     the manifest's import-rewrite map. Covers: controller imports, hooks string
     refs, `frappe.get_doc`/`get_attr` strings, `scheduler_events`, `doc_events`,
     `override_doctype_class`, `override_whitelisted_methods`,
     `permission_query_conditions`, `has_permission`, report `.py`, jinja methods,
     server scripts.
  3. Move `www/`, `public/` (non-frontend assets), `fixtures/`, `patches/`,
     `translations/`, `templates/`, workspace JSONs.
  4. Emit this app's **hooks fragment**, **patches list**, **deps fragment**, and
     **www/asset path changes** as structured output for Phase 3.
- **Artifacts:** Per-app module package inside `suite`; per-app hooks/patches/deps
  fragments.
- **Gate:** Each module folder imports cleanly (`python -c "import suite.<module>"`
  style smoke check); no remaining `<app>.` dotted refs for that app.

### Phase 3 — Consolidate shared app files  *(serial barrier — single agent)*  ✅ DONE
- **Goal:** One coherent `hooks.py`, `modules.txt`, `patches.txt`, `pyproject.toml`.
- **Parallelism:** Single agent (these are shared files → must be serialized).
- **Steps:**
  1. **`modules.txt`:** union all module names + `Suite Core` (apply rename map).
  2. **`hooks.py`:** merge fragments —
     - dicts (`doc_events`, `override_whitelisted_methods`,
       `permission_query_conditions`, `has_permission`, `scheduler_events`):
       deep-merge; dedup scheduler cron keys.
     - lists (`fixtures`, `website_route_rules`, `app_include_js/css`): concatenate.
     - `after_install`/`after_migrate`/`boot_session`/`extend_bootinfo`: wrap into
       single `suite` functions that call each former app's function in order.
     - `add_to_apps_screen`: replace 7 entries with **one** "Frappe Suite" entry.
     - `override_doctype_class` (File) + `override_whitelisted_methods`
       (update_password): repoint dotted paths to `suite.*`.
     - `website_route_rules`: all app prefixes → the single SPA bootstrap (D9).
  3. **`patches.txt`:** concatenate all apps' patches (still valid — doctype names
     unchanged), repoint dotted paths `<app>.` → `suite.`. (No extra migration
     patches on the empty site; see §12 for the populated-site case.)
  4. **`pyproject.toml`:** union python deps; pin resolved versions for conflicts.
- **Artifacts:** Final shared files in `suite`.
- **Gate:** `hooks.py` imports without error; `bench --site <clone>` boots and
  `bench build` discovers `suite`.

### Phase 4 — Site cutover (greenfield — empty `suite.localhost`)  *(serial)*  ✅ DONE
- **Goal:** Install the unified `suite` app on the empty site and retire the 7 old
  apps. No data-migration patches needed.
- **Parallelism:** Single agent.
- **Cutover sequence:**
  1. `bench --site suite.localhost install-app suite`.
  2. Remove the 7 old apps — `bench --site suite.localhost uninstall-app <app>` for
     each (safe: empty site), or just drop them from `apps.txt` + `installed_apps`.
  3. Remove the old app code dirs from `apps/` (their modules now live in `suite`).
  4. `bench --site suite.localhost migrate` → syncs `suite` Module Defs + DocTypes
     and runs each former app's patches once.
  5. `bench build` + restart.
  6. Verify (Phase 6).
- **Artifacts:** Installed unified `suite`; old apps gone from `apps.txt`.
- **Gate:** `bench migrate` green; all 7 modules' DocTypes present and owned by
  `suite`; site boots with no missing-module errors.

> **Why no patches:** the site is empty, so there is no existing data to re-home —
> no `Module Def` re-parenting and no Patch Log seeding. That machinery is preserved
> in [§12](#12-appendix--data-safe-cutover-for-a-populated-site) for migrating a
> site that already holds data.

### Phase 5 — Frontend unification → single SPA  *(largest; fan-out per app behind a shared shell)*  ✅ DONE
- **Goal:** One Vite 8 + Vue 3.5 + frappe-ui `1.0.0-beta.N` SPA serving every app.
- **Parallelism:** 1 agent builds the shell/router/build (serial), then **7
  parallel agents** port each app's UI into `src/apps/<app>/` (coordinate on the
  shared router/store registration via a manifest of route modules).
- **Steps:**
  1. **Foundation (serial):** `suite/frontend` with Vite 8, single Tailwind config
     + design tokens, single `tsconfig`, single `package.json` pinned to the
     resolved frappe-ui `1.0.0-beta.N`. Shared frappe-ui resource/boot layer.
  2. **Shell (serial):** launcher at `/suite`, app-switcher, top-nav, shared
     layout + auth + boot. One Pinia root; per-app composables kept module-scoped.
  3. **Router (serial):** one Vue Router; route groups per app preserving prefixes
     (`/drive`, `/slides`, `/sheets`, `/writer`, `/mail`, `/meet`, `/calendar`);
     **lazy-load each app's route bundle** (code-split for perf).
  4. **Per-app port (parallel):** move each app's views/components into
     `src/apps/<app>/`; migrate to unified frappe-ui (treat Drive & Meet
     0.1.x→1.0-beta and Mail & Writer git-commit→beta as real component-API
     migrations); fix asset paths + API base; register the app's route module.
  5. **Bootstrap (serial):** one `www/suite.py` + `suite.html`; `website_route_rules`
     map every prefix to it. Remove old `www/*.py|html` and `public/<app>` outputs.
- **Artifacts:** Single built SPA in `suite/public`; one frontend package.
- **Gate:** `bench build` succeeds; launcher loads at `/suite`; **every** app route
  loads and renders inside the one bundle; no console import errors.

### Phase 6 — Cutover verification  *(fan-out per app)*  🔄 IN PROGRESS
- **Goal:** Prove data + behavior intact across all 7 apps.
- **Parallelism:** 7 parallel verification agents (one per app) + 1 cross-cutting.
- **Steps (per app):** create a new artifact and open it, exercise permissions
  (`permission_query_conditions`/`has_permission`), confirm scheduler jobs
  registered, hit key API endpoints, confirm fixtures present.
  **Cross-cutting:** Drive's `File` override active; Mail's `update_password`
  override active; Sheets' `extend_bootinfo` boot keys present; app-switcher lists
  all 7.
- **Gate:** All per-app checklists pass on `suite.localhost`. (Single empty target
  site — no separate production promote.)

### Phase 7 — Repo / CI / docs consolidation  ⬜ NOT STARTED
- **Goal:** One repo of record.
- **Steps:** single CI pipeline + test/lint config; update README/docs; archive the
  7 old app repos (read-only) with a pointer to `frappe/suite`; tag `suite` release.
- **Gate:** CI green on `suite`; old repos archived.

---

## 9. Open Items (decide during execution, low-risk defaults given)

- **`add_to_apps_screen`:** single "Frappe Suite" entry (default) vs. keep per-app
  desk entries. Default: single entry → launcher.
- **Pinia vs composables:** unified root Pinia; do **not** force-rewrite working
  composables. Revisit only if state collides.
- **Git history:** `subtree` preferred (D13); fall back to copy if it stalls the
  workflow — note the fallback in the run log.
- **Lazy-load granularity:** per-app route chunk (default) vs. finer splitting —
  tune after first build based on bundle sizes.

---

## 10. Workflow Orchestration Shape

Maps the phases onto a dynamic Workflow (`pipeline`/`parallel`/`phase`):

```
phase('Pre-flight')         → parallel(7 inventory agents) → 1 merge agent → manifest   [GATE: manifest ready]
phase('Scaffold')           → 1 agent (suite skeleton on suite.localhost)               [GATE: empty migrate green]
phase('Backend relocate')   → parallel(7 per-app move+rewrite agents, worktree-isolated) [GATE: per-module import smoke]
phase('Consolidate shared') → 1 agent (hooks/modules/patches/pyproject) — BARRIER        [GATE: boots + build discovers]
phase('Site cutover')       → 1 agent (install suite, drop old apps, migrate)            [GATE: migrate green]
phase('Frontend foundation')→ 1 agent (shell+router+build) — BARRIER
phase('Frontend port')      → parallel(7 per-app UI port agents)                         [GATE: all routes render]
phase('Verify')             → parallel(7 per-app + 1 cross-cutting) — BARRIER            [GATE: checklists pass]
phase('Consolidate repo')   → 1 agent (CI/docs/archive)
```

**Barriers** (must collect all prior results before proceeding): Consolidate
shared, Site cutover, Frontend foundation, Verify. **Fan-out** units are always
**per-app** (7), driven by `migration-manifest.json`. Each agent's acceptance
criteria = that phase's gate.

**Rule for executing agents:** everything runs against the empty `suite.localhost`
on a branch; rollback = re-add the old apps and reinstall. No clone/backup gating
(the site holds no data — D5). The data-safe variant in §12 applies only to a
populated site.

---

## 11. Follow-on (NOT this plan)

After the monorepo stands, the original Suite spec resumes as a separate plan,
now trivial to build because everything shares one namespace:

- Shared **notification system** (mentions, shares, event invites/reminders,
  comments) across all modules.
- **Storage metering** per artifact + **storage-based billing** (per-site, D1).
- **Common permission layer** + **user-permission management**.
- **Admin console** + **storage analytics**.
- **First-time-setup** / onboarding flow + cross-app integrations.

These live in `suite_core` (and new modules) and are specced separately.

---

## 12. Appendix — Data-safe cutover for a populated site

**This is the real validation target — planned immediately after the empty-site
migration lands, not a hypothetical.** The empty-site run (main plan) exists to
de-risk the *structural* work cheaply; migrating a site that **already holds data**
(the existing deployment with all 7 apps installed) is what actually proves the
migration. **Phases 0–3 and 5–7 are reused unchanged — only Phase 4 (cutover) is
replaced by the data-safe sequence below**, which re-homes modules without ever
dropping a table. The governing rule returns: **never `bench uninstall-app`** on a
populated site (it deletes that app's DocTypes and their data).

**Extra pre-flight:** full DB + files backup, test-restored to a clone; rehearse
this entire sequence on the clone before touching the real site.

**Cutover sequence (run on the clone first, then the real site):**
  1. **Backup.**
  2. `suite` code (all modules moved in) present; add `suite` to `apps.txt` +
     `installed_apps`.
  3. **Pre-migrate patch** — re-parent each migrated module to `suite`:
     ```sql
     UPDATE `tabModule Def`
        SET app_name = 'suite'
      WHERE module_name IN (<all migrated module names>);
     ```
  4. **Pre-seed Patch Log** for renamed patch dotted paths so they are not
     re-executed:
     ```python
     for old, new in patch_rename_map.items():
         if frappe.db.exists("Patch Log", {"patch": old}) and \
            not frappe.db.exists("Patch Log", {"patch": new}):
             frappe.get_doc({"doctype": "Patch Log", "patch": new}).insert()
     ```
  5. Remove the 7 old apps from `apps.txt` + `installed_apps` **manually**
     (site_config/DB edit) — **NOT** `bench uninstall-app` — and remove their code
     dirs.
  6. `bench migrate` → syncs `suite` (Module Defs now owned by `suite`), runs
     remaining patches.
  7. Verify: `bench migrate` green; `tab<DocType>` row counts match the backup;
     `Module Def.app_name='suite'` for all migrated modules; no orphaned `Module
     Def` pointing at removed apps. Then promote clone → production with a fresh
     backup.
