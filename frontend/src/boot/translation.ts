import type { App } from 'vue'

/**
 * Shared frappe-style translation for the whole suite.
 *
 * The standalone apps (calendar, mail, …) each shipped their own translation
 * plugin that installed a global `__()` onto `app.config.globalProperties` (so
 * bare `__('text')` resolves inside templates) and onto `window.__` (so plain
 * `<script>`/util code can call it too). Since several ported apps use `__()`
 * the same way, the suite registers ONE generic translation plugin here instead
 * of per-app copies.
 *
 * This boot is intentionally endpoint-agnostic: `translate()` only looks up
 * `window.translatedMessages`. WHO populates that map is an app concern — an app
 * route module can fetch its own translations on load (e.g. mail/calendar's
 * `suite.mail.api.get_translations`) and assign the result to `window.translatedMessages`.
 * Until then `translate()` is an identity function, so untranslated UI still
 * renders the source string.
 */
export function translate(message: string, replace?: Array<string | number>): string {
  const messages = window.translatedMessages || {}
  let translated = messages[message] || message

  const hasPlaceholders = /{\d+}/.test(translated) && Array.isArray(replace)
  if (!hasPlaceholders) return translated

  return translated.replace(/{(\d+)}/g, (match: string, index: string) => {
    const value = replace![Number(index)]
    return value !== undefined ? String(value) : match
  })
}

export const translationPlugin = {
  install(app: App) {
    app.config.globalProperties.__ = translate
    window.__ = translate
  },
}

//// Neoffice — added: the suite loads the user's translations ONCE, before the first render, for every app.
//// Upstream leaves it to each app's route module (see above): Meet, Sheets and Slides never did, so a French
//// account saw them in English, the cockpit included, and the apps that did could paint their first screen in
//// English before the answer came (neoffice-maintenance#1316). Same endpoint as Drive and Writer: the user's
//// language, else the system's. It waits at most `timeoutMs` (the answer weighs ~1.5 MB compressed); a late
//// answer still lands for whatever renders after it.
export async function loadTranslations(timeoutMs = 2500): Promise<void> {
  if (window.translatedMessages) return
  const request = fetch('/api/method/suite.drive.api.product.get_translations', {
    headers: { Accept: 'application/json' },
    credentials: 'same-origin',
  })
    .then((response) => (response.ok ? response.json() : null))
    .then((body) => {
      if (body && body.message && typeof body.message === 'object' && !window.translatedMessages) {
        window.translatedMessages = body.message
      }
    })
    .catch(() => undefined) // untranslated UI still renders its source strings
  await Promise.race([request, new Promise((resolve) => setTimeout(resolve, timeoutMs))])
}

export default translationPlugin
