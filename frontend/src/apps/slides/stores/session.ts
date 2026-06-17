import { computed, reactive } from 'vue'

/**
 * Slides session compat shim.
 *
 * Slides reads `session.user` / `session.isLoggedIn` from plain ES modules
 * (outside any component `setup()` / active Pinia), so it cannot consume the
 * suite's Pinia `useSessionStore` directly at module scope. This shim mirrors
 * that store's source of truth — the `user_id` cookie set by the Frappe backend
 * (`Guest` => logged-out) — so both agree on auth without a per-app CSRF/fetch
 * wrapper. The shared `useSessionStore` (`@/boot/session`) remains the store the
 * shell + router auth-gate use.
 */
const sessionUser = (): string | null => {
  const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  let user = cookies.get('user_id')
  if (user === 'Guest') user = null
  return user
}

export const session = reactive({
  user: sessionUser(),
  isLoggedIn: computed((): boolean => !!session.user),
})
