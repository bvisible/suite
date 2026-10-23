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
////
//// The editor tells Nora which Drive file its document is (`document.id` of the page context it sends with each
//// message), the id this page gave it with the file (CraftEditor.vue's `open`). A message that names another file
//// (an editor still on a file this page has left) leaves without it: never another file than the page's. The server
//// reads the id again under the person's rights anyway (neoffice_theme.editor_document).

/** The person's answer to a card shown in the pane (« sauvegarde ce modèle »: a letter template to confirm, #1822). Not
 * nora's `respond`, which also approves and edits an e-mail waiting to leave: a door for the template cards only. */
export const CARD_PATH = '/api/method/nora.api.cards.confirm_template'

/** The calls of the craft-nora protocol (craft-libs crates/nora/src/protocol.rs), and nothing else of the instance. */
export const NORA_PATHS = new Set([
  '/api/method/nora.api.chat.start_or_resume_thread',
  '/api/method/nora.api.chat.post_message',
  '/api/method/nora.api.chat.get_messages',
  '/api/method/nora.api.chat.get_browser_actions',
  '/api/method/nora.api.page_observation.receive_observation',
  CARD_PATH,
])

/** What a card's answer may say: yes or no, nothing else. */
const CARD_ACTIONS = new Set(['approve', 'reject'])
const MAX_TOKEN = 140

/** Where a link the pane shows may lead, on this page's origin: a document of the Drive, a page of the desk, NeoMail. */
export const OPEN_PREFIXES = ['/drive/', '/app/', '/neomail']

/** The calls that carry the page context (`context`, a JSON text). */
const MESSAGE_PATHS = new Set([
  '/api/method/nora.api.chat.start_or_resume_thread',
  '/api/method/nora.api.chat.post_message',
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
 * The arguments of a message (JSON text) with the document's file id kept only when it is `fileId`, the page's own file;
 * an id of any other file is taken out of the context, and none is ever added. Arguments that carry no context, or no
 * id, are left as they came.
 */
export function keepThePagesFile(text, fileId) {
  let args
  let context
  try {
    args = JSON.parse(text)
    context = typeof args.context === 'string' ? JSON.parse(args.context) : null
  } catch {
    return text
  }
  const document = context && typeof context === 'object' && !Array.isArray(context) ? context.document : null
  if (!document || typeof document !== 'object' || Array.isArray(document) || !('id' in document)) return text
  if (typeof fileId === 'string' && fileId && document.id === fileId) return text
  const rest = { ...document }
  delete rest.id
  return JSON.stringify({ ...args, context: JSON.stringify({ ...context, document: rest }) })
}

/** Whether the arguments of a card's answer are a card's token and yes or no, and nothing else. */
export function cardAnswer(text) {
  let value
  try {
    value = JSON.parse(text)
  } catch {
    return false
  }
  const keys = Object.keys(value || {})
  return (
    keys.every((key) => key === 'token' || key === 'action') &&
    typeof value.token === 'string' &&
    value.token.length > 0 &&
    value.token.length <= MAX_TOKEN &&
    CARD_ACTIONS.has(value.action)
  )
}

/**
 * The function the editor calls: `(path, body) => Promise<{ status, body }>`. Status 0, with the reason, when nothing
 * came back; 403 for a path that is not the protocol's, 400 for a body that is not plain arguments, 413 for one too large.
 *
 * @param {object} [options]
 * @param {typeof fetch} [options.fetch]
 * @param {() => string | undefined} [options.csrfToken] read at every call (the page's `window.csrf_token`)
 * @param {number} [options.timeoutMs]
 * @param {() => string | undefined} [options.fileId] the Drive file the page shows, read at every call: a message names
 *   that file or none (keepThePagesFile)
 */
export function noraCall({
  fetch = (...args) => globalThis.fetch(...args),
  csrfToken = () => '',
  timeoutMs = TIMEOUT_MS,
  fileId,
} = {}) {
  return async (path, body) => {
    // One value, read once: an object whose text changes between two reads never passes the list.
    if (typeof path !== 'string' || !NORA_PATHS.has(path)) return { status: 403, body: '' }
    if (typeof body === 'string' && body.length > MAX_BODY) return { status: 413, body: '' }
    let text = plainArguments(typeof body === 'string' ? body : '')
    if (text === null) return { status: 400, body: '' }
    if (path === CARD_PATH && !cardAnswer(text)) return { status: 400, body: '' }
    if (fileId && MESSAGE_PATHS.has(path)) text = keepThePagesFile(text, fileId())
    const headers = { Accept: 'application/json', 'Content-Type': 'application/json' }
    const token = csrfToken()
    if (typeof token === 'string' && token && token !== UNRENDERED_TOKEN) headers['X-Frappe-CSRF-Token'] = token
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      // A path: the page's own origin, with its session cookie and nothing else.
      const response = await fetch(path, {
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
 * The address a link of Nora's leads to when it is one of this instance's pages, else null: a path (`/drive/f/…`), or
 * an address of the page's own origin, under OPEN_PREFIXES. Another site, a `javascript:` link, a path that a browser
 * reads as another host (`//…`, a backslash) are never one.
 */
export function instanceHref(url, origin) {
  if (typeof url !== 'string' || !url || url.length > 2048 || /[\s\\]/.test(url)) return null
  if (!url.startsWith('/') && !url.startsWith(`${origin}/`)) return null
  if (url.startsWith('//')) return null
  let address
  try {
    address = new URL(url, origin)
  } catch {
    return null
  }
  if (address.origin !== origin || !['http:', 'https:'].includes(address.protocol)) return null
  const path = address.pathname
  const allowed = OPEN_PREFIXES.some((prefix) =>
    prefix.endsWith('/') ? path.startsWith(prefix) : path === prefix || path.startsWith(`${prefix}/`),
  )
  return allowed ? address.href : null
}

/**
 * The function the editor calls to open a link of Nora's (a card's « Ouvrir », a link in a reply): `(url) => boolean`.
 * An address of this instance opens in a new tab, on a click of the person's; anything else is refused (false).
 *
 * @param {object} [options]
 * @param {(href: string) => void} [options.open]
 * @param {() => string} [options.origin] the page's origin
 */
export function noraOpen({
  open = (href) => globalThis.open(href, '_blank', 'noopener,noreferrer'),
  origin = () => globalThis.location.origin,
} = {}) {
  return (url) => {
    const href = instanceHref(url, origin())
    if (!href) return false
    open(href)
    return true
  }
}

/**
 * Offers the editor of `prefix` its way to Nora on `target` (the Drive page's window), before the editor starts: its
 * calls (`<prefix>NoraCall`) and the links it opens (`<prefix>NoraOpen`). Returns what takes them back, which leaves
 * alone a function put there by someone else since.
 */
export function offerNora(target, prefix, options) {
  if (!target || !EDITORS.has(prefix)) return () => {}
  const offered = { [`${prefix}NoraCall`]: noraCall(options), [`${prefix}NoraOpen`]: noraOpen(options) }
  Object.assign(target, offered)
  return () => {
    for (const [name, fn] of Object.entries(offered)) {
      if (target[name] === fn) delete target[name]
    }
  }
}
