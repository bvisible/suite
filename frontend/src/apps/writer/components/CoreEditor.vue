<template>
  <div class="flex flex-col w-full bg-surface-white">
    <TextEditorFixedMenu
      v-if="editable"
      class="py-1.5 w-full max-w-[100vw] overflow-x-auto flex md:justify-center shrink-0 transition-opacity duration-1 border-b border-outline-gray-modals"
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
        class="min-w-full h-full flex flex-col"
        @click="
          $event.target.tagName === 'DIV' &&
          textEditor.editor?.chain?.().focus?.().run?.()
        "
      >
        <FTextEditor
          ref="textEditor"
          class="min-w-full h-full flex flex-col"
          editor-class="min-h-full  px-10 overflow-x-auto py-7"
          :upload-function
          :autofocus="true"
          :content="rawContent"
          :mentions="{ mentions: allUsers.data, selectable: false }"
          placeholder="Start thinking..."
          :extensions="editorExtensions"
          :bubble-menu="bubbleButtons"
          :bubble-menu-options="{
            shouldShow: ({ from, to }) => {
              if (from === to) return false
              let hide = false
              comments.forEach((k) => (k.new || k.edit) && (hide = true))
              return !hide
            },
            getReferencedVirtualElement: () => {
              const { selection } = editor.state
              const { from, to } = selection

              const start = editor.view.coordsAtPos(from)
              const end = editor.view.coordsAtPos(to)

              const editorElement = editor.view.dom
              const editorRect = editorElement.getBoundingClientRect()

              const verticalCenter = (start.bottom + end.bottom) / 2 + 15
              return {
                getBoundingClientRect: () => ({
                  width: 0,
                  height: 0,
                  x: editorRect.right,
                  y: verticalCenter,
                  top: verticalCenter,
                  right: editorRect.right,
                  bottom: verticalCenter,
                  left: editorRect.right,
                }),
              }
            },
          }"
          :editable
          :starterkit-options="{
            undoRedo: doc ? false : true,
            trailingNode: { node: 'paragraph', notAfter: 'tab' },
            paragraph: false,
            gapcursor: false,
          }"
          @change="(val) => emit('editor-change', val)"
          @keydown="
            async (e) => {
              if (editable && !e.metaKey && !e.ctrlKey & !edited) {
                edited = true
                await nextTick()
                autoversion()
              }
            }
          "
        >
          <template #editor="{ editor }">
            <EditorContent
              class="bg-surface-white prose prose-sm prose-v2"
              :class="[
                settings?.wide
                  ? 'md:min-w-[100ch] md:max-w-[100ch]'
                  : 'md:min-w-[48rem] md:max-w-[48rem]',
                isPainting && 'cursor-crosshair',
              ]"
              :style="{
                fontFamily: `var(--font-${settings?.font_family})`,
                fontSize: `${settings?.font_size || 15}px`,
                lineHeight: settings?.line_height || 1.5,
                '--paragraph-spacing-before': `${settings?.paragraph_spacing_before || 0}px`,
                '--paragraph-spacing-after': `${settings?.paragraph_spacing_after || 0}px`,
              }"
              :editor="editor"
            />
          </template>
        </FTextEditor>
      </div>
      <FloatingComments
        v-if="commentsPainted"
        :y-comments="comments"
        v-model:active-comment="activeComment"
        :show-comments
        :document
        :show-resolved
        :editor
        @save="saveComments"
      >
        <div class="sticky self-end top-3 flex items-center gap-1">
          <Button
            :label="showResolved ? 'Hide resolved' : 'Show resolved'"
            v-if="
              showComments &&
              Array.from(comments._map).find(
                (k) => k[1].content?.arr?.[0].resolved,
              )
            "
            class="text-sm text-ink-gray-5"
            variant="ghost"
            @click="showResolved = !showResolved"
          />
          <Button
            v-if="comments._map.size"
            :icon="
              showComments ? LucideMessageSquareOff : LucideMessageSquareQuote
            "
            variant="outline"
            :tooltip="showComments ? 'Hide comments' : 'Show comments'"
            @click="showComments = !showComments"
          ></Button>
        </div>
      </FloatingComments>
    </div>
  </div>
</template>
<script setup>
import { EditorContent, Extension } from '@tiptap/vue-3'
import {
  TextEditor as FTextEditor,
  TextEditorFixedMenu,
  toast,
  useFileUpload,
} from 'frappe-ui'
import { Slice } from '@tiptap/pm/model'
import { TextSelection } from '@tiptap/pm/state'
import ManageFont from './ManageFont.vue'
import { v4 as uuidv4 } from 'uuid'
import {
  computed,
  defineAsyncComponent,
  ref,
  onBeforeUnmount,
  h,
  provide,
  nextTick,
} from 'vue'
import { Plugin } from '@tiptap/pm/state'

import FloatingComments from './FloatingComments.vue'
import { Selection, CharacterCount } from '@tiptap/extensions'
import { PageBreakExtension } from '@/extensions/page-break'
import { onKeyDown } from '@vueuse/core'

import store from '@/store'
import emitter from '@/emitter'
import { rename, allUsers } from 'frappe-ui/frappe/drive/js/resources'
import { printDoc, updateURLSlug, isModKey, COMMON_EXTENSIONS } from '@/utils'

import MediaDownload from '@/extensions/media-download'
import { CommentExtension, rebuild } from '@/extensions/comments'
import {
  default as TableOfContents,
  getHierarchicalIndexes,
} from '@tiptap/extension-table-of-contents'
import OldCommentExtension from '@/extensions/old-comment'
import { TabsExtension } from '@/extensions/tabs'

import { getTemplates } from '@/resources'
import { insertTemplate } from '@/utils'

import LucideMessageSquareQuote from '~icons/lucide/message-square-quote'
import LucideMessageSquareOff from '~icons/lucide/message-square-off'
import LucidePaintRoller from '~icons/lucide/paint-roller'
import LucideBrushCleaning from '~icons/lucide/brush-cleaning'
import LucideSettings from '~icons/lucide/settings'
import LucideForm from '~icons/lucide/sticky-note'
import LucideAlignVerticalSpacingAround from '~icons/lucide/align-vertical-space-around'
import LucideMessageSquarePlus from '~icons/lucide/message-square-plus'

const props = defineProps({
  document: Object,
  entity: Object,
  settings: Object,
  editable: Boolean,
  doc: { required: false, default: null },
  extensions: { type: Array, default: [] },
  comments: Object,
  newComment: Function,
  saveComments: Function,
  //   Checker for collab
  rawContent: String,
})
const emit = defineEmits(['save', 'editor-change'])
const scrollParent = computed(() =>
  document.querySelector('#editorScrollContainer'),
)
const anchors = ref([])
const textEditor = ref('textEditor')
const editor = computed(() => {
  const editor = textEditor.value?.editor
  return editor
})
provide('editor', editor)
defineExpose({ editor })
const activeComment = ref(null)
const showSettings = defineModel('showSettings')
const edited = defineModel('edited')

watch(activeComment, () => rebuild(editor.value))
const showComments = ref(true)
const showResolved = ref(false)
const commentsPainted = ref(false)
const isPainting = computed(() =>
  editor.value && editor.value.storage.styleClipboard.styleClipboard
    ? true
    : false,
)

const autoversion = async () => {
  if (!edited.value) return
  const html = editor.value.getHTML()
  if (!html || html === '<p></p>') return
  await props.document.newVersion.submit({ data: html })
  if (props.document.newVersion.error) {
    toast.error(
      'Something has gone wrong - please copy the file content and contact support.',
    )
  }
}
const autoversionInterval = setInterval(autoversion, 10 * 60 * 1000)

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
  Extension.create({
    addKeyboardShortcuts() {
      if (!getTemplates.data) return {}
      const shortcuts = Object.fromEntries(
        getTemplates.data
          .filter((t) => t.keymap)
          .map((t) => [
            t.keymap,
            () => {
              return insertTemplate(t, this.editor)
            },
          ]),
      )
      return shortcuts
    },
    addCommands: () => {
      return {
        // override tiptap's as all marks are removed while using tabs
        removeEmptyTextStyle:
          () =>
          ({ tr }) => {
            const { selection } = tr

            tr.doc.nodesBetween(selection.from, selection.to, (node, pos) => {
              if (!node.isText) {
                return true
              }

              const TYPE = 'textStyle'
              const styleMark = !node.marks
                .filter((mark) => mark.type.name === TYPE)
                .some((mark) =>
                  Object.values(mark.attrs).some((value) => !!value),
                )
              if (styleMark) {
                tr.removeMark(pos, pos + node.nodeSize, styleMark.type)
              }
            })
          },
      }
    },
    addProseMirrorPlugins() {
      return [
        new Plugin({
          props: {
            // remove tab container while copying
            transformCopied(slice) {
              const frag = slice.content
              if (frag.childCount === 1 && frag.child(0).type.name === 'tab') {
                const tabNode = frag.child(0)
                return new Slice(
                  tabNode.content,
                  slice.openStart,
                  slice.openEnd,
                )
              }
              return slice
            },
          },
        }),
      ]
    },
  }),
  PageBreakExtension,
  CharacterCount,
  Selection,
  // MathematicsExtension,
  TabsExtension,
  OldCommentExtension.configure({
    onCommentActivated: onCommentActivated,
  }),
  TableOfContents.configure({
    onUpdate: (val) => (anchors.value = val),
    getIndex: getHierarchicalIndexes,
    scrollParent: () => scrollParent.value,
  }),
  MediaDownload,

  CommentExtension.configure({
    comments: props.comments,
    doc: props.doc,
    activeComment,
    showComments,
    showResolved,
    edited,
    onActivated: onCommentActivated,
    onDecorationsPainted: () => (commentsPainted.value = true),
  }),
  ...props.extensions,
]

const menuButtons = computed(() => [
  ['Paragraph', 'Heading 1', 'Heading 2', 'Heading 3', 'Heading 4'],
  'Bold',
  'Italic',
  'Underline',
  'Strikethrough',
  'Link',
  'FontColor',
  ['Align Left', 'Align Center', 'Align Right'],
  {
    label: 'Paint Styles',
    icon: LucidePaintRoller,
    // how do we get this prop into f-ui?
    isActive: () => isPainting.value,
    action: (editor) => {
      editor.commands.focus()
      editor.commands.storeStyles()
    },
  },
  {
    label: 'Clear formatting',
    icon: LucideBrushCleaning,
    isActive: (editor) =>
      editor.storage.styleClipboard.styleClipboard ? true : false,
    action: (editor) => {
      editor.commands.focus()
      editor.commands.clearStyles()
    },
    isActive: () => false,
  },
  'Separator',
  {
    label: 'FontOptions',
    component: h(ManageFont, {
      editor,
      font_size: +props.settings.font_size || 15,
      font_family: props.settings.font_family || 'inter',
    }),
  },
  'Separator',
  ['Bullet List', 'Numbered List', 'Task List'],
  'Blockquote',
  'Code',
  // {
  //   label: 'Mathematics',
  //   icon: LucideSquareFunction,
  //   action: (editor) => editor.commands.openMathEditor('block'),
  // },
  ['Image', 'Video'],
  'Separator',
  'Iframe',
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
  'TableOfContents',
  'Separator',
  {
    label: 'Page Break',
    icon: LucideForm,
    action: (editor) => editor.commands.setPageBreak(),
  },
  {
    label: 'Custom Spacing',
    icon: LucideAlignVerticalSpacingAround,
    component: h(
      defineAsyncComponent(() => import('@/components/SpacingDialog.vue')),
      { settings: props.settings, editor: editor },
    ),
  },
  {
    icon: LucideSettings,
    label: 'Settings',
    action: () => (showSettings.value = true),
  },
])

const bubbleButtons = props.entity.comment
  ? [
      {
        label: 'Comment',
        icon: LucideMessageSquarePlus,
        action: () => addComment(),
        isActive: () => false,
      },
    ]
  : []

// Scripts

const uploadFunction = (file) => {
  const fileUpload = useFileUpload()
  return fileUpload.upload(file, {
    params: { file_id: props.entity.name },
    upload_endpoint: `/api/method/writer.api.embed.add`,
  })
}

// Util functions
const autorename = () => {
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
  if (!props.entity.title.startsWith('Untitled Document')) return
  if (implicitTitle.length)
    rename.submit(
      {
        entity_name: props.entity.name,
        new_title: implicitTitle,
      },
      {
        onSuccess: () => {
          props.document.doc.title = rename.params.new_title
          props.document.doc.breadcrumbs[
            props.document.doc.breadcrumbs.length - 1
          ].title = rename.params.new_title
          updateURLSlug(rename.params.new_title)
        },
      },
    )
}

const addComment = () => {
  if (!props.doc) {
    return toast.error("New comments aren't supported on old schema.")
  }
  showComments.value = true
  const id = uuidv4()
  const { state } = editor.value
  const { from, to } = state.selection
  if (from === to) return
  props.newComment(
    id,
    from,
    to,
    store.state.user.id,
    state.doc.textBetween(from, to, ' '),
  )
  activeComment.value = id
  const tr = state.tr
  tr.setSelection(TextSelection.create(state.doc, from))
  editor.value.view.dispatch(tr)
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
const manualSave = () => emit('save', true)
emitter.on('manual-save', manualSave)

onKeyDown('Enter', autorename)
onKeyDown('s', (e) => {
  if (!props.editable) return
  if (!isModKey(e) || e.shiftKey) return
  e.preventDefault()
  manualSave()
  toast.success('Saved document', { duration: 0.75 })
})

onBeforeUnmount(() => {
  if (edited.value) {
    // fix: call autoversion on unmount with savee
    emit('save')
  }
  if (autoversionInterval) clearInterval(autoversionInterval)
  emitter.off('print-file')
  emitter.off('manual-save')
  emit('cleanup')
})
</script>
<style>
@import url('@/styles/editor.css');
iframe {
  border: 1px solid var(--surface-gray-4) !important;
}
.prose-v2 p + p {
  margin-top: var(--paragraph-spacing-before, 0);
}
.prose-v2 p {
  margin-bottom: var(--paragraph-spacing-after, 0);
}
</style>
