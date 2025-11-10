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
  <!-- <Teleport v-if="document?.doc?.settings && entity.write" to="#navbar-content" defer>
    <UsersBar
      v-if="editorValue?.storage?.collaborationCursor?.users?.length > 1"
      :users="
        editorValue.storage.collaborationCursor.users.filter(
          (k) => k.name !== $store.state.user.id
        )
      "
    />

    <Button
      v-if="document?.doc?.settings?.lock"
      :icon="LucideLock"
      variant="outline"
      @click="
        () => {
          document.doc.settings.lock = null
          editor.editor.commands.focus()
          toast('Unlocked document temporarily.')
        }
      "
    />
    <Button
      v-if="document?.doc?.settings?.lock === null"
      :icon="LucideLockOpen"
      variant="outline"
      @click="
        () => {
          document.doc.settings.lock = true
          editor.editor.commands.blur()
          toast('Locked document.')
        }
      "
    />
  </Teleport> -->
  <Navbar
    v-if="!inIframe && document.doc"
    :root-entity="document.doc"
    :breadcrumbs="
      document.doc.breadcrumbs?.map((k) => ({ ...k, label: k.title }))
    "
    :actions="isFrappeDoc ? navBarActions : null"
  >
    <template
      #breadcrumbs
      v-if="document?.doc?.settings?.minimal && entity.write"
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
  </Navbar>

  <!-- <ErrorPage v-if="document.error" :error="document.error" /> -->
  <LoadingIndicator
    v-if="!document.data && document.loading"
    :error="document.error"
    class="w-10 h-full text-neutral-100 mx-auto"
  />
  <div v-else class="flex w-full h-full overflow-hidden">
    <VersionsSidebar
      v-if="showVersions"
      v-model="current"
      v-model:show-versions="showVersions"
      :editor="editor?.editor"
      :versions="entity.versions"
      @save-document="saveDocument"
    />
    <TextEditor
      v-if="document?.doc?.settings"
      ref="editor"
      v-model:edited="edited"
      v-model:raw-content="rawContent"
      v-model:yjs-content="yjsContent"
      v-model:show-comments="showComments"
      v-model:current="current"
      :entity="document.doc"
      :editable="inIframe ? false : editable"
      :is-frappe-doc
      :settings
      :users="allUsers.data || []"
      :show-resolved
      @save-document="saveDocument"
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
import { fromUint8Array, toUint8Array } from 'js-base64'
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

import { prettyData, updateURLSlug, dynamicList, toast } from '@/utils/'
import { entitiesDownload } from '@/utils/download'
import { allUsers, apps } from '@/resources/permissions'
import useDocument from '@/composables/useDocument'
import MessagesSquare from '~icons/lucide/messages-square'
import LucideRulerDimensionLine from '~icons/lucide/ruler-dimension-line'
import LucideUserPen from '~icons/lucide/user-pen'
import LucideEraser from '~icons/lucide/eraser'
import LucideView from '~icons/lucide/view'
import LucideSettings from '~icons/lucide/settings'
import LucideImageDown from '~icons/lucide/image-down'
import LucideNewspaper from '~icons/lucide/newspaper'
import LucideDownload from '~icons/lucide/download'
import LucideListRestart from '~icons/lucide/list-restart'
import LucideHistory from '~icons/lucide/history'
import MessageSquareDot from '~icons/lucide/message-square-dot'
import LucideWifi from '~icons/lucide/wifi'
import LucideLock from '~icons/lucide/lock'
import LucideLockOpen from '~icons/lucide/lock-open'
import LucideWifiOff from '~icons/lucide/wifi-off'
import LucideFileWarning from '~icons/lucide/file-warning'

const TextEditor = defineAsyncComponent(
  () => import('@/components/TextEditor.vue'),
)

const props = defineProps({
  id: String,
  slug: String,
})

const store = useStore()
const showResolved = ref(false)
const editor = useTemplateRef('editor')
const editorValue = computed(() => editor.value?.editor)
provide('editor', editorValue)
provide('showResolved', showResolved)

// Reactive data properties
const title = ref(null)
const rawContent = ref(null)
const yjsContent = ref(null)
const entity = ref(null)
const current = ref(null)
const showComments = ref(false)
const showVersions = ref(false)
const showSettings = ref(false)
const edited = ref(false)
const owner = computed(() => document.doc?.owner)
const isOldSchema = computed(() => {
  if (!owner.value) return false
  return !document?.doc?.settings?.collab && store.state.user.id !== owner.value
})

const editable = computed(
  () =>
    !!document?.doc?.write &&
    !document?.doc?.settings?.lock &&
    !isOldSchema.value,
)
watch(showVersions, (v) => {
  if (!v) current.value = null
})
const isFrappeDoc = computed(
  () => document.doc && document.doc.mime_type === 'frappe_doc',
)

const saveDocument = (comment = false) => {
  if ((!comment && !edited.value) || current.value) return
  if (document.doc.write || (comment && document.doc.comment)) {
    if (isFrappeDoc.value) {
      const params = {
        entity_name: props.id,
        doc_name: document.doc.document,
        content: rawContent.value,
        yjs: fromUint8Array(yjsContent.value || ''),
        comment,
      }
      if (document.doc.settings.collab) delete params.content
      else delete params.yjs
      updateDocument.submit(params)
    } else
      updateDocument.submit({
        entity_name: props.id,
        content: rawContent.value,
      })
    return true
  }
}
const inIframe = inject('inIframe')

const document = useDocument(props.id)
document.onSuccess((data) => {
  yjsContent.value = toUint8Array(data.content)
})
usePageMeta(() => ({
  title: document.doc ? document.doc.title : 'Document',
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
const onSuccess = (data) => {
  // document.setData(prettyData([data])[0])
  store.commit('setActiveEntity', data)

  rawContent.value = data.raw_content
}

const settings = computed(() => {
  if (!isFrappeDoc.value) return {}
  for (const [k, v] of Object.entries(document.doc?.settings || {})) {
    if (v === 'global') delete document.doc?.settings[k]
  }
  return {
    ...(globalSettings.doc?.writer_settings || {}),
    ...document.doc?.settings,
  }
})

store.commit('setCurrentResource', document)

const updateDocument = createResource({
  url: 'drive.api.files.save_doc',
  onError() {
    toast({
      title: 'There was an error.',
      icon: LucideFileWarning,
      text: "We can't save your file. Please contact support.",
    })
  },
})

const newVersion = createResource({
  url: 'drive.api.docs.create_version',
  makeParams: (k) => ({ ...k, doc: document.doc.document }),
  onSuccess(data) {
    if (data && data.length != document.doc.versions.length)
      document.doc.versions = data
  },
})

// Functions and constants
const navBarActions = computed(
  () =>
    document.doc && [
      'extend',
      {
        group: true,
        hideLabel: true,
        items: dynamicList([
          {
            label: 'View',
            icon: LucideView,
            cond: document.doc.write,
            submenu: [
              {
                label: 'Lock',
                switch: true,
                switchValue: document.doc.settings.lock,
                icon: LucideLock,
                onClick: (val) => {
                  document.doc.settings.lock = val
                  document.setValue.submit({
                    settings: JSON.stringify(document.doc.settings),
                  })
                },
              },
              {
                label: 'Wide',
                icon: LucideRulerDimensionLine,
                switch: true,
                switchValue: document.doc.settings.wide,
                onClick: (val) => {
                  document.doc.settings.wide = val
                  document.setValue.submit({
                    settings: JSON.stringify(document.doc.settings),
                  })
                },
              },
              {
                onClick: (val) => {
                  document.doc.settings.minimal = val
                  document.setValue.submit({
                    settings: JSON.stringify(document.doc.settings),
                  })
                },
                switch: true,
                switchValue: document.doc.settings.minimal,
                label: 'Minimal',
                icon: LucideEraser,
              },
            ],
          },
          {
            onClick: () => {
              showSettings.value = true
            },
            label: 'Settings',
            icon: LucideSettings,
          },
          {
            label: 'Export',
            icon: LucideDownload,
            submenu: dynamicList([
              {
                onClick: exportMedia,
                label: 'Export Media',
                icon: LucideImageDown,
              },
              {
                onClick: exportBlog,
                label: 'Export Blog',
                icon: LucideNewspaper,
                cond: apps.data && apps.data.find((k) => k.name === 'blog'),
              },
            ]),
          },
          {
            onClick: clearCache,
            label: 'Clear Cache',
            icon: LucideListRestart,
          },
        ]),
      },
      {
        group: true,
        hideLabel: true,
        items: dynamicList([
          {
            icon: LucideHistory,
            label: 'Versions',
            cond: document?.doc?.settings.collab,
            onClick: () => (showVersions.value = true),
          },
          {
            icon: MessagesSquare,
            label: 'Show Comments',
            onClick: () => (showComments.value = true),
            isEnabled: () => !showComments.value,
            cond: document.doc?.comments?.length,
          },
          {
            icon: MessagesSquare,
            label: 'Hide Comments',
            onClick: () => (showComments.value = false),
            isEnabled: () => showComments.value,
            cond: document.doc?.comments?.length,
          },
          {
            icon: MessageSquareDot,
            label: 'Show Resolved',
            onClick: () => {
              showResolved.value = true
              showComments.value = true
            },
            isEnabled: () => !showResolved.value,
            cond: document.doc?.comments?.filter((k) => k.resolved)?.length,
          },
          {
            icon: MessageSquareDot,
            label: 'Hide Resolved',
            onClick: () => (showResolved.value = false),
            isEnabled: () => showResolved,
            cond: document.doc?.comments?.filter((k) => k.resolved)?.length,
          },
        ]),
      },
    ],
)

const toggleMinimal = (val) => {
  const sidebar = window.document.querySelector('#sidebar')
  if (!sidebar) return
  if (val) {
    sidebar.style.display = 'none'
  } else {
    sidebar.style.removeProperty('display')
  }
}

const clearCache = () => {
  const DBDeleteRequest = window.indexedDB.deleteDatabase(
    'fdoc-' + document.doc.name,
  )

  DBDeleteRequest.onerror = () => {
    console.error('Error deleting database.')
  }

  DBDeleteRequest.onsuccess = () => {
    console.log('Database deleted successfully')
  }
}

const exportMedia = async () => {
  toast('Preparing...')
  const urls = editor.value.editor.commands.getEmbedUrls()
  const getExtension = createResource({
    url: 'drive.api.docs.get_extension',
  })
  for (const i in urls) {
    const ext = await getExtension.fetch({ entity_name: urls[i].name })
    if (ext) urls[i].title += '.' + ext
  }
  entitiesDownload(null, urls)
}
const exportBlog = async () => {
  toast('Starting export...')
  createResource({
    url: 'drive.api.docs.create_blog',
    auto: true,
    params: {
      entity_name: props.id,
      html: editorValue.value.getHTML(),
    },
    onSuccess: (d) => {
      window.open('/app/blog-post/' + d)
    },
    onError: (error) => {
      toast({
        title: error.messages[0] || 'Could not export your document.',
        type: 'error',
      })
    },
  })
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
  if (edited.value) saveDocument()
  const sidebar = window.document.querySelector('#sidebar')
  if (sidebar) sidebar.style.removeProperty('display')
})

let toasted
watch(isOldSchema, (v) => {
  if (document?.doc?.settings && document.doc.write && v && !toasted) {
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
