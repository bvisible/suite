# Calendar — port notes

Standalone source: `apps/calendar_app/frontend/src`. Now at
`apps/suite/frontend/src/apps/calendar/`, served under **`/calendar`**.
See the parent `../README.md` for suite-wide conventions.

## Routes (relative to `/calendar`, names namespaced `calendar-*`)
All real routes nest under `views/CalendarLayout.vue`:
- `account/:accountId/month|week|day/...` → `calendar-month` / `calendar-week` / `calendar-day`
- shortcut routes (`''`, `account/:accountId?`, `month|week|day/...`) →
  `calendar-root-shortcut` / `calendar-account-shortcut` / `calendar-*-shortcut`,
  resolved to full account-scoped routes by the guard.

## What changed vs standalone
- Standalone `createRouter`/`createWebHistory('/calendar')` dropped. The
  account-resolution + shortcut-expansion logic moved into a prefix-scoped guard
  in `router.ts` (attached to the shared suite router, early-returns for non-`calendar-*`).
- **Auth:** the `/mail/login` redirect and the local session store were dropped —
  auth is delegated to the suite (`useSessionStore`, guests → `/login`).
- **`$user` / `$dayjs`** are provided by `CalendarLayout` (the suite `main.ts` no
  longer provides them). `inject('$user')`/`inject('$dayjs')` still work in views.
- **Translation:** the app's own translation plugin was removed; bare `__()` uses
  the shared foundation plugin. `routes.ts` populates `window.translatedMessages`
  via `suite.mail.api.get_translations`.
- Pinia stores namespaced: `calendar-user`, `calendar-branding`.
- Own `tailwind.config.ts` / `index.css` dropped (suite owns these).
- **No new dependencies** were needed — Calendar's deps were already in the suite.
- Backend method paths rewritten to `suite.*` (`suite.mail.api.*`,
  `suite.client.doctype.calendar_event.*`, `suite.calendar.api.*`).

## Known / deferred (please review)
- **`utils/dayjs.ts`** parses custom formats (`dayjs(str, 'YYYY-M-D')`,
  `dayjs(time, 'h a')`) but never extends `customParseFormat`. Carried over faithfully
  from the source — a latent runtime bug that may misparse. Add the plugin if it bites.
- **`AppSidebar.vue`** "Apps" submenu renders `suite.mail.api.get_permitted_apps`
  with absolute hrefs to the old standalone apps — should point at suite prefixes.

## Verify (Phase 6)
Log in at `suite.localhost:8004/calendar`. Confirm: month/week/day views render
and switch; shortcut URLs redirect to the account-scoped route; create/edit an
event (EventModal); settings (profile/appearance) open and save.
