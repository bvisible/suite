import { ref } from 'vue'
import { defineStore } from 'pinia'

/**
 * Root suite store: cross-app UI state that the shell and every app share
 * (active app id, global theme, command-palette open state, etc.).
 *
 * Per-app stores live under src/apps/<app>/stores/ and are namespaced; this
 * root store only holds what the shell itself needs.
 */
export const useRootStore = defineStore('suite-root', () => {
  // id of the currently active suite app (drive|slides|writer|sheets|meet|mail|calendar)
  const activeApp = ref<string | null>(null)
  const theme = ref<'light' | 'dark'>('light')

  function setActiveApp(id: string | null) {
    activeApp.value = id
  }

  function setTheme(next: 'light' | 'dark') {
    theme.value = next
    document.documentElement.setAttribute('data-theme', next)
    document.documentElement.setAttribute('data-theme-mode', next)
  }

  return { activeApp, theme, setActiveApp, setTheme }
})
