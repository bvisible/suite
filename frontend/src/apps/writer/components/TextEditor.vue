<template>
  <CoreEditor
        ref="textEditor"
    v-model:show-settings="showSettings"
    v-model:edited="edited"
    v-bind="{ ...props, ...commentsDetail }"
    :yjs-doc="doc"
    :extensions
    @save="
      (manual = false, html, func) => {
        save(manual, html).then(func)
      }
    "
    @cleanup="cleanup"
  />
</template>

<script setup>
import { watch } from 'vue'

import { computed, onMounted, ref, provide } from 'vue'

import Collaboration from '@tiptap/extension-collaboration'
import CollaborationCaret from '@tiptap/extension-collaboration-caret'

import store from '@/apps/writer/store'

import { getRandomColor } from '@/apps/writer/utils'
import { rebuild } from '@/apps/writer/extensions/comments'
import { useYjs } from '@/apps/writer/composables/useYjs'

const activeComment = ref(null)
const showSettings = defineModel('showSettings')

watch(activeComment, () => rebuild(editor.value))
const edited = ref(false)

const props = defineProps({
  document: Object,
  file: Object,
  settings: Object,
  editable: Boolean,
})
const emit = defineEmits(['saveComment'])

const textEditor = ref('textEditor')
const editor = computed(() => {
  const editor = textEditor.value?.editor
  return editor
})
provide('editor', editor)
defineExpose({ editor })

const {
  doc,
  save,
  cleanup,
  provider,
  permanentUserData,
  loaded,
  ...commentsDetail
} = useYjs(props.file.doc.name, props.document, editor, edited)
watch(loaded, () => rebuild(editor.value))

const extensions = [
  Collaboration.configure({
    document: doc,
    field: 'default',
    ySyncOptions: {
      permanentUserData,
    },
  }),
  CollaborationCaret.configure({
    provider,
    selectionRender: () => {},
    user: {
      name: store.state.user.fullName,
      id: store.state.user.id,
      avatar: store.state.user.imageURL,
      color: getRandomColor(),
    },
  }),
]

// Events
onMounted(() => {
  const { view, state } = editor.value
  view.dispatch(state.tr)
})
</script>
