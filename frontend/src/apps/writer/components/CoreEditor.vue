<template>
  <div class="flex flex-col w-full bg-surface-white">
    <TextEditorFixedMenu
      v-if="editable && editor"
      class="w-full max-w-[100vw] py-1.5 !px-4 md:px-0 overflow-x-auto flex shrink-0 border-b border-outline-gray-modals"
      :buttons="menuButtons"
    />
    <div class="flex flex-1 overflow-auto">
      <ToC v-if="editor" :editor :anchors />
      <div
        id="editor-scroll-container"
        class="flex w-full overflow-y-auto relative"
      >
        <div
          class="h-full flex flex-col flex-grow"
          @click="
            $event.target.tagName === 'DIV' &&
            textEditor.editor?.chain?.().focus?.().run?.()
          "
        >
          <FTextEditor
            ref="textEditor"
            class="min-h-full flex flex-col"
            editor-class="overflow-x-auto pt-10 pb-24 px-5"
            :upload-function
            :autofocus="true"
            :content="rawContent"
            :mentions="{ mentions: allUsers.data, selectable: false }"
            placeholder="Start thinking..."
            :extensions="editorExtensions"
            :bubble-menu="bubButtons"
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
              // undoRedo: doc ? false : true,
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
                class="md:mx-auto flex w-[100vw] bg-surface-white prose prose-sm prose-v2 prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:relative prose-th:relative prose-th:bg-surface-gray-2"
                :class="[
                  settings?.wide
                    ? 'md:min-w-[100ch] md:max-w-[100ch]'
                    : 'md:min-w-[48rem] md:max-w-[48rem]',
                  isPainting && 'cursor-crosshair',
                ]"
                :style="{
                  fontFamily:
                    settings?.font_family &&
                    `var(--font-${settings?.font_family})`,
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
          v-model:active-comment="activeComment"
          :y-comments="comments"
          :file
          :show-comments
          :show-resolved
          :show-unanchored
          :editor
          @save="saveComments"
        >
          <div
            v-if="comments._map.size"
            class="sticky self-end top-4 right-4 z-10"
          >
            <Dropdown :options="commentFilterOptions" placement="right">
              <Button :icon="LucideMessageSquareQuote" variant="outline" />
            </Dropdown>
          </div>
        </FloatingComments>

        <div v-if="!commentsPainted" class="w-72" />
      </div>
    </div>
    <ToCMobile v-if="editor" :editor />
  </div>
</template>
<script setup>
import { EditorContent, Extension } from '@tiptap/vue-3'
import {
  TextEditor as FTextEditor,
  TextEditorFixedMenu,
  toast,
  useFileUpload,
  ContextMenu,
  createEditorButton,
  Dropdown,
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
import { rename, allUsers } from 'frappe-ui/drive/js/resources'
import {
  printDoc,
  updateURLSlug,
  isModKey,
  COMMON_EXTENSIONS,
  formatShortcut,
} from '@/utils'

import MediaDownload from '@/extensions/media-download'
import CleanStyles from '@/extensions/clean-styles'
import { CommentExtension, rebuild } from '@/extensions/comments'
import {
  default as TableOfContents,
  getHierarchicalIndexes,
} from '@tiptap/extension-table-of-contents'
import OldCommentExtension from '@/extensions/old-comment'
import { TabsExtension } from '@/extensions/tabs'
import TabTrailingNode from '@/extensions/tab-trailing-node'

import { getTemplates } from '@/resources'
import { insertTemplate } from '@/utils'

import LucideMessageSquareQuote from '~icons/lucide/message-square-quote'
import LucideMessageSquareOff from '~icons/lucide/message-square-off'
import LucidePaintRoller from '~icons/lucide/paint-roller'
import LucideBrushCleaning from '~icons/lucide/brush-cleaning'
import LucideBrush from '~icons/lucide/brush'
import LucidePilcrow from '~icons/lucide/pilcrow'
import LucideSettings from '~icons/lucide/settings'
import LucideForm from '~icons/lucide/sticky-note'
import LucideAlignVerticalSpacingAround from '~icons/lucide/align-vertical-space-around'
import LucideMessageSquarePlus from '~icons/lucide/message-square-plus'

const props = defineProps({
  file: Object,
  document: Object,
  settings: Object,
  editable: Boolean,
  yjsDoc: { required: false, default: null },
  extensions: { type: Array, default: [] },
  comments: Object,
  newComment: Function,
  saveComments: Function,
  //   Checker for collab
  rawContent: String,
})
const emit = defineEmits(['save', 'editor-change', 'cleanup'])
const scrollParent = computed(() =>
  document.querySelector('#editor-scroll-container'),
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
const showComments = ref(
  JSON.parse(localStorage.getItem('show-comments') || 'false'),
)
watch(showComments, (val) => localStorage.setItem('show-comments', val))
const showResolved = ref(false)
const showUnanchored = ref(false)
const showUnanchoredButton = computed(() => {
  return (
    commentsPainted.value &&
    Array.from(props.comments._map)
      .map(
        (l) =>
          !document.querySelector(
            `[data-comment-name='${l[1].content?.arr?.[0].id}']`,
          ),
      )
      .filter((k) => k).length
  )
})
const commentsPainted = ref(false)
const commentFilterOptions = computed(() => {
  const hasResolved = Array.from(props.comments._map).find(
    (k) => k[1].content?.arr?.[0].resolved,
  )
  return [
    {
      label: 'Comments',
      switch: true,
      switchValue: showComments.value,
      onClick: () => (showComments.value = !showComments.value),
    },
    hasResolved &&
      showComments.value && {
        label: 'Resolved',
        switch: true,
        switchValue: showResolved.value,
        onClick: () => (showResolved.value = !showResolved.value),
      },
    showUnanchoredButton.value &&
      showComments.value && {
        label: 'Outdated',
        switch: true,
        switchValue: showUnanchored.value,
        onClick: () => (showUnanchored.value = !showUnanchored.value),
      },
  ].filter(Boolean)
})
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
  if (
    props.document.newVersion.error &&
    props.document.newVersion.error !== 'Client is offline'
  ) {
    toast.error('Something has gone wrong - please contact support.')
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
                tr.removeMark(
                  pos,
                  pos + node.nodeSize,
                  node.type.schema.marks.textStyle,
                )
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
  CleanStyles.configure({
    allowProperty: (prop, value) => value !== '',
    validators: {
      lineHeight: (value) => !value.endsWith('%'),
      fontFamily: (value) => value.trim() !== '""',
    },
  }),
  // MathematicsExtension,
  TabsExtension,
  TabTrailingNode,
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
    doc: props.yjsDoc,
    activeComment,
    showComments,
    showResolved,
    edited,
    onActivated: onCommentActivated,
    onDecorationsPainted: () => (commentsPainted.value = true),
  }),
  ...props.extensions,
]

const EXTRA_BUTTON_FUNCTIONS = [
  (e) => e.can().sinkListItem('listItem'),
  (e) => e.can().liftListItem('listItem'),
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
      editor.commands.cleanStyles()
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
  'Separator',
  'Image',
  'Video',
  'Iframe',
  'Separator',
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
  {
    type: 'separator',
    condition: (editor) => {
      return EXTRA_BUTTON_FUNCTIONS.some((fn) => fn(editor))
    },
  },
  'DedentList',
  'IndentList',
])

const convertEditorButton = (id) => {
  const command = createEditorButton(id)
  command.disabled = command.isDisabled
  command.onClick = () => command.action(editor.value)
  command.shortcut = formatShortcut(command.shortcut)
  return command
}
const bubButtons = [
  {
    label: 'Comment',
    icon: LucideMessageSquarePlus,
    action: () => addComment(),
  },
]

const bubbleButtons = computed(() => [
  {
    group: true,
    hideLabel: true,
    items: [
      {
        label: 'Comment',
        icon: LucideMessageSquarePlus,
        onClick: () => addComment(),
      },
    ],
  },
  {
    label: 'Formatting',
    icon: LucideBrush,
    submenu: [
      convertEditorButton('Bold'),
      convertEditorButton('Italic'),
      convertEditorButton('Underline'),
      convertEditorButton('Strikethrough'),
    ],
  },
  {
    label: 'Paragraph',
    icon: LucidePilcrow,
    submenu: [
      convertEditorButton('Heading 1'),
      convertEditorButton('Heading 2'),
      convertEditorButton('Heading 3'),
      convertEditorButton('Blockquote'),
      convertEditorButton('Bullet List'),
      convertEditorButton('Numbered List'),
    ],
  },
])

// Scripts

const uploadFunction = (file) => {
  const fileUpload = useFileUpload()
  return fileUpload.upload(file, {
    params: { file_id: props.file.doc.name },
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
    .slice(0, 30)
    .trim()
  if (!props.file.doc.title.startsWith('Untitled Document')) return
  if (implicitTitle.length)
    rename.submit(
      {
        entity_name: props.file.doc.name,
        new_title: implicitTitle.slice(0, 100),
      },
      {
        onSuccess: () => {
          props.file.doc.title = rename.params.new_title
          props.file.doc.breadcrumbs[
            props.file.doc.breadcrumbs.length - 1
          ].title = rename.params.new_title
          updateURLSlug(rename.params.new_title)
        },
      },
    )
}

const addComment = () => {
  if (!props.yjsDoc) {
    return toast.warning("New comments aren't supported on this doc.", {
      duration: 1,
    })
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
    emitter.emit('print-file')
  }
})

emitter.on('print-file', () => {
  if (editor.value)
    printDoc(editor.value.commands.getCurrentTabHTML(), props.settings)
})
const manualSave = (func) => emit('save', true, null, func)
emitter.on('manual-save', manualSave)

onKeyDown('Enter', autorename)
onKeyDown('s', (e) => {
  if (!props.editable) return
  if (!isModKey(e) || e.shiftKey) return
  e.preventDefault()
  manualSave(() => toast.success('Saved document', { duration: 0.75 }))
})

onBeforeUnmount(() => {
  if (edited.value) {
    // fix: call autoversion on unmount with savee
    emit('save', false, editor.value.getHTML())
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
