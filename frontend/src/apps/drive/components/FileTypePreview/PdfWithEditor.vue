<!-- //// Neoffice — added file (no upstream equivalent): the PDF preview. A PDF opens in the PDF editor (PdfCraft, a browser
     build served by this site, see suite/drive/wopi/craft.py) as a Word, Excel or PowerPoint document opens in its own
     editor: directly, with no button to click first (Jérémy, 14.10: « tu fais directement dans le système PDF »).
     A site that has no build of the editor, or a question that failed, previews the PDF as upstream does, and says
     nothing about it: a PDF is never sent anywhere either way. //// -->
<template>
  <CraftEditor v-if="craftConfig" :config="craftConfig" :preview-entity="previewEntity" />
  <div v-else-if="state === 'probing'" class="w-full h-full flex flex-col items-center justify-center gap-3">
    <LucideLoaderCircle class="size-7 animate-spin text-ink-gray-6" />
  </div>
  <PDFPreview v-else :preview-entity="previewEntity" />
</template>

<script setup>
import { createResource } from 'frappe-ui'
import { onMounted, ref } from 'vue'
import CraftEditor from '@/apps/drive/components/FileTypePreview/CraftEditor.vue'
import PDFPreview from '@/apps/drive/components/FileTypePreview/PDFPreview.vue'
import LucideLoaderCircle from '~icons/lucide/loader-circle'

const props = defineProps({ previewEntity: Object })

// What the server said about this document's editor (get_craft_editor_config): `probing` while asking; `editor`
// when the PDF editor opens it (craftConfig holds its session); `viewer` when this site has no build of it or the
// answer did not come: upstream's preview.
const craftConfig = ref(null)
const state = ref('probing')
const probe = createResource({
  url: 'suite.drive.wopi.craft.get_craft_editor_config',
  onSuccess(data) {
    if (data?.available) {
      craftConfig.value = data
      state.value = 'editor'
    } else {
      state.value = 'viewer'
    }
  },
  onError() {
    state.value = 'viewer'
  },
})

// `requested` names the editor, as before the server took the PDF editor by default: an older server answers too.
onMounted(() => probe.submit({ file_id: props.previewEntity.name, requested: 'pdf' }))
</script>
