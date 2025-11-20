<template>
  <Teleport to="#navbar-content" defer>
    <Button
      v-if="
        Array.from(commentsMap).find((k) => k[1].content?.arr?.[0].resolved)
      "
      :icon="LucideMessageSquareDot"
      variant="outline"
      tooltip="Toggle resolved"
      @click="showResolved = !showResolved"
    ></Button>
    <Button
      v-if="comments._map.size"
      :icon="showComments ? LucideMessageSquareOff : LucideMessageSquareQuote"
      variant="outline"
      :tooltip="showComments ? 'Hide comments' : 'Show comments'"
      @click="showComments = !showComments"
    ></Button>
  </Teleport>
  <div class="flex flex-col w-full">
    <div
      class="w-full max-w-[100vw] overflow-x-auto border-b border-outline-gray-modals grid md:grid-cols-[minmax(0,1fr)_minmax(auto,48rem)_minmax(0,1fr)]"
    >
      <div />
      <TextEditorFixedMenu
        class="py-1.5 mx-auto flex justify-center shrink-0 transition-opacity duration-1"
        v-if="editable && !settings.minimal"
        :buttons="menuButtons"
        :class="hideToolbar ? 'opacity-0' : 'opacity-100'"
      />
      <div class="flex items-center justify-end pr-4"></div>
    </div>

    <div
      id="editorScrollContainer"
      class="flex-1 flex w-full overflow-y-auto grid grid-cols-1 md:grid-cols-[minmax(10rem,1fr)_minmax(auto,48rem)_minmax(0,1fr)]"
      @mousemove="hideToolbar = false"
    >
      <ToC :editor :anchors />
      <div
        class="mx-auto cursor-text w-full flex justify-center h-full"
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
          ]"
          :upload-function
          :autofocus="true"
          :mentions="{ mentions: allUsers.data, selectable: false }"
          placeholder="Start writing here..."
          :bubble-menu="settings.minimal && menuButtons"
          :extensions="editorExtensions"
          :editable
          :starterkit-options="{ history: false }"
          @keydown="
            (e) => {
              if (!e.metaKey && !e.ctrlKey) {
                hideToolbar = true
                if (!edited) {
                  edited = true
                  autoversion()
                }
              }
            }
          "
        >
          <template #editor="{ editor }">
            <EditorContent
              class="prose-sm prose-v2"
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

      <FloatingComments
        v-if="editor"
        :y-comments="comments"
        v-model:active-comment="activeComment"
        :class="showComments ? 'opacity-100' : 'opacity-0'"
        :document
        :show-resolved
        :editor
        @save="saveComments"
      />
    </div>
  </div>
</template>

<script setup>
import {
  TextEditor as FTextEditor,
  TextEditorFixedMenu,
  useDoc,
  toast,
  useFileUpload,
} from 'frappe-ui'
import { v4 as uuidv4 } from 'uuid'
import {
  computed,
  defineAsyncComponent,
  onMounted,
  ref,
  onBeforeUnmount,
  h,
  inject,
  provide,
} from 'vue'
import { EditorContent } from '@tiptap/vue-3'

import Collaboration from '@tiptap/extension-collaboration'
import { onKeyDown } from '@vueuse/core'

import { isModKey, COMMON_EXTENSIONS } from '@/utils'

import LucideMessageSquarePlus from '~icons/lucide/message-square-plus'
import LucideMessageSquareQuote from '~icons/lucide/message-square-quote'
import LucideMessageSquareOff from '~icons/lucide/message-square-off'
import LucideMessageSquareDot from '~icons/lucide/message-square-dot'
import { updateURLSlug } from '@/utils'

import store from '@/store'
import emitter from '@/emitter'
import { rename, allUsers } from 'frappe-ui/frappe/drive/js/resources'
import { printDoc, getRandomColor } from '@/utils'
import { formatDate } from '@/utils/format'
import FloatingQuoteButton from '@/extensions/comment-button'
import MediaDownload from '@/extensions/media-download'
import { CommentExtension, rebuild } from '@/extensions/comments'
import { CollaborationCursor } from '@/extensions/collaboration-cursor'
import { CharacterCount } from '@/extensions/character-count'
import {
  default as TableOfContents,
  getHierarchicalIndexes,
} from '@tiptap/extension-table-of-contents'
import OldCommentExtension from '@/extensions/old-comment'
import { useYjs } from '@/composables/useYjs'
import FloatingComments from './FloatingComments.vue'
import { TabsExtension } from '@/extensions/tabs'

const activeComment = ref(null)
const showComments = defineModel('showComments')
watch([showComments, activeComment], () => rebuild(editor.value))
const showResolved = ref(false)
const edited = ref(false)
const hideToolbar = ref(false)

const props = defineProps({
  document: Object,
  entity: Object,
  settings: Object,
  editable: Boolean,
  currentVersion: { required: false, type: Object },
})
const emit = defineEmits(['saveComment'])
const inIframe = inject('inIframe')

const anchors = ref([])

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

const {
  doc,
  save,
  cleanup,
  provider,
  permanentUserData,
  newComment,
  comments,
  saveComments,
} = useYjs(props.document, editor, edited)
const commentsMap = computed(() => comments._map)
const showResolvedButton = computed(() => {
  let show = false
  console.log(comments._map.size)
  if (!comments._map.size) return false
  comments.forEach((k) => k.resolved && (show = true))
  return show
})

const onCommentActivated = (id) => {
  if (!id) return
  activeComment.value = id
  showComments.value = true
  const commentEl =
    document.querySelector(`span[data-comment-name="${id}"]`) ||
    document.querySelector(`span[data-comment-id="${id}"]`)
  if (!commentEl.offsetParent)
    commentEl.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
      inline: 'nearest',
    })
}
const editorExtensions = [
  ...COMMON_EXTENSIONS,
  CharacterCount,
  TabsExtension,
  CommentExtension.configure({
    comments,
    doc,
    activeComment,
    showComments,
    showResolved,
    edited,
    onActivated: onCommentActivated,
  }),
  OldCommentExtension.configure({
    onCommentActivated: onCommentActivated,
  }),
  TableOfContents.configure({
    onUpdate: (val) => (anchors.value = val),
    getIndex: getHierarchicalIndexes,
    scrollParent: () => scrollParent.value,
  }),
  props.entity.comment &&
    !inIframe &&
    FloatingQuoteButton.configure({
      onClick: () => addComment(),
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

const menuButtons = computed(() => [
  'Paragraph',
  ['Heading 1', 'Heading 2', 'Heading 3', 'Heading 4'],
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
  'Image',
  'Video',
  'Iframe',
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
  'Separator',
  {
    label: 'Comment',
    icon: LucideMessageSquarePlus,
    action: () => addComment(),
    isActive: () => false,
  },
])

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

const addComment = () => {
  showComments.value = true
  const id = uuidv4()
  const { state } = editor.value
  const { from, to } = state.selection
  if (from === to) return
  newComment(
    id,
    from,
    to,
    store.state.user.id,
    state.doc.textBetween(from, to, ' '),
  )
  activeComment.value = id
  const tr = state.tr
  editor.value.view.dispatch(tr)
}

const autoversion = async () => {
  if (!edited.value) return
  const html = editor.value.getHTML()

  try {
    const data = await props.document.newVersion.submit({ data: html })
    if (data) {
      props.document.doc.versions.push(data)
    }
  } catch (error) {
    console.error('Failed to create snapshot:', error)
  }
}
const manualSave = () => save(true)

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

emitter.on('manual-save', manualSave)

const autoversionInterval = setInterval(autoversion, 10 * 60 * 1000)
onMounted(() => {
  const { view, state } = editor.value
  view.dispatch(state.tr)
  editor.value.on('create', applyTemplate)
})

onBeforeUnmount(() => {
  if (edited.value) save()
  emitter.off('print-file')
  if (autoversionInterval) clearInterval(autoversionInterval)
  cleanup()
})

onKeyDown('Enter', autorename)
onKeyDown('s', (e) => {
  if (!isModKey(e)) return
  e.preventDefault()
  manualSave()
  toast.success('Saved document', { duration: 0.75 })
})
</script>
<style>
@import url('@/styles/editor.css');
iframe {
  border: 1px solid var(--surface-gray-4) !important;
}
</style>
