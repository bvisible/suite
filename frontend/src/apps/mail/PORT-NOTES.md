# Mail — port notes

Standalone source: `apps/mail/frontend/src` (was a **bun** project — now yarn).
Now at `apps/suite/frontend/src/apps/mail/`, served under **`/mail`**.
See the parent `../README.md` for suite-wide conventions.

## Routes (relative to `/mail`, names namespaced `mail-*`)
Authed routes nest under `views/MailLayout.vue`: `mail-mailbox`, `mail-mail`,
`mail-address-books`/`mail-address-book`, `mail-contacts`/`mail-contact`,
`mail-exchanges`/`mail-exchange`, `mail-mime-message`, `mail-domains`/`mail-domain`,
`mail-members`, `mail-invites`, plus the 5 shortcut routes.
**`isPublic` (guest-reachable, outside the layout):** `mail-login`, `mail-signup`,
`mail-invite-setup`, `mail-forgot-password`, `mail-reset-password`, `mail-mime-message`.

## What changed vs standalone
- `createWebHistory('/mail')` dropped; routes are relative under `/mail`. All
  hardcoded string-path navigations were converted to named routes.
- The `beforeEach` (setup-wizard escape, dashboard access, account resolution,
  mailbox validation, shortcut expansion) moved into a prefix-scoped guard (`router.ts`),
  using `useSessionStore` for login state.
- **`socket.ts`** reads `window.socketio_port` (was a `common_site_config.json` import).
- **`$user` / `$dayjs` / `$socket`** are provided by `MailLayout` (gone from `main.ts`).
- **Translation:** own plugin removed; bare `__()` via the foundation; `routes.ts`
  populates `window.translatedMessages` via `suite.mail.api.get_translations`.
- Pinia stores: `mail-user`, `mail-session` (the latter delegates login state to the
  shared `suite-session` but keeps mail's own login/logout resources).
- frappe-ui git-pin → `1.0.0-beta.9`; `lucide-vue-next` `0.383` → `^1.0.0`.
- **Deps added:** `@iframe-resizer/child`+`/vue`, `cheerio`, `dompurify`, `firebase`,
  `gemoji`, `vue-pdf-embed`. `@vueuse/core` pinned `^10.4.1` (matches beta.9 peer).
  `firebase`/PDF kept lazy. `@iframe-resizer/vue` imported via its concrete `.vue` file.
- Backend method paths rewritten: `suite.mail.api.*`, `suite.mail.utils.*`, and
  `mail.client.*` → **`suite.client.*`** (the `client` module was hoisted top-level).

## Known / deferred (please review)
- **Push notifications (Firebase FCM) won't work at runtime yet.** The suite has no
  `vite-plugin-pwa`, so `/assets/suite/frontend/sw.js` is not emitted. The push code
  (`utils/frappe-push-notification.ts`, registered fail-safe in `MailLayout onMounted`,
  SW URL repointed to `/assets/suite/frontend/`) is in place but inert until a
  **foundation PWA/FCM setup** lands. Flagged suite-wide.
- `mail-session` doesn't push login state into `suite-session` on mail-local login
  (works because both read the `user_id` cookie); a sync would be cleaner.

## Verify (Phase 6)
Log in at `suite.localhost:8004/mail`. Confirm: mailbox lists + opens a message;
compose/send; attachments + PDF preview; address books/contacts; admin domains;
the public `/mail/login` + signup/forgot-password flows render for guests.
