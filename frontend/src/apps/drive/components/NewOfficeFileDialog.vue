<!-- //// Neoffice: new file — blank Office files (docx/xlsx/pptx, opened in
     Collabora), port of drive_wopi's NewOfficeFileDialog to the suite. //// -->
<template>
  <Dialog v-model:open="open" :title="dialogTitle" size="xs" :actions="[
    {
      label: __('Create'),
      variant: 'solid',
      disabled: fileName.length === 0,
      loading: createFile.loading,
      onClick: submit,
    },
  ]" @close="dialogType = ''">
    <FormControl v-model="fileName" autofocus :label="__('Name:')" @keyup.enter="submit"
      @keydown="createFile.error = null">
      <template #prefix>
        <component :is="fileIcon" class="size-4" />
      </template>
    </FormControl>
    <div v-if="createFile.error" class="pt-4 text-base font-sm text-ink-red-6">
      {{ createFile.error.messages?.[0] || createFile.error.message }}
    </div>
  </Dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Dialog, createResource, FormControl } from 'frappe-ui'
import { useRoute, useRouter } from 'vue-router'
import LucideFileText from '~icons/lucide/file-text'
import LucideFileSpreadsheet from '~icons/lucide/file-spreadsheet'
import LucidePresentation from '~icons/lucide/presentation'

const route = useRoute()
const router = useRouter()

const props = defineProps({
  parent: String,
  fileType: {
    type: String,
    required: true,
    validator: (value) => ['docx', 'xlsx', 'pptx'].includes(value),
  },
})
const emit = defineEmits(['success'])

const dialogType = defineModel()
const open = ref(true)

const fileName = ref('')

const dialogTitle = computed(() => {
  const titles = {
    docx: __('Create a Word Document'),
    xlsx: __('Create a Spreadsheet'),
    pptx: __('Create a Presentation'),
  }
  return titles[props.fileType] || __('Create a Word Document')
})

const fileIcon = computed(() => {
  const icons = {
    docx: LucideFileText,
    xlsx: LucideFileSpreadsheet,
    pptx: LucidePresentation,
  }
  return icons[props.fileType] || LucideFileText
})

const createFile = createResource({
  url: 'suite.drive.wopi.editor.create_office_file',
  onSuccess(data) {
    open.value = false
    emit('success', data)
    // Open the new file in the Collabora editor right away
    if (data.file_id) {
      router.push({ name: 'drive-File', params: { entityName: data.file_id } })
    }
  },
})

const submit = () => {
  const title = fileName.value.trim()
  if (!title) return

  createFile.submit({
    file_type: props.fileType,
    title,
    parent: props.parent || null,
    team: route.params.team || null,
  })
}
</script>
