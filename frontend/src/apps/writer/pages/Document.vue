<template>
  <div
    v-if="inIframe && file.doc"
    class="p-1.5 border-b text-base text-ink-gray-7 flex justify-between items-center relative"
  >
    <div class="font-semibold">
      {{ file.doc.title }}
    </div>
    <div class="flex gap-3 items-center text-ink-gray-5 text-xs">
      Edited {{ file.doc.relativeModified }}
    </div>
  </div>
  <Navbar
    v-if="!inIframe && !showVersions && file.doc"
    v-model:showVersions="showVersions"
    v-model:showTemplates="showTemplates"
    :file
    :document
    :breadcrumbs="file.doc.breadcrumbs?.map((k) => ({ ...k, label: k.title }))"
    :offline
  >
    <template #content v-if="document.doc?.settings && file.doc.write">
      <UsersBar
        v-if="editor?.storage?.collaborationCaret?.users?.length"
        :users="
          editor.storage.collaborationCaret.users.filter(
            (k) => k.id !== $store.state.user.id,
          )
        "
      />

      <Button
        v-if="document.doc?.settings?.lock"
        :icon="LucideLock"
        variant="outline"
        @click="
          () => {
            document.doc.settings.lock = null
            editor.commands.focus()
            toast('Unlocked document temporarily.')
          }
        "
      />
      <Button
        v-if="document.doc?.settings?.lock === null"
        :icon="LucideLockOpen"
        variant="outline"
        @click="
          () => {
            document.doc.settings.lock = true
            editor.commands.blur()
            toast('Locked document.')
          }
        "
      />
    </template>
  </Navbar>
  <VersionsSidebar
    v-if="showVersions"
    v-model="versionPreview"
    v-model:show-versions="showVersions"
    :settings
    :document
    :editor
  />
  <div
    v-if="!document.doc?.collab"
    class="bg-surface-gray-2 text-ink-gray-8 p-3 text-base flex justify-between items-center select-none"
  >
    <div class="flex flex-col gap-1">
      <div class="text-sm text-ink-gray-6">
        This is an old schema document - you cannot do collaboritive editing.
      </div>
    </div>
  </div>
  <ErrorPage v-if="file.error" :error="file.error" />
  <LoadingIndicator
    v-else-if="!file.doc && file.loading"
    class="w-10 h-full text-neutral-100 mx-auto"
  />
  <div
    v-else-if="document?.doc"
    class="flex w-full h-full overflow-hidden"
    v-show="!showVersions"
  >
    <NonCollabEditor
      v-if="!document.doc?.collab"
      ref="editorEl"
      v-model:versionPreview="versionPreview"
      v-model:showSettings="showSettings"
      :file="file.doc"
      :document
      :settings
      :editable
    />
    <MarkdownEditor
      v-else-if="file.doc?.mime_type == 'text/markdown'"
      :document
      :settings
    />
    <TextEditor
      v-else-if="document.doc?.settings"
      ref="editorEl"
      v-model:show-versions="showVersions"
      v-model:versionPreview="versionPreview"
      v-model:showSettings="showSettings"
      :file
      :document
      :editable
      :settings
    />

    <WriterSettings
      v-if="showSettings"
      v-model="showSettings"
      :doc-settings="document"
      :global-settings="globalSettings"
      :editable
    />
    <TemplateDialog v-if="showTemplates" v-model="showTemplates" :editor />
  </div>
</template>

<script setup>
import Navbar from '@/components/Navbar.vue'
import ErrorPage from '@/components/ErrorPage.vue'
import {
  ref,
  inject,
  defineAsyncComponent,
  provide,
  watch,
  h,
  computed,
  useTemplateRef,
} from 'vue'
import { useStore } from 'vuex'
import { LoadingIndicator, useDoc, usePageMeta } from 'frappe-ui'

import VersionsSidebar from '@/components/VersionsSidebar.vue'
import WriterSettings from '@/components/WriterSettings.vue'
import TemplateDialog from '@/components/TemplateDialog.vue'
import UsersBar from '@/components/UsersBar.vue'

import { toast } from '@/utils/'
import useDocument from '@/composables/useDocument'
import LucideLock from '~icons/lucide/lock'
import LucideLockOpen from '~icons/lucide/lock-open'
import TextEditor from '@/components/TextEditor.vue'
import NonCollabEditor from '@/components/NonCollabEditor.vue'
const MarkdownEditor = defineAsyncComponent(
  () => import('@/components/MarkdownEditor.vue'),
)

const props = defineProps({
  id: String,
  slug: String,
})

const store = useStore()
const editorEl = useTemplateRef('editorEl')
const editor = computed(() => editorEl.value?.editor)
provide('editor', editor)

const versionPreview = ref(null)
const showSettings = ref(false)
const showTemplates = ref(false)
const showVersions = ref(false)
const offline = ref(false)

const isOldSchema = computed(() => {
  if (!document.value?.doc) return false
  return (
    !document.value?.doc.collab &&
    store.state.user.id !== document.value?.doc.owner
  )
})

const inIframe = inject('inIframe')
const { file, document } = useDocument(() => props.id)
provide('file', file)

const editable = computed(() => {
  return !inIframe.value &&
    !!file.doc?.write &&
    !document.value?.doc?.settings?.lock &&
    editor.value &&
    !isOldSchema.value
    ? true
    : false
})
watch(showVersions, (v) => {
  if (!v) versionPreview.value = null
})
usePageMeta(() => ({
  title: file.doc ? file.doc.title : 'Loading...',
}))

// fix: bad pattern
const globalSettings = !store.getters.isLoggedIn
  ? { doc: {} }
  : useDoc({
      doctype: 'Drive Settings',
      name: store.state.user.id,
      immediate: true,
      transform: (doc) => {
        doc.writer_settings = JSON.parse(doc.writer_settings) || {}
        return doc
      },
    })

const settings = computed(() => {
  for (const [k, v] of Object.entries(document.value?.doc?.settings || {})) {
    if (v === 'global') delete document.value?.doc?.settings[k]
  }
  return {
    ...(globalSettings.doc?.writer_settings || {}),
    ...(document.value?.doc?.settings || {}),
  }
})

store.commit('setCurrentResource', file)

// Events
window.addEventListener('offline', () => (offline.value = true))
window.addEventListener('online', () => (offline.value = false))

let toasted
watch(isOldSchema, (v) => {
  if (document.value?.doc?.settings && file.doc.write && v && !toasted) {
    toast({
      title:
        'This document uses an old schema. Collaborative editing is disabled.',
      type: 'warning',
      duration: 8000,
    })
    toasted = true
  }
})
</script>
