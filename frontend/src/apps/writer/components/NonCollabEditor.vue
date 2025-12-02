<template>
  <div class="flex flex-col w-full bg-surface-white">
    <TextEditorFixedMenu
      v-if="editor && editable && !settings.minimal"
      class="w-full max-w-[100vw] overflow-x-auto border-b border-outline-gray-modals justify-start md:justify-center py-1.5 shrink-0"
      :buttons="menuButtons"
    />
    <div
      id="editorScrollContainer"
      class="flex-1 flex w-full overflow-y-auto grid grid-cols-1 relative"
      :class="
        settings.wide
          ? 'md:grid-cols-[minmax(10rem,1fr)_minmax(auto,95ch)_minmax(0,1fr)]'
          : ' md:grid-cols-[minmax(10rem,1fr)_minmax(auto,48rem)_minmax(0,1fr)]'
      "
    >
      <ToC v-if="editor" :editor :anchors />
      <div
        class="cursor-text w-full flex justify-center h-full"
        @click="
          $event.target.tagName === 'DIV' &&
          textEditor.editor?.chain?.().focus?.().run?.()
        "
      >
        <FTextEditor
          ref="textEditor"
          class="min-w-full h-full flex flex-col"
          editor-class="min-h-full mx-auto px-10 overflow-x-auto py-7"
          :content="rawContent"
          :editable
          :upload-function="uploadFunction"
          :mentions="{ mentions: allUsers.data }"
          placeholder="Start writing here..."
          :bubble-menu="settings.minimal && menuButtons"
          :extensions="editorExtensions"
          :autofocus="true"
          @change="
            (val) => {
              if (val === rawContent) return
              rawContent = val
              if (db)
                db.transaction(['content'], 'readwrite')
                  .objectStore('content')
                  .put({ val, saved: new Date() }, props.entity.name)
              if (!editable) return
              edited = true
              autosave()
            }
          "
        >
          <template #editor="{ editor }">
            <EditorContent
              class="bg-surface-white prose prose-sm prose-v2"
              :class="
                settings?.wide
                  ? 'md:min-w-[100ch] md:max-w-[100ch]'
                  : 'md:min-w-[48rem] md:max-w-[48rem]'
              "
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
      <Button
        class="absolute right-3 top-3"
        v-if="comments._map.size"
        :icon="showComments ? LucideMessageSquareOff : LucideMessageSquareQuote"
        variant="outline"
        :tooltip="showComments ? 'Hide comments' : 'Show comments'"
        @click="showComments = !showComments"
      ></Button>
      <Button
        class="absolute right-3 top-12"
        v-if="
          showComments &&
          Array.from(comments._map).find((k) => k[1].content?.arr?.[0].resolved)
        "
        :icon="LucideMessageSquareDot"
        variant="outline"
        tooltip="Toggle resolved"
        @click="showResolved = !showResolved"
      ></Button>
    </div>
  </div>
</template>

<script setup>
import {
  TextEditor as FTextEditor,
  TextEditorFixedMenu,
  debounce,
  useFileUpload,
} from 'frappe-ui'
import { allUsers } from 'frappe-ui/frappe/drive/js/resources'
import { v4 as uuidv4 } from 'uuid'
import {
  computed,
  defineAsyncComponent,
  ref,
  onBeforeUnmount,
  h,
  watch,
  inject,
  provide,
} from 'vue'
import { EditorContent } from '@tiptap/vue-3'
import { onKeyDown } from '@vueuse/core'
import {
  default as TableOfContents,
  getHierarchicalIndexes,
} from '@tiptap/extension-table-of-contents'

import LucideMessageSquareQuote from '~icons/lucide/message-square-quote'
import LucideMessageSquareOff from '~icons/lucide/message-square-off'
import LucideMessageSquareDot from '~icons/lucide/message-square-dot'

import store from '@/store'
import emitter from '@/emitter'
import { rename } from '@/resources/files'
import { printDoc, dynamicList, toast, isModKey } from '@/utils/'
import FontFamily from '@/extensions/font-family'
import FloatingQuoteButton from '@/extensions/comment-button'
import MediaDownload from '@/extensions/media-download'
import OldCommentExtension from '@/extensions/old-comment'
import { CommentExtension } from '@/extensions/comments'
import { CharacterCount } from '@/extensions/character-count'
import { FontSize } from '@/extensions/font-size'
import EmbedExtension from '@/extensions/embed-extension'
import FloatingComments from '@/components/FloatingComments.vue'
import { useComments } from '@/composables/useYjs'

const showComments = ref(true)
const showSettings = defineModel('showSettings')
const showResolved = ref(false)
const edited = ref(false)

const props = defineProps({
  entity: Object,
  document: Object,
  settings: Object,
  editable: Boolean,
  isFrappeDoc: Boolean,
})
const rawContent = ref(props.document.doc.html)
const emit = defineEmits(['saveComment', 'saveDocument'])
const inIframe = inject('inIframe')

const anchors = ref([])
const activeComment = ref(null)

const textEditor = ref('textEditor')
const editor = computed(() => {
  const editor = textEditor.value?.editor
  return editor
})
provide('editor', editor)
const { comments, saveComments, newComment } = useComments(
  props.document,
  editor,
)

const scrollParent = computed(() =>
  document.querySelector('#editorScrollContainer'),
)
defineExpose({ editor })

const save = () => props.document.saveHtml.submit({ html: rawContent.value })
const autosave = debounce(save, 5000)

onBeforeUnmount(() => {
  console.log('savin')
  if (edited.value) save()
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
  CommentExtension.configure({
    comments,
    doc: null,
    activeComment,
    showComments,
    showResolved,
    edited,
    onActivated: onCommentActivated,
  }),
  OldCommentExtension.configure({
    onCommentActivated,
  }),
  MediaDownload,
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
  {
    icon: LucideSettings,
    label: 'Settings',
    action: () => (showSettings.value = true),
  },
  'Separator',
])

// Local saving with IndexedDB
const db = ref()
watch(db, (db) => {
  if (!props.entity.write) return
  db
    .transaction(['content'])
    .objectStore('content')
    .get(props.entity.name).onsuccess = (val) => {
    if (
      val.target.result?.val?.length > 20 &&
      val.target.result.saved > new Date(props.entity.modified)
    )
      rawContent.value = val.target.result.val
  }
})

if (props.entity.write) {
  const request = window.indexedDB.open('Writer', 1)
  request.onsuccess = (event) => {
    db.value = event.target.result
  }
  request.onupgradeneeded = () => {
    if (!request.result.objectStoreNames.contains('content'))
      request.result.createObjectStore('content')
  }
}

// Util functions
const uploadFunction = (file) => {
  const fileUpload = useFileUpload()
  return fileUpload.upload(file, {
    params: { doc: props.entity.name },
    upload_endpoint: `/api/method/drive.api.files.upload_embed`,
  })
}

const autorename = (bypass = false) => {
  const { $anchor } = editor.value.view.state.selection
  if (!($anchor.index(0) === 1 && $anchor.depth === 1)) {
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
  if (!props.entity.title.startsWith('Untitled Document') && !bypass) {
    return
  }

  if (implicitTitle.length)
    rename.submit({
      entity_name: props.entity.name,
      new_title: implicitTitle,
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

emitter.on('printFile', () => {
  if (editor.value) printDoc(editor.value.getHTML(), props.settings)
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
</style>
