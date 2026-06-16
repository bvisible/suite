import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

/**
 * Shared suite session store.
 *
 * One source of truth for "who is logged in" across all 7 apps. Reads the
 * `user_id` cookie set by the Frappe backend; `Guest` is treated as logged-out.
 * Per-app session stores should be replaced by (or delegate to) this one so the
 * unified shell and every app route group agree on auth state.
 */
export const useSessionStore = defineStore('suite-session', () => {
  const sessionUser = (): string | null => {
    const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
    let user = cookies.get('user_id')
    if (user === 'Guest') user = null
    return user
  }

  const user = ref<string | null>(sessionUser())
  const isLoggedIn = computed(() => !!user.value)

  const login = createResource({
    url: 'login',
    onError() {
      throw new Error('Invalid email or password')
    },
    onSuccess() {
      user.value = sessionUser()
      login.reset()
    },
  })

  const logout = createResource({
    url: 'logout',
    onSuccess() {
      user.value = null
      window.location.reload()
    },
  })

  return { user, isLoggedIn, login, logout }
})
