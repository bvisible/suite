<!-- //// Neoffice — added file (no upstream equivalent): a Craft editor (NeoWrite, NeoSheet, NeoSlides, NeoPDF) framed in the Drive page.
     The editor is a browser build served from this site (suite/public/craft/, see suite/drive/wopi/craft.py): it
     speaks `postMessage` to this page (`?host=parent`), which gives it the file and stores what it saves, through the
     content endpoints (suite/drive/wopi/endpoints.py), with a token and no session cookie. For staff, it also offers the
     editor its way to Nora (`window.<editor>NoraCall`, utils/craftNora.js), with the desk session. //// -->
<template>
  <div class="relative flex h-full w-full flex-col">
    <!-- Loading state: the build (WebAssembly) and the document -->
    <div v-if="loading" class="absolute inset-0 z-10 flex items-center justify-center bg-surface-base">
      <div class="flex flex-col items-center gap-3">
        <LucideLoaderCircle class="size-8 animate-spin text-ink-gray-6" />
        <span class="text-p-base text-ink-gray-7">{{ __('Loading editor…') }}</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="absolute inset-0 z-10 flex items-center justify-center bg-surface-base">
      <div class="max-w-[450px] p-10 bg-surface-base rounded-md text-center shadow-xl flex flex-col items-center gap-4">
        <LucideAlertCircle class="size-10 text-ink-gray-7" />
        <span class="text-p-base text-ink-gray-7">{{ error }}</span>
        <div class="flex gap-2">
          <Button variant="subtle" @click="reload">{{ __('Try again') }}</Button>
          <Button variant="solid" @click="downloadOriginal">{{ __('Download') }}</Button>
        </div>
      </div>
    </div>

    <!-- The editor does not know the permissions of the page: say it when the document is read-only -->
    <div
      v-if="!session.can_write"
      class="flex items-center gap-2 border-b border-outline-gray-2 bg-surface-gray-1 px-3 py-1.5 text-p-sm text-ink-gray-7"
    >
      <LucideInfo class="size-4 shrink-0" />
      {{ __('You can read this document but not change it.') }}
    </div>

    <iframe
      ref="frame"
      :key="reloads"
      :src="src"
      :title="session.file_name"
      class="w-full grow border-0"
      allow="clipboard-read; clipboard-write; fullscreen"
    />

    <!-- Someone saved the document since it was opened here: nothing was written, the user chooses -->
    <Dialog
      v-model:open="conflictOpen"
      :title="__('This document has changed')"
      size="sm"
      :actions="[
        { label: __('Save as a copy'), variant: 'solid', onClick: keepAsCopy },
        { label: __('Replace their version'), variant: 'subtle', theme: 'red', onClick: replaceTheirs },
      ]"
    >
      <p class="text-p-base text-ink-gray-7">{{ conflictMessage }}</p>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, call, toast } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRouter } from 'vue-router'
import LucideAlertCircle from '~icons/lucide/alert-circle'
import LucideInfo from '~icons/lucide/info'
import LucideLoaderCircle from '~icons/lucide/loader-circle'
import { offerNora } from '@/apps/drive/utils/craftNora'

const props = defineProps({
  // What `suite.drive.wopi.craft.get_craft_editor_config` answered for this file.
  config: { type: Object, required: true },
  previewEntity: Object,
})
const emit = defineEmits(['loaded'])

const router = useRouter()

// The prefix of the editor's messages (`wordcraft:ready`, …).
const PREFIXES = { word: 'wordcraft', sheet: 'gridcraft', deck: 'deckcraft', pdf: 'pdfcraft' }
const prefix = PREFIXES[props.config.editor]

// Own copy: the token is renewed when it expires.
const session = reactive({ ...props.config })
const frame = ref(null)
const reloads = ref(0)
const loading = ref(true)
const error = ref(null)
const dirty = ref(false)
const conflict = ref(null)
const conflictOpen = computed({
  get: () => !!conflict.value,
  set: (open) => {
    if (!open) conflict.value = null
  },
})
// The content this page last read or wrote: a save is refused when the file has moved on since.
let baseVersion = ''
// Saves go one at a time, in the order the editor made them.
let saving = Promise.resolve()
// The build is 20 to 40 MB of WebAssembly: a page that has heard nothing of the editor after this long is
// not waiting for a slow network, its build is missing or cannot start (no WebGL2, a blocked script).
const READY_TIMEOUT_MS = 60000
let readyTimer = null

// The page that frames the editor in its own way (the PDF editor's overlay) asks before it throws it away.
defineExpose({ dirty })

// Nora's pane, for staff only: the server says so (`nora`, get_craft_editor_config), with the rule Nora's own endpoints
// apply. The editor looks for its way to her once, as it starts, so it is put on this page before the frame loads; a
// person without it gets no pane. The calls go to this page's origin with the desk session, never to an address read
// from the URL (maintenance#1661).
const withdrawNora = session.nora ? offerNora(window, prefix, { csrfToken: () => window.csrf_token }) : () => {}

const src = computed(() => {
  const query = new URLSearchParams({ host: 'parent', v: session.version })
  if (session.author) query.set('author', session.author)
  return `${session.base_url}index.html?${query}`
})

class Conflict extends Error {}

// One line, with its string right after `__(`: the extractor of the translation catalogs misses the others.
const conflictMessage = __('Someone else saved a new version of this document since you opened it. You can keep yours as a copy next to it, or replace theirs with yours.')

const extension = (name) => (name.includes('.') ? name.split('.').pop().toLowerCase() : '')

function waitForEditor() {
  clearTimeout(readyTimer)
  readyTimer = setTimeout(() => {
    if (!loading.value || error.value) return
    loading.value = false
    error.value = __('The document editor did not start. Your document has not left this server.')
  }, READY_TIMEOUT_MS)
}

function post(type, fields = {}, transfer = []) {
  frame.value?.contentWindow?.postMessage({ type: `${prefix}:${type}`, ...fields }, window.location.origin, transfer)
}

// The token and not the cookie: the same authentication as the NeoDesk shell, and no CSRF token to carry. It
// goes in the URL, as the WOPI protocol has it: nginx's /wopi/ rule (snippets/wopi.conf) turns that query
// argument into the header the endpoints read, and would overwrite one sent by the page.
const wopi = (path, init = {}) =>
  fetch(`${session.wopi_src}${path}?access_token=${encodeURIComponent(session.access_token)}`, {
    credentials: 'omit',
    ...init,
  })

async function failure(response) {
  if (response.status === 401) return __('The editing session has expired. Reload the page.')
  if (response.status === 403) return __('You do not have permission to change this document.')
  if (response.status === 404) return __('This document no longer exists.')
  return __('The server answered {0}.', [response.status])
}

async function openDocument() {
  try {
    let response = await wopi('/contents')
    if (response.status === 401) {
      await renewToken()
      response = await wopi('/contents')
    }
    if (!response.ok) throw new Error(await failure(response))
    baseVersion = response.headers.get('X-Neoffice-Content-Version') || ''
    const bytes = await response.arrayBuffer()
    post('open', { name: session.file_name, bytes }, [bytes])
    loading.value = false
    emit('loaded')
    frame.value?.contentWindow?.focus()
  } catch (e) {
    loading.value = false
    error.value = e.message || __('Unable to load editor')
  }
}

// A session left open past the token's life: ask for a new one rather than lose the user's work.
async function renewToken() {
  const fresh = await call('suite.drive.wopi.craft.get_craft_editor_config', {
    file_id: props.previewEntity.name,
    requested: session.editor,
  })
  if (!fresh?.available) throw new Error(__('The editing session has expired. Reload the page.'))
  session.access_token = fresh.access_token
  session.access_token_ttl = fresh.access_token_ttl
  session.can_write = fresh.can_write
}

async function overwrite(bytes, { force = false } = {}) {
  if (!session.can_write) throw new Error(__('You do not have permission to change this document.'))
  const send = () =>
    wopi('/contents', {
      method: 'POST',
      body: bytes,
      headers: {
        'Content-Type': 'application/octet-stream',
        ...(baseVersion && !force ? { 'X-Neoffice-Base-Version': baseVersion } : {}),
      },
    })
  let response = await send()
  if (response.status === 401) {
    await renewToken()
    response = await send()
  }
  if (response.status === 409) throw new Conflict()
  if (!response.ok) throw new Error(await failure(response))
  baseVersion = response.headers.get('X-Neoffice-Content-Version') || baseVersion
}

// Save As with the same type: a new document next to this one, and the editor moves to it.
async function saveCopy(name, bytes) {
  const query = new URLSearchParams({ file_id: props.previewEntity.name, file_name: name })
  const response = await fetch(`/api/method/suite.drive.wopi.craft.save_copy?${query}`, {
    method: 'POST',
    body: bytes,
    headers: { 'Content-Type': 'application/octet-stream', 'X-Frappe-CSRF-Token': window.csrf_token },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok || !body.message) {
    const reasons = body._server_messages ? JSON.parse(body._server_messages).map((m) => JSON.parse(m).message) : []
    throw new Error(reasons[0] || (await failure(response)))
  }
  const copy = body.message
  // Stored: leaving the page is not losing anything.
  dirty.value = false
  toast.success(__('Saved as {0}', [copy.file_name]))
  router.push({ name: 'drive-File', params: { entityName: copy.file_id } })
}

// An export (PDF, a picture…) is not the document: the browser downloads it.
function exportFile(name, bytes) {
  const url = URL.createObjectURL(new Blob([bytes]))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

// The name of a copy kept next to the document ("Quote (copy).docx").
const copyName = (name) => `${__('{0} (copy)', [name.replace(/\.[^.]+$/, '')])}.${extension(name)}`

async function store(name, bytes, saveAs) {
  // PdfCraft says when the user asked for Save As (it keeps the document's name); the others carry the new name.
  if (saveAs) return saveCopy(copyName(name), bytes)
  if (name.toLowerCase() === session.file_name.toLowerCase()) return overwrite(bytes)
  if (extension(name) === extension(session.file_name)) return saveCopy(name, bytes)
  exportFile(name, bytes)
}

function save(name, bytes, saveAs = false) {
  saving = saving.then(async () => {
    try {
      await store(name, bytes, saveAs)
      post('saved', { name, ok: true })
    } catch (e) {
      if (e instanceof Conflict) {
        conflict.value = { name, bytes }
        post('saved', { name, ok: false, error: __('Someone else changed this document since you opened it.') })
        return
      }
      const reason = e.message || __('The document could not be saved.')
      post('saved', { name, ok: false, error: reason })
      toast.error(reason)
    }
  })
}

// The two ways out of a conflict, both on the bytes the editor handed over.
async function keepAsCopy() {
  const { name, bytes } = conflict.value
  conflict.value = null
  try {
    await saveCopy(copyName(name), bytes)
    post('saved', { name, ok: true })
  } catch (e) {
    toast.error(e.message)
  }
}

async function replaceTheirs() {
  const { name, bytes } = conflict.value
  conflict.value = null
  try {
    await overwrite(bytes, { force: true })
    post('saved', { name, ok: true })
  } catch (e) {
    toast.error(e.message)
  }
}

function onMessage(event) {
  if (event.origin !== window.location.origin || event.source !== frame.value?.contentWindow) return
  const data = event.data
  if (!data || typeof data.type !== 'string' || !data.type.startsWith(`${prefix}:`)) return
  switch (data.type.slice(prefix.length + 1)) {
    case 'ready':
      clearTimeout(readyTimer)
      openDocument()
      break
    case 'dirty':
      dirty.value = !!data.dirty
      break
    case 'save':
      save(data.name, data.bytes, data.saveAs === true)
      break
    case 'failed':
      clearTimeout(readyTimer)
      loading.value = false
      error.value = data.error || __('The editor could not start.')
      break
  }
}

// Cmd/Ctrl+S with the keyboard on the Drive page (after a click on its own chrome, the editor having lost the focus)
// would offer to save THE PAGE. The editor saves its document: this gives it the key. The events reach the page only
// when the editor does not have the focus, and the editor reads a keydown from its canvas once that has the focus.
function onKeydown(event) {
  if (!(event.metaKey || event.ctrlKey) || event.altKey || event.key.toLowerCase() !== 's') return
  event.preventDefault()
  const canvas = frame.value?.contentDocument?.querySelector('canvas')
  if (!canvas) return
  canvas.focus()
  const init = {
    key: event.shiftKey ? 'S' : 's',
    code: 'KeyS',
    keyCode: 83,
    which: 83,
    metaKey: event.metaKey,
    ctrlKey: event.ctrlKey,
    shiftKey: event.shiftKey,
    bubbles: true,
    cancelable: true,
  }
  canvas.dispatchEvent(new frame.value.contentWindow.KeyboardEvent('keydown', init))
  canvas.dispatchEvent(new frame.value.contentWindow.KeyboardEvent('keyup', init))
}

function reload() {
  error.value = null
  loading.value = true
  dirty.value = false
  reloads.value += 1
  waitForEditor()
}

async function downloadOriginal() {
  try {
    const response = await wopi('/contents')
    if (!response.ok) throw new Error(await failure(response))
    exportFile(session.file_name, await response.arrayBuffer())
  } catch (e) {
    toast.error(e.message)
  }
}

// Leaving the page (another file, another app) throws the editor away: ask first when it holds unsaved changes.
// Closing or reloading the tab is guarded by the editor itself.
const leave = () => !dirty.value || window.confirm(__('You have unsaved changes. Leave without saving?'))
onBeforeRouteLeave(leave)
onBeforeRouteUpdate(leave)

onMounted(() => {
  window.addEventListener('message', onMessage)
  window.addEventListener('keydown', onKeydown)
  waitForEditor()
})
onBeforeUnmount(() => {
  clearTimeout(readyTimer)
  window.removeEventListener('message', onMessage)
  window.removeEventListener('keydown', onKeydown)
  withdrawNora()
  // Let the editor free its memory (a document, a 40 MB module) at once.
  if (frame.value) frame.value.src = 'about:blank'
})
</script>
