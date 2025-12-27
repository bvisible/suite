<template>
  <div
    v-if="inIframe && document.doc"
    class="p-1.5 border-b text-base text-ink-gray-7 flex justify-between items-center relative"
  >
    <div class="font-semibold">
      {{ document.doc.title }}
    </div>
    <div class="flex gap-3 items-center text-ink-gray-5 text-xs">
      Edited {{ document.doc.relativeModified }}
    </div>
  </div>
  <Navbar
    v-if="!inIframe && !showVersions && document.doc"
    :document
    :breadcrumbs="
      document.doc.breadcrumbs?.map((k) => ({ ...k, label: k.title }))
    "
    v-model:showVersions="showVersions"
    v-model:showTemplates="showTemplates"
  >
    <template #content v-if="document.doc?.settings && document.doc.write">
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
  <ErrorPage v-if="document.error" :error="document.error" />
  <LoadingIndicator
    v-else-if="!document.doc && document.loading"
    class="w-10 h-full text-neutral-100 mx-auto"
  />
  <div
    v-else-if="document.doc"
    class="flex w-full h-full overflow-hidden"
    v-show="!showVersions"
  >
    <NonCollabEditor
      v-if="!document.doc?.collab"
      ref="editorEl"
      v-model:versionPreview="versionPreview"
      v-model:showSettings="showSettings"
      :entity="document.doc"
      :document
      :settings
      :editable
    />
    <MarkdownEditor
      v-else-if="document.doc?.mime_type == 'text/markdown'"
      :document
      :settings
    />
    <TextEditor
      v-else-if="document.doc?.settings"
      ref="editorEl"
      v-model:show-versions="showVersions"
      v-model:versionPreview="versionPreview"
      v-model:showSettings="showSettings"
      :entity="document.doc"
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
import LucideWifi from '~icons/lucide/wifi'
import LucideLock from '~icons/lucide/lock'
import LucideLockOpen from '~icons/lucide/lock-open'
import LucideWifiOff from '~icons/lucide/wifi-off'
import TextEditor from '@/components/TextEditor.vue'

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

const isOldSchema = computed(() => {
  if (!document.doc) return false
  return !document.doc.collab && store.state.user.id !== document.doc.owner
})

const inIframe = inject('inIframe')
const document = useDocument(props.id)
const editable = computed(() =>
  !inIframe.value &&
  !!document.doc?.write &&
  !document.doc?.settings?.lock &&
  editor.value &&
  !isOldSchema.value
    ? true
    : false,
)
watch(showVersions, (v) => {
  if (!v) versionPreview.value = null
})
usePageMeta(() => ({
  title: document.doc ? document.doc.title : 'Loading...',
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
  for (const [k, v] of Object.entries(document.doc?.settings || {})) {
    if (v === 'global') delete document.doc?.settings[k]
  }
  return {
    ...(globalSettings.doc?.writer_settings || {}),
    ...(document.doc?.settings || {}),
  }
})

store.commit('setCurrentResource', document)

// Events
window.addEventListener('offline', () => {
  toast({
    title: "You're offline",
    icon: LucideWifiOff,
    text: "Don't worry, your changes will be saved locally.",
  })
})
window.addEventListener('online', () => {
  toast({ title: 'Back online!', icon: h(LucideWifi) })
})

let toasted
watch(isOldSchema, (v) => {
  if (document.doc?.settings && document.doc.write && v && !toasted) {
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
