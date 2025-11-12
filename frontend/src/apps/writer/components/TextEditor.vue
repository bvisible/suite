<template>
  <div class="flex flex-col w-full">
    <TextEditorFixedMenu
      v-if="editable && !settings.minimal && !versionPreview"
      class="w-full max-w-[100vw] overflow-x-auto border-b border-outline-gray-modals justify-start md:justify-center py-1.5 shrink-0"
      :buttons="menuButtons"
    />
    <div
      v-if="versionPreview"
      class="bg-surface-gray-2 text-ink-gray-8 p-3 text-base flex justify-between items-center"
    >
      <div class="flex flex-col gap-1">
        <div v-if="versionPreview.manual">
          <span class="font-medium">{{ versionPreview.title }}</span>
        </div>
        <div v-else>
          This is a automatic snapshot of this document from
          {{ formatDate(versionPreview.title) }}.
        </div>
        <div class="text-xs text-ink-gray-5">
          Editing is disabled until you exit this preview.
        </div>
      </div>
      <div class="flex gap-2">
        <Button
          variant="ghost"
          label="Exit"
          class="hover:!bg-surface-gray-2 hover:underline"
          @click="emitter.emit('clear-snapshot')"
        />
        <Button
          variant="solid"
          label="Restore"
          @click="emitter.emit('restore-snapshot', versionPreview)"
        />
      </div>
    </div>
    <div id="editorScrollContainer" class="flex-1 flex w-full overflow-y-auto">
      <div
        class="mx-auto cursor-text w-full flex justify-center h-full"
        :class="versionPreview ? 'pb-15' : ''"
        @click="
          $event.target.tagName === 'DIV' &&
          textEditor.editor?.chain?.().focus?.().run?.()
        "
      >
        <FTextEditor
          ref="textEditor"
          class="min-w-full h-full flex flex-col"
          :editor-class="[
            'min-h-full mx-auto px-10 overflow-x-auto py-7',
            settings?.wide
              ? 'md:min-w-[100ch] md:max-w-[100ch]'
              : 'md:min-w-[48rem] md:max-w-[48rem]',
            versionPreview ? 'pb-24' : '',
          ]"
          :editable
          :upload-function
          :mentions="{ mentions: allUsers.data, selectable: false }"
          placeholder="Start writing here..."
          :bubble-menu="settings.minimal && menuButtons"
          :extensions="editorExtensions"
          :autofocus="true"
          :starterkit-options="{ history: false }"
          @change="
            () => {
              if (!editable) return
              edited = true
            }
          "
        >
          <template #editor="{ editor }">
            <EditorContent
              class="prose-sm"
              :style="{
                fontFamily: `var(--font-${settings?.font_family})`,
                fontSize: `${settings?.font_size || 15}px`,
                lineHeight: settings?.line_height || 1.5,
              }"
              :editor="editor"
            />
          </template>
        </FTextEditor>
      </div>
      <!-- <ToC v-show="anchors.length > 1" :editor :anchors :class="editable ? 'top-24' : 'top-15'" /> -->
      <!-- <FloatingComments
        v-if="comments.length"
        v-model:show-comments="showComments"
        v-model:active-comment="activeComment"
        v-model:comments="comments"
        :entity="entity"
        :editor
        @save="$emit('saveComment')"
        @autosave="autosave"
      /> -->
    </div>
  </div>
</template>

<script setup>
import {
  TextEditor as FTextEditor,
  TextEditorFixedMenu,
  useDoc,
  debounce,
  useFileUpload,
} from 'frappe-ui'
import { v4 as uuidv4 } from 'uuid'
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  ref,
  onBeforeUnmount,
  h,
  watch,
  inject,
  provide,
} from 'vue'
import { EditorContent } from '@tiptap/vue-3'
import { toUint8Array } from 'js-base64'
// import * as Y from 'yjs'
// import { IndexeddbPersistence } from 'y-indexeddb'
import { ySyncPluginKey } from 'y-prosemirror'
import { WebrtcProvider } from 'y-webrtc'
import Collaboration from '@tiptap/extension-collaboration'
import { onKeyDown } from '@vueuse/core'
import router from '@/router'
import {
  default as TableOfContents,
  getHierarchicalIndexes,
} from '@tiptap/extension-table-of-contents'
import { isModKey } from '@/utils'

import LucideMessageCircle from '~icons/lucide/message-circle'
import { updateURLSlug } from '@/utils'

import store from '@/store'
import emitter from '@/emitter'
import { rename, allUsers } from 'frappe-ui/frappe/drive/js/resources'
import { printDoc, getRandomColor } from '@/utils'
import { formatDate } from '@/utils/format'
import { toast } from '@/utils/'
import FontFamily from '@/extensions/font-family'
import FloatingQuoteButton from '@/extensions/comment'
import MediaDownload from '@/extensions/media-download'
import ExtendedCommentExtension from '@/extensions/extended-comment'
import { CharacterCount } from '@/extensions/character-count'
import { CollaborationCursor } from '@/extensions/collaboration-cursor'
import { FontSize } from '@/extensions/font-size'
import EmbedExtension from '@/extensions/embed-extension'
import { useYjs } from '@/composables/useYjs'
// import FloatingComments from './FloatingComments.vue'

const showComments = defineModel('showComments')
const versionPreview = defineModel('versionPreview')
const edited = ref(false)

const props = defineProps({
  document: Object,
  entity: Object,
  settings: Object,
  editable: Boolean,
  showResolved: Boolean,
  currentVersion: { required: false, type: Object },
})
const emit = defineEmits(['newVersion', 'saveComment', 'saveDocument'])
const inIframe = inject('inIframe')

const comments = ref([])
const anchors = ref([])
const activeComment = ref(null)

const textEditor = ref('textEditor')
const editor = computed(() => {
  const editor = textEditor.value?.editor
  return editor
})
provide('editor', editor)
const scrollParent = computed(() =>
  document.querySelector('#editorScrollContainer'),
)
defineExpose({ editor })

watch(
  () => props.settings,
  (val, prev) => {
    // if (val.versioning === prev?.versioning && autoversion) return
    // const duration = Math.max(0.9, +val.versioning - 1) * 1000
    // autoversion = debounce(() => {
    //   const snap = Y.snapshot(doc)
    //   const prevVersion =
    //     props.entity.versions[props.entity.versions.length - 1]
    //   const prevSnapshot = prevVersion
    //     ? Y.decodeSnapshot(toUint8Array(prevVersion.snapshot))
    //     : Y.emptySnapshot
    //   if (prevVersion != null) {
    //     // account for the action of adding a version to ydoc
    //     prevSnapshot.sv.set(
    //       prevVersion.clientID,
    //       prevSnapshot.sv.get(prevVersion.clientID) + 1,
    //     )
    //   }
    //   if (!Y.equalSnapshots(prevSnapshot, snap)) {
    //     emit('newVersion', Y.encodeSnapshot(snap), +props.settings.versioning)
    //   }
    // }, duration)
  },
)

watch(
  () => props.currentVersion,
  (val) => {
    if (!val) return
    toast('Changing version')
    const { view } = editor.value
    view.dispatch(
      view.state.tr.setMeta(ySyncPluginKey, {
        snapshot: Y.decodeSnapshot(val[1].snapshot),
        prevSnapshot: Y.decodeSnapshot(val[0].snapshot),
      }),
    )
  },
)

const { doc, save, cleanup, provider, permanentUserData } = useYjs(
  props.document,
  edited,
)

const editorExtensions = [
  FontSize,
  CharacterCount,
  TableOfContents.configure({
    onUpdate: (val) => (anchors.value = val),
    getIndex: getHierarchicalIndexes,
    scrollParent: () => scrollParent.value,
  }),
  FontFamily.configure({
    types: ['textStyle'],
  }),
  EmbedExtension,
  props.entity.comment &&
    !inIframe &&
    FloatingQuoteButton.configure({
      onClick: () => {
        createNewComment(editor.value)
      },
    }),
  ExtendedCommentExtension.configure({
    onCommentActivated: (id) => {
      const isResolved = comments.value.find((k) => id === k.name)?.resolved
      if (id && (!isResolved || showResolved)) {
        activeComment.value = id
        showComments.value = true
        const commentEl = document.querySelector(
          `span[data-comment-id="${id}"]`,
        )
        if (!commentEl.offsetParent)
          commentEl.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
            inline: 'nearest',
          })
      }
    },
  }),
  MediaDownload,
  Collaboration.configure({
    document: doc,
    field: 'default',
    ySyncOptions: {
      permanentUserData,
    },
  }),
  CollaborationCursor.configure({
    provider,
    user: {
      name: store.state.user.fullName,
      id: store.state.user.id,
      avatar: store.state.user.imageURL,
      color: getRandomColor(),
    },
  }),
]

const menuButtons = computed(
  () => [
    'Paragraph',
    ['Heading 1', 'Heading 2', 'Heading 3'],
    'Separator',
    'Bold',
    'Italic',
    'Strikethrough',
    'Link',
    'FontColor',
    'Separator',
    ['Bullet List', 'Numbered List', 'Task List'],
    'Separator',
    ['Align Left', 'Align Center', 'Align Right'],
    'Separator',
    {
      label: 'FontOptions',
      component: h(
        defineAsyncComponent(() => import('./ManageFont.vue')),
        {
          editor,
          font_size: props.settings.font_size || 15,
          font_family: props.settings.font_family || 'inter',
        },
      ),
    },
    'Separator',
    {
      label: 'Comment',
      icon: LucideMessageCircle,
      action: createNewComment,
      isActive: () => false,
    },
    'Image',
    'Video',
    'Iframe',
  ],
  'Blockquote',
  'Code',
  [
    'InsertTable',
    'AddColumnBefore',
    'AddColumnAfter',
    'DeleteColumn',
    'AddRowBefore',
    'AddRowAfter',
    'DeleteRow',
    'MergeCells',
    'SplitCell',
    'ToggleHeaderColumn',
    'ToggleHeaderRow',
    'ToggleHeaderCell',
    'DeleteTable',
  ],
)

// Util functions
const autorename = (bypass = false) => {
  const { $anchor } = editor.value.view.state.selection
  // Check if we're in the very first textblock
  if (!($anchor.index(0) === 1 && $anchor.depth === 1)) {
    // scroll down if in the last line
    if (
      $anchor.depth === 1 &&
      editor.value.state.doc.childCount - 1 === $anchor.index(0)
    ) {
      scrollParent.value.scroll(0, scrollParent.value.scrollHeight)
    }
    return
  }
  const implicitTitle = editor.value.state.doc.firstChild.textContent
    .replaceAll('#', '')
    .replaceAll('@', '')
    .trim()
  if (!props.entity.title.startsWith('Untitled Document') && !bypass) return
  if (implicitTitle.length)
    rename.submit(
      {
        entity_name: props.entity.name,
        new_title: implicitTitle,
      },
      {
        onSuccess: () => {
          props.document.doc.title = rename.params.new_title
          updateURLSlug(rename.params.new_title)
        },
      },
    )
}

async function applyTemplate() {
  if (!editor.value || !props.settings.template) {
    return
  }

  const html = editor.value.getHTML()
  if (!html || html === '<p></p>') {
    const getTemplate = useDoc({
      doctype: 'Writer Template',
      name: props.settings.template,
    })

    getTemplate.onSuccess((data) => {
      const html = editor.value.getHTML()
      if (html && html !== '<p></p>') return
      const content = data.content.replaceAll(
        /\{\{(date|time|datetime)\}\}/g,
        (_, type) => formatDate(new Date(), { datetime: type }),
      )
      editor.value.commands.setContent(content)
    })

    // trigger the fetch after registering the callback
    getTemplate.fetch()
  }
}

const uploadFunction = (file) => {
  const fileUpload = useFileUpload()
  return fileUpload.upload(file, {
    params: { file_id: props.entity.name },
    upload_endpoint: `/api/method/writer.api.embed.add`,
  })
}
const getOrderedComments = (doc) => {
  const comments = []
  doc.descendants((node, pos) => {
    node.marks.forEach((mark) => {
      if (mark.type.name === 'comment' && mark.attrs.commentId) {
        comments.push({ id: mark.attrs.commentId, pos })
      }
    })
  })

  return comments.sort((a, b) => a.pos - b.pos)
}

const createNewComment = (editor) => {
  showComments.value = true
  const id = uuidv4()
  editor.chain().focus().setComment(id).run()
  const orderedComments = getOrderedComments(editor.state.doc)
  const newComment = {
    name: id,
    owner: store.state.user.id,
    creation: new Date(),
    content: '',
    edit: true,
    new: true,
    loading: true,
    replies: [],
  }
  comments.value = [...comments.value, newComment].toSorted((a, b) => {
    const pos1 = orderedComments.findIndex((k) => k.id === a.name)
    const pos2 = orderedComments.findIndex((k) => k.id === b.name)
    return pos1 - pos2
  })
  activeComment.value = id
}

// Events
onKeyDown('p', (e) => {
  if (isModKey(e)) {
    e.preventDefault()
    if (editor.value) printDoc(editor.value.getHTML(), props.settings)
  }
})

emitter.on('print-file', () => {
  if (editor.value) printDoc(editor.value.getHTML(), props.settings)
})
emitter.on('create-version', (title) => {
  const snap = Y.snapshot(doc)
  emit('newVersion', Y.encodeSnapshot(snap), 0, title)
})

onMounted(() => {
  const orderedComments = getOrderedComments(editor.value.state.doc)
  comments.value = props.entity.comments.toSorted((a, b) => {
    const pos1 = orderedComments.findIndex((k) => k.id === a.name)
    const pos2 = orderedComments.findIndex((k) => k.id === b.name)
    return pos1 - pos2
  })
  editor.value.on('create', applyTemplate)
})

onUnmounted(() => {
  emitter.off('print-file')
  emitter.off('create-version')
  if (edited.value) save()
})
onBeforeUnmount(() => {
  comments.value
    .filter((k) => k.new)
    .filter(({ name }) => editor.value.commands.unsetComment(name))
  cleanup()
})

onKeyDown('Enter', () => autorename())
onKeyDown('s', (e) => {
  if (!e.metaKey || !e.shiftKey) {
    return
  }
  e.preventDefault()
  emit('saveDocument')
  toast({
    title: 'Saving document',
  })
})
</script>
<style>
@import url('@/styles/editor.css');
iframe {
  border: 1px solid var(--surface-gray-4) !important;
}

.h-full.overflow-y-auto {
  scrollbar-width: thin;
  scrollbar-gutter: stable;
}
</style>
