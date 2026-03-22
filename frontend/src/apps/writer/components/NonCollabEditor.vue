<template>
  <CoreEditor
    ref="textEditor"
    v-model:show-settings="showSettings"
    v-model:edited="edited"
    v-bind="{ ...props, ...commentsDetail }"
    :raw-content
    @editor-change="
      (val) => {
        if (val === rawContent) return
        rawContent = val
        if (db)
          db.transaction(['content'], 'readwrite')
            .objectStore('content')
            .put({ val, saved: new Date() }, props.file.name)
        if (!editable) return
        edited = true
        autosave()
      }
    "
    @save="save"
    @cleanup="commentsDetail.cleanup"
  />
</template>

<script setup>
import { debounce } from 'frappe-ui'
import { computed, ref, onBeforeUnmount, watch, inject, provide } from 'vue'
import { useComments } from '@/composables/useYjs'
import CoreEditor from './CoreEditor.vue'

const showSettings = defineModel('showSettings')
const edited = ref(false)

const props = defineProps({
  file: Object,
  document: Object,
  settings: Object,
  editable: Boolean,
})
const rawContent = ref(props.document.doc.html)
const emit = defineEmits(['saveComment', 'saveDocument'])

const textEditor = ref('textEditor')
const editor = computed(() => {
  const editor = textEditor.value?.editor
  return editor
})
provide('editor', editor)
defineExpose({ editor })

const commentsDetail = useComments(props.document, editor)
const save = async (manual, html, onSuccess) => {
  await props.document.saveHtml.submit({ html: rawContent.value })
  onSuccess?.()
}
const autosave = debounce(save, 5000)

onBeforeUnmount(() => {
  if (edited.value) save()
})

// Local saving with IndexedDB
const db = ref()
watch(db, (db) => {
  if (!props.file.write) return
  db
    .transaction(['content'])
    .objectStore('content')
    .get(props.file.name).onsuccess = (val) => {
    if (
      val.target.result?.val?.length > 20 &&
      val.target.result.saved > new Date(props.file.modified)
    )
      rawContent.value = val.target.result.val
  }
})

if (props.file.write) {
  const request = window.indexedDB.open('Writer', 1)
  request.onsuccess = (event) => {
    db.value = event.target.result
  }
  request.onupgradeneeded = () => {
    if (!request.result.objectStoreNames.contains('content'))
      request.result.createObjectStore('content')
  }
}
</script>
