//// Neoffice — added file (no upstream equivalent): the way to Nora that the Drive page offers a Craft editor it frames.
//// The editors' Nora pane (craft-nora, in bvisible/craft-libs) makes no call of its own in the Drive: it looks, once as
//// the editor starts, for `window.<editor>NoraCall(path, body)` on the page of the same origin that frames it, and sends
//// every call of the pane through it, a promise of `{ status, body }` that it reads as a `fetch`'s answer. Neodesk's
//// host page offers the same function (neoffice-mobile: desktop/src/editors/host/host.js, editors/nora.js); here the
//// page makes the call itself, with the person's desk session (the cookie) and the page's CSRF token.
////
//// Where a call goes is never read from anywhere: it is one of the protocol's five paths, at the page's own origin.
//// Anything else is refused before it leaves, and so is a body that is not a plain JSON object or that names `cmd`
//// (Frappe runs the method `cmd` names whatever the path says: with it, the editor could have any method run as the
//// person, past the list below).

/** The calls of the craft-nora protocol (craft-libs crates/nora/src/protocol.rs), and nothing else of the instance. */
export const NORA_PATHS = new Set([
  '/api/method/nora.api.chat.start_or_resume_thread',
  '/api/method/nora.api.chat.post_message',
  '/api/method/nora.api.chat.get_messages',
  '/api/method/nora.api.chat.get_browser_actions',
  '/api/method/nora.api.page_observation.receive_observation',
])

/** The editors that have the pane, by the prefix of their messages (CraftEditor.vue's PREFIXES). */
const EDITORS = new Set(['wordcraft', 'gridcraft', 'deckcraft', 'pdfcraft'])

/** An observation carries the document's visible text: far from this. */
export const MAX_BODY = 4 * 1024 * 1024

/** A message is answered at once (the pane sends `block: 0`); a call still open after this long has no answer coming. */
const TIMEOUT_MS = 180_000

/** What the page holds where its template was not rendered: not a token. */
const UNRENDERED_TOKEN = '{{ csrf_token }}'

/** The arguments of a call as JSON, once they are only that: a plain object without `cmd`, written again; else null. */
export function plainArguments(body) {
  let value
  try {
    value = body === '' ? {} : JSON.parse(body)
  } catch {
    return null
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  if (Object.prototype.hasOwnProperty.call(value, 'cmd')) return null
  return JSON.stringify(value)
}

/**
 * The function the editor calls: `(path, body) => Promise<{ status, body }>`. Status 0, with the reason, when nothing
 * came back; 403 for a path that is not the protocol's, 400 for a body that is not plain arguments, 413 for one too large.
 *
 * @param {object} [options]
 * @param {typeof fetch} [options.fetch]
 * @param {() => string | undefined} [options.csrfToken] read at every call (the page's `window.csrf_token`)
 * @param {number} [options.timeoutMs]
 */
export function noraCall({ fetch = (...args) => globalThis.fetch(...args), csrfToken = () => '', timeoutMs = TIMEOUT_MS } = {}) {
  return async (path, body) => {
    if (!NORA_PATHS.has(String(path))) return { status: 403, body: '' }
    if (typeof body === 'string' && body.length > MAX_BODY) return { status: 413, body: '' }
    const text = plainArguments(typeof body === 'string' ? body : '')
    if (text === null) return { status: 400, body: '' }
    const headers = { Accept: 'application/json', 'Content-Type': 'application/json' }
    const token = csrfToken()
    if (typeof token === 'string' && token && token !== UNRENDERED_TOKEN) headers['X-Frappe-CSRF-Token'] = token
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      // A path: the page's own origin, with its session cookie and nothing else.
      const response = await fetch(String(path), {
        method: 'POST',
        credentials: 'same-origin',
        redirect: 'error',
        headers,
        body: text,
        signal: controller.signal,
      })
      let answer = ''
      try {
        answer = await response.text()
      } catch {
        answer = ''
      }
      return { status: response.status, body: answer }
    } catch (error) {
      return { status: 0, body: JSON.stringify({ exception: `Nora could not be reached: ${error?.message || error}` }) }
    } finally {
      clearTimeout(timer)
    }
  }
}

/**
 * Offers the editor of `prefix` its way to Nora on `target` (the Drive page's window), before the editor starts.
 * Returns what takes it back, which leaves alone a function put there by someone else since.
 */
export function offerNora(target, prefix, options) {
  if (!target || !EDITORS.has(prefix)) return () => {}
  const name = `${prefix}NoraCall`
  const call = noraCall(options)
  target[name] = call
  return () => {
    if (target[name] === call) delete target[name]
  }
}
