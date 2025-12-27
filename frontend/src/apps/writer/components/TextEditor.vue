<template>
  <CoreEditor
    ref="textEditor"
    v-model:show-settings="showSettings"
    v-model:edited="edited"
    v-bind="{ ...props, ...commentsDetail }"
    :doc
    :extensions
    @save="(manual = false) => save(manual)"
    @cleanup="cleanup"
  />
</template>

<script setup>
import { computed, onMounted, ref, provide } from 'vue'

import Collaboration from '@tiptap/extension-collaboration'
import CollaborationCaret from '@tiptap/extension-collaboration-caret'

import store from '@/store'

import { getRandomColor } from '@/utils'
import { rebuild } from '@/extensions/comments'
import { useYjs } from '@/composables/useYjs'

const activeComment = ref(null)
const showSettings = defineModel('showSettings')

watch(activeComment, () => rebuild(editor.value))
const edited = ref(false)

const props = defineProps({
  document: Object,
  entity: Object,
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

const { doc, save, cleanup, provider, permanentUserData, ...commentsDetail } =
  useYjs(props.document, editor, edited)

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
