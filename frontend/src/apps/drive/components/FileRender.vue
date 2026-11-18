<template>
  <div
    v-if="error"
    class="max-w-[450px] h-fit self-center p-10 border border-outline-gray-2 bg-surface-base rounded-4 text-2xl-medium text-center shadow-xl flex flex-col justify-center items-center gap-4"
  >
    <LucideAlertCircle class="size-8 text-ink-gray-8" />
    <span class="text-ink-gray-9">Cannot open file</span>
    <span class="text-base text-center text-ink-gray-7">
      {{ error }}
    </span>
    <Button class="w-full" variant="solid" @click="download"> Download </Button>
  </div>
  <!-- //// Neoffice — `hands-back` and `@no-editor`: a type a Craft editor imports is asked of the editors first (editorFirst). //// -->
  <component
    :is="previewComponent"
    v-else
    :preview-entity="previewEntity"
    v-bind="editorFirst ? { handsBack: true } : {}"
    @no-editor="editorFirst = false"
  />
</template>
<script setup>
import { Button } from 'frappe-ui'
//// Neoffice — ref: editorFirst below
import { computed, defineAsyncComponent, ref } from 'vue'
//// Neoffice — the types a Craft editor imports (editorFirst below)
import { importsInEditor } from '@/apps/drive/utils/files'

const MSOfficePreview = defineAsyncComponent(() => import('@/apps/drive/components/FileTypePreview/MSOfficePreview.vue'))
const ImagePreview = defineAsyncComponent(() => import('@/apps/drive/components/FileTypePreview/ImagePreview.vue'))
const PDFPreview = defineAsyncComponent(() => import('./FileTypePreview/PDFPreview.vue'))
//// Neoffice — a PDF opens in the PDF editor directly when the site has one, and is previewed as upstream does when not.
const PdfWithEditor = defineAsyncComponent(() => import('./FileTypePreview/PdfWithEditor.vue'))
const VideoPreview = defineAsyncComponent(() => import('./FileTypePreview/VideoPreview.vue'))
const TextPreview = defineAsyncComponent(() => import('./FileTypePreview/TextPreview.vue'))
const AudioPreview = defineAsyncComponent(() => import('@/apps/drive/components/FileTypePreview/AudioPreview.vue'))
import LucideAlertCircle from '~icons/lucide/alert-circle'
import { diskSettings } from '@/apps/drive/resources/permissions'

const props = defineProps({
  previewEntity: {
    type: Object,
    required: true,
  },
  modelValue: {
    type: Boolean,
    required: false,
    default: true,
  },
})

if (!diskSettings.data) diskSettings.fetch()
const error = computed(() => {
  const limit = diskSettings.data?.preview_size || 100
  //// Neoffice — `!editorFirst.value && !fallback.value`: a type no preview of the Drive takes (.xlsb, .tsv, .rtf) may
  //// open in an editor, and a .csv or .tsv falls back to the text preview (fallback below)
  if (!editorFirst.value && !fallback.value)
    return 'Previews are not supported for this file type. Would you like to download it instead?'
  else if (props.previewEntity.file_size > limit * 1024 * 1024)
    return 'This is too large to preview - would you like to download instead?'
  return false
})

const download = () => {
  window.location.href = `/api/method/suite.drive.api.files.get_file_content?entity_name=${props.previewEntity.name}&trigger_download=1`
}

const RENDERS = {
  PDF: PdfWithEditor, //// Neoffice — was PDFPreview, which PdfWithEditor falls back to.
  Image: ImagePreview,
  Video: VideoPreview,
  Audio: AudioPreview,
  Document: MSOfficePreview,
  Spreadsheet: MSOfficePreview,
  Presentation: MSOfficePreview,
  Text: TextPreview,
  Code: TextPreview,
}

const EXCEPTIONS = {
  'text/csv': 'Text',
}

const getType = (k) => {
  return EXCEPTIONS[k.mime_type] || k.file_type
}
//// Neoffice — a type a Craft editor imports (utils/files.js, importsInEditor) that the Drive previews elsewhere (a .csv
//// filed as "Text", its type read as plain text) or not at all (.xlsb, .tsv, .rtf: "Unknown") goes to the Office preview
//// first, which asks the server (get_craft_editor_config) and opens the editor; when no editor of this site takes it, the
//// preview hands it back (`no-editor`) and the page shows what it shows without the editors (`fallback`). A .csv or .tsv
//// is data in text whatever type the Drive filed it under (a .csv is often "Spreadsheet"): it falls back to the text
//// preview, never to the Office preview's outside viewer. The other types the Office preview has anyway (.xls, .doc…)
//// stay there, and keep its own viewer when no editor takes them.
const TEXT_DATA = /\.(csv|tsv)$/i
const isTextData = (entity) => TEXT_DATA.test(entity.file_name || entity.title || '')
const fallback = computed(() => {
  if (isTextData(props.previewEntity)) return TextPreview
  return Object.keys(RENDERS).includes(props.previewEntity.file_type) ? RENDERS[getType(props.previewEntity)] : null
})
const editorFirst = ref(
  importsInEditor(props.previewEntity) &&
    (isTextData(props.previewEntity) || RENDERS[getType(props.previewEntity)] !== MSOfficePreview)
)
const previewComponent = computed(() => (editorFirst.value ? MSOfficePreview : fallback.value))
</script>
