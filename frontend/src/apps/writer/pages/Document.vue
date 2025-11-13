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
    v-model:showComments="showComments"
    v-model:showVersions="showVersions"
  >
    <template
      #breadcrumbs
      v-if="document.doc?.settings?.minimal && entity.write"
    >
      <Button variant="ghost">
        <router-link
          :to="$store.state.breadcrumbs?.[0]?.route"
          class="cursor-pointer"
        >
          <LucideArrowLeft class="size-3.5" />
        </router-link>
      </Button>
    </template>
    <template #content v-if="document.doc?.settings && document.doc.write">
      <UsersBar
        v-if="editor?.storage?.collaborationCursor?.users?.length > 1"
        :users="
          editor.storage.collaborationCursor.users.filter(
            (k) => k.name !== $store.state.user.id,
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
  <div v-else-if="showVersions" class="flex w-full flex-col">
    <div
      class="py-3 px-5 border-b flex items-center justify-between bg-surface-white"
    >
      <div class="text-md font-medium text-ink-gray-8">
        <span class="text-ink-gray-6">Version History - </span>
        {{ document.doc.title }}
      </div>
    </div>
  </div>

  <!-- <ErrorPage v-if="document.error" :error="document.error" /> -->
  <LoadingIndicator
    v-if="!document.data && document.loading"
    :error="document.error"
    class="w-10 h-full text-neutral-100 mx-auto"
  />
  <div v-else class="flex w-full h-full overflow-hidden">
    <TextEditor
      v-if="document.doc?.settings"
      ref="editorEl"
      v-model:show-comments="showComments"
      v-model:show-versions="showVersions"
      v-model:versionPreview="versionPreview"
      :entity="document.doc"
      :document
      :editable
      :settings
      :show-resolved
      @save-comment="saveDocument(true)"
      @new-version="
        (snap, duration, title) => {
          newVersion.submit({
            snapshot: fromUint8Array(snap),
            duration,
            title,
            manual: !!title,
          })
        }
      "
    />
    <MarkdownEditor
      v-else-if="document.doc?.mime_type == 'text/markdown'"
      :document
      :settings
    />
    <!-- 
    <WriterSettings
      v-if="showSettings"
      v-model="showSettings"
      :doc-settings
      :global-settings
      :editable
    /> -->
  </div>
</template>

<script setup>
import { fromUint8Array } from 'js-base64'
import Navbar from '@/components/Navbar.vue'
import {
  ref,
  inject,
  defineAsyncComponent,
  provide,
  onBeforeUnmount,
  watch,
  h,
  computed,
  useTemplateRef,
} from 'vue'
import { useStore } from 'vuex'
import {
  createResource,
  LoadingIndicator,
  useDoc,
  usePageMeta,
} from 'frappe-ui'

import VersionsSidebar from '@/components/VersionsSidebar.vue'
// import WriterSettings from '@/components/WriterSettings.vue'
// import UsersBar from '@/components/UsersBar.vue'

import { toast } from '@/utils/'
import useDocument from '@/composables/useDocument'
import LucideWifi from '~icons/lucide/wifi'
import LucideLock from '~icons/lucide/lock'
import LucideLockOpen from '~icons/lucide/lock-open'
import LucideWifiOff from '~icons/lucide/wifi-off'
import LucideFileWarning from '~icons/lucide/file-warning'

const TextEditor = defineAsyncComponent(
  () => import('@/components/TextEditor.vue'),
)
const MarkdownEditor = defineAsyncComponent(
  () => import('@/components/MarkdownEditor.vue'),
)

const props = defineProps({
  id: String,
  slug: String,
})

const store = useStore()
const showResolved = ref(false)
const editorEl = useTemplateRef('editorEl')
const editor = computed(() => editorEl.value?.editor)
provide('editor', editor)
provide('showResolved', showResolved)

// Reactive data properties
const versionPreview = ref(null)
const showComments = ref(false)
const showVersions = ref(false)
const owner = computed(() => document.doc?.owner)
const isOldSchema = computed(() => {
  if (!owner.value) return false
  return !document.doc?.settings?.collab && store.state.user.id !== owner.value
})

const editable = computed(
  () =>
    !inIframe.value &&
    !!document.doc?.write &&
    !document.doc?.settings?.lock &&
    editor.value &&
    !isOldSchema.value,
)
watch(showVersions, (v) => {
  if (!v) versionPreview.value = null
})

const inIframe = inject('inIframe')

const document = useDocument(props.id)
usePageMeta(() => ({
  title: document.doc ? document.doc.title : 'Loading...',
}))

const globalSettings = useDoc({
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

const newVersion = createResource({
  url: 'drive.api.docs.create_version',
  makeParams: (k) => ({ ...k, doc: document.doc.document }),
  onSuccess(data) {
    if (data && data.length != document.doc.versions.length)
      document.doc.versions = data
  },
})

const toggleMinimal = (val) => {
  const sidebar = window.document.querySelector('#sidebar')
  if (!sidebar) return
  if (val) {
    sidebar.style.display = 'none'
  } else {
    sidebar.style.removeProperty('display')
  }
}

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

onBeforeUnmount(() => {
  const sidebar = window.document.querySelector('#sidebar')
  if (sidebar) sidebar.style.removeProperty('display')
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
