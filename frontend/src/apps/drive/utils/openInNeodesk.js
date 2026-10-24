//// Neoffice — added file (no upstream equivalent): « Ouvrir dans Neodesk », a document of this Drive opened in the
//// editor window of Neodesk, the desktop app of Neoffice (bvisible/neoffice-mobile, desktop/src/editors/drive-link.js).
////
//// The page hands Neodesk `neodesk://drive/<host>/<id>`: this site's host name and the file's id, nothing else (no
//// token, no name, no port). Neodesk opens the document where it is, as its Documents tab does, and only for an
//// instance the person is signed in to there. A page cannot know whether Neodesk is installed (nothing ties the
//// browser to it, and no local port is ever asked: Zoom, 2019): the address is tried within the click (a browser may
//// refuse to start another program without one), and when the page neither lost the focus nor was hidden after a
//// moment, a quiet « Nothing opened? » offers the download, with « Don't show again » kept in this browser.

import { computed, onScopeDispose, ref, watch } from 'vue'

/** What Neodesk opens where it is: the types the Drive's editors write back (suite/drive/wopi/craft.py, EDITORS). */
export const NEODESK_EXTENSIONS = ['docx', 'xlsx', 'pptx', 'pdf']
/** The editor of the Drive for each of them (get_installed_editors names them so). */
const EDITOR_OF = { docx: 'word', xlsx: 'sheet', pptx: 'deck', pdf: 'pdf' }
/** Where Neodesk is downloaded: its public releases, the address Neodesk itself shows for them. */
export const NEODESK_DOWNLOAD_URL = 'https://github.com/bvisible/neoffice-desktop-releases/releases/latest'
/** How long the page waits for a sign that Neodesk took the address before it says « Nothing opened? ». */
export const NOTHING_OPENED_AFTER_MS = 2500
/** Where this browser keeps « Don't show again ». */
export const HINT_HIDDEN_KEY = 'neoffice.drive.neodesk-hint-hidden'
/** The ids of the Drive's files, as Neodesk takes them. */
const FILE_ID = /^[A-Za-z0-9_-]{1,140}$/

const extensionOf = (name) => {
  const text = String(name || '')
  return text.includes('.') ? text.split('.').pop().toLowerCase() : ''
}

/**
 * The address that opens the file `fileId` of this site in Neodesk, or null where Neodesk could not take it: a page
 * that is not served over https on its standard port (a development bench), an id of another shape.
 */
export function neodeskLink(location, fileId) {
  if (!location || location.protocol !== 'https:' || location.port) return null
  const host = String(location.hostname || '').toLowerCase()
  if (!/^[a-z0-9.-]{1,253}$/.test(host) || !host.includes('.')) return null
  // An address in numbers (a bench on an IP): Neodesk takes host names only, and would say nothing.
  if (/^\d+$/.test(host.split('.').pop())) return null
  if (!FILE_ID.test(String(fileId || ''))) return null
  return `neodesk://drive/${host}/${fileId}`
}

/** Whether Neodesk opens this entity of the Drive: a file (not a folder, a link or a hosted document) of its types. */
export function opensInNeodesk(entity) {
  if (!entity || entity.is_folder || entity.is_link) return false
  if (['Link', 'Document', 'Presentation', 'Spreadsheet'].includes(entity.file_type)) return false
  return NEODESK_EXTENSIONS.includes(extensionOf(entity.file_name))
}

/** Whether the site has the Drive's editor for this file (`installed`: what get_installed_editors answered). */
export function editorInstalledFor(entity, installed) {
  const editor = EDITOR_OF[extensionOf(entity && entity.file_name)]
  return Boolean(editor && installed && Object.prototype.hasOwnProperty.call(installed, editor))
}

/** Whether this browser is a computer's: Neodesk is for Mac and Windows, never a phone or a tablet. */
export function isDesktopBrowser(nav) {
  if (!nav) return false
  if (nav.userAgentData && nav.userAgentData.mobile === true) return false
  const agent = String(nav.userAgent || '')
  if (/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle|Opera Mini/i.test(agent)) return false
  // An iPad asks for the desktop site and says « Macintosh »: it is the only one with a touch screen.
  if (/Macintosh/i.test(agent) && Number(nav.maxTouchPoints) > 1) return false
  return /Macintosh|Windows/i.test(agent)
}

/** Whether the person said « Don't show again » in this browser. Unreadable storage (a private window): not said. */
export function hintHidden(storage) {
  try {
    return storage.getItem(HINT_HIDDEN_KEY) === '1'
  } catch {
    return false
  }
}

/** « Don't show again », kept in this browser when it can be. */
export function hideHint(storage) {
  try {
    storage.setItem(HINT_HIDDEN_KEY, '1')
  } catch {
    // A browser that keeps nothing: the hint shows again next time, nothing worse.
  }
}

/**
 * Whether this browser hands an address the page cannot open to an error page in its place: Firefox may, for an address
 * no program takes (no Neodesk), when the page itself goes to it. Chrome, Edge and Safari keep the page and say nothing
 * or ask; Firefox gets the address in a hidden frame of the page instead, whose error nobody sees.
 */
export function replacesPageOnUnknownAddress(nav) {
  return /Firefox\//.test(String((nav && nav.userAgent) || ''))
}

/**
 * Hands `link` to the system, within the click that asked (no step before it), then watches for `waitMs` whether
 * the page lost the focus or was hidden, which is what Neodesk coming to the front does. When nothing of that
 * happened, `onNothing()` (the page says « Nothing opened? », unless the person asked not to be told). A guess, not a
 * proof: a browser's own question about the link does not always take the focus. Answers a function that stops the
 * watch (the page went away meanwhile).
 */
export function tryNeodesk(
  link,
  { win = window, doc = document, nav = win.navigator, onNothing = () => {}, waitMs = NOTHING_OPENED_AFTER_MS } = {},
) {
  let left = false
  let frame = null
  const leave = () => {
    left = true
  }
  const hidden = () => {
    if (doc.visibilityState === 'hidden') left = true
  }
  win.addEventListener('blur', leave)
  win.addEventListener('pagehide', leave)
  doc.addEventListener('visibilitychange', hidden)
  const stop = () => {
    win.clearTimeout(timer)
    win.removeEventListener('blur', leave)
    win.removeEventListener('pagehide', leave)
    doc.removeEventListener('visibilitychange', hidden)
    frame?.remove()
    frame = null
  }
  const timer = win.setTimeout(() => {
    stop()
    if (!left) onNothing()
  }, waitMs)
  if (replacesPageOnUnknownAddress(nav)) {
    frame = doc.createElement('iframe')
    frame.setAttribute('aria-hidden', 'true')
    frame.tabIndex = -1
    frame.style.display = 'none'
    frame.src = link
    doc.body.appendChild(frame)
  } else {
    win.location.href = link
  }
  return stop
}

/** The browser's storage, when it lets the page read it at all (a private window may not). */
function browserStorage(win) {
  try {
    return win.localStorage
  } catch {
    return null
  }
}

/**
 * « Ouvrir dans Neodesk » as a file's page offers it (components/Navbar.vue, the bar's button and its menu): `link`, the
 * address when the button is offered (a file's own page, a person signed in, a computer's browser, a type Neodesk opens
 * where it is, whose editor the site has — `installedEditors`, get_installed_editors — and a page not framed), else
 * null; `open()`, for the click; `hint`, whether « Nothing opened? » shows; `close()` and `never()` (« Don't show again »).
 * The editors are asked once a file's page is shown. Everything stops with the component (onScopeDispose).
 */
export function useOpenInNeodesk({ route, entity, isLoggedIn, inIframe, installedEditors, win = window, doc = document }) {
  watch(
    () => route.name === 'drive-File' && isLoggedIn.value && !inIframe,
    (asked) => {
      if (asked && !installedEditors.data && !installedEditors.loading) installedEditors.fetch()
    },
    { immediate: true },
  )
  const link = computed(() => {
    const shown = entity.value
    if (route.name !== 'drive-File' || !isLoggedIn.value || inIframe || !shown) return null
    if (!opensInNeodesk(shown) || !isDesktopBrowser(win.navigator)) return null
    if (!editorInstalledFor(shown, installedEditors.data)) return null
    return neodeskLink(win.location, shown.name)
  })
  const hint = ref(false)
  let stop = null
  function close() {
    hint.value = false
    win.removeEventListener('blur', close)
  }
  function never() {
    hideHint(browserStorage(win))
    close()
  }
  // No step before the address: a browser starts another program only within the click that asked.
  function open() {
    const address = link.value
    if (!address) return
    close()
    stop?.()
    stop = tryNeodesk(address, {
      win,
      doc,
      onNothing: () => {
        if (hintHidden(browserStorage(win))) return
        hint.value = true
        // Neodesk may still come, once the person answered the browser's question about the link: the hint then goes.
        win.addEventListener('blur', close)
      },
    })
  }
  onScopeDispose(() => {
    stop?.()
    close()
  })
  return { link, hint, open, close, never }
}
