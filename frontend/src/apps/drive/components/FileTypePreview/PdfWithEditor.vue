<!-- //// Neoffice — added file (no upstream equivalent): the PDF preview, and the way into the PDF editor.
     Upstream previews a PDF and nothing more. When this site has the PDF editor (see suite/drive/wopi/craft.py) and the
     user may change the file, "Edit PDF" opens it in PdfCraft, over the page. The preview stays what it was. //// -->
<template>
  <PDFPreview :key="previews" :preview-entity="previewEntity" />
  <Button v-if="canEdit" class="absolute right-4 top-4 z-10 shadow-md" variant="solid" :loading="starting" @click="start">
    <template #prefix><LucidePencil class="size-4" /></template>
    {{ __('Edit PDF') }}
  </Button>
  <Teleport to="body">
    <div v-if="config" class="fixed inset-0 z-40 flex flex-col bg-surface-base">
      <div class="flex items-center justify-between gap-3 border-b border-outline-gray-2 px-4 py-2">
        <span class="truncate text-p-base text-ink-gray-8">{{ previewEntity.file_name }}</span>
        <Button variant="subtle" @click="close">{{ __('Close') }}</Button>
      </div>
      <CraftEditor ref="editor" class="min-h-0 grow" :config="config" :preview-entity="previewEntity" />
    </div>
  </Teleport>
</template>

<script setup>
import { Button, call, createResource, toast } from 'frappe-ui'
import { computed, ref } from 'vue'
import CraftEditor from '@/apps/drive/components/FileTypePreview/CraftEditor.vue'
import PDFPreview from '@/apps/drive/components/FileTypePreview/PDFPreview.vue'
import LucidePencil from '~icons/lucide/pencil'

const props = defineProps({ previewEntity: Object })

const editor = ref(null)
const config = ref(null)
const starting = ref(false)
// The preview is built again after an editing session: it shows what was saved.
const previews = ref(0)

// Which editors the site has: one cheap call, the answer does not change within a visit.
const installed = createResource({
  url: 'suite.drive.wopi.craft.get_installed_editors',
  cache: 'craft-installed-editors',
  auto: true,
})
const canEdit = computed(() => !!installed.data?.pdf && !!props.previewEntity?.write)

async function start() {
  starting.value = true
  try {
    const answer = await call('suite.drive.wopi.craft.get_craft_editor_config', {
      file_id: props.previewEntity.name,
      requested: 'pdf',
    })
    if (!answer?.available) throw new Error(answer?.reason || __('The editor is unavailable'))
    config.value = answer
  } catch (e) {
    toast.error(e.messages?.[0] || e.message)
  } finally {
    starting.value = false
  }
}

function close() {
  if (editor.value?.dirty && !window.confirm(__('You have unsaved changes. Leave without saving?'))) return
  config.value = null
  previews.value += 1
}
</script>
