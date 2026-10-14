<!-- //// Neoffice: new file — a Craft editor (Word, Excel, PowerPoint, PDF) framed in the Drive page.
     The editor is a browser build served from this site (suite/public/craft/, see suite/drive/wopi/craft.py): it
     speaks `postMessage` to this page (`?host=parent`), which gives it the file and stores what it saves, through the
     WOPI endpoints, with a token and no session cookie, the way Collabora's server does. //// -->
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
      <p class="text-p-base text-ink-gray-7">
        {{
          __(
            'Someone else saved a new version of this document since you opened it. You can keep yours as a copy next to it, or replace theirs with yours.'
          )
        }}
      </p>
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

const src = computed(() => {
  const query = new URLSearchParams({ host: 'parent', v: session.version })
  if (session.author) query.set('author', session.author)
  return `${session.base_url}index.html?${query}`
})

class Conflict extends Error {}

const extension = (name) => (name.includes('.') ? name.split('.').pop().toLowerCase() : '')

function post(type, fields = {}, transfer = []) {
  frame.value?.contentWindow?.postMessage({ type: `${prefix}:${type}`, ...fields }, window.location.origin, transfer)
}

// The token and not the cookie: the same authentication as Collabora's server, and no CSRF token to carry. It
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

async function store(name, bytes) {
  if (name.toLowerCase() === session.file_name.toLowerCase()) return overwrite(bytes)
  if (extension(name) === extension(session.file_name)) return saveCopy(name, bytes)
  exportFile(name, bytes)
}

function save(name, bytes) {
  saving = saving.then(async () => {
    try {
      await store(name, bytes)
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
  const stem = name.replace(/\.[^.]+$/, '')
  try {
    await saveCopy(`${stem} (${__('copy')}).${extension(name)}`, bytes)
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
      openDocument()
      break
    case 'dirty':
      dirty.value = !!data.dirty
      break
    case 'save':
      save(data.name, data.bytes)
      break
    case 'failed':
      loading.value = false
      error.value = data.error || __('The editor could not start.')
      break
  }
}

function reload() {
  error.value = null
  loading.value = true
  dirty.value = false
  reloads.value += 1
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

onMounted(() => window.addEventListener('message', onMessage))
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  // Let the editor free its memory (a document, a 40 MB module) at once.
  if (frame.value) frame.value.src = 'about:blank'
})
</script>
