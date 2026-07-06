<template>
  <div class="relative w-full h-full flex flex-col">
    <!-- Hidden form: WOPI hands the access token to the iframe via POST -->
    <form ref="wopiForm" :action="editorUrl" method="POST" target="collabora-frame" class="hidden">
      <input type="hidden" name="access_token" :value="accessToken" />
      <input type="hidden" name="access_token_ttl" :value="accessTokenTtl" />
    </form>

    <!-- Loading state -->
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-surface-base">
      <div class="flex flex-col items-center gap-3">
        <LucideLoaderCircle class="size-8 animate-spin text-ink-gray-6" />
        <span class="text-p-base text-ink-gray-7">{{ __('Loading editor…') }}</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="absolute inset-0 flex items-center justify-center">
      <div
        class="max-w-[450px] p-10 bg-surface-base rounded-md text-center shadow-xl flex flex-col items-center gap-4"
      >
        <LucideAlertCircle class="size-10 text-ink-gray-7" />
        <span class="text-p-base text-ink-gray-7">{{ error }}</span>
        <Button variant="solid" @click="loadEditor">{{ __('Retry') }}</Button>
      </div>
    </div>

    <!-- Collabora editor -->
    <iframe
      v-show="!loading && !error"
      ref="editorFrame"
      name="collabora-frame"
      class="w-full h-full grow border-0"
      :title="fileName"
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads"
      allow="clipboard-read; clipboard-write"
      @load="onFrameLoad"
    />
  </div>
</template>
<script setup>
import { Button, createResource } from 'frappe-ui'
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import LucideAlertCircle from '~icons/lucide/alert-circle'
import LucideLoaderCircle from '~icons/lucide/loader-circle'

const props = defineProps({
  previewEntity: Object,
})
const emit = defineEmits(['loaded', 'error'])

const wopiForm = ref(null)
const editorFrame = ref(null)
const editorUrl = ref('')
const accessToken = ref('')
const accessTokenTtl = ref('')
const fileName = ref('')
const loading = ref(true)
const error = ref(null)

const editorConfig = createResource({
  url: 'suite.drive.wopi.discovery.get_editor_config',
  onSuccess(data) {
    editorUrl.value = data.editor_url
    accessToken.value = data.access_token
    accessTokenTtl.value = data.access_token_ttl
    fileName.value = data.file_name
    // Submit the token form once the DOM has the final action URL
    nextTick(() => wopiForm.value && wopiForm.value.submit())
  },
  onError(err) {
    error.value = err.messages?.[0] || err.message || __('Unable to load editor')
    loading.value = false
    emit('error', err)
  },
})

function loadEditor() {
  loading.value = true
  error.value = null
  editorConfig.submit({ file_id: props.previewEntity.name })
}

function onFrameLoad() {
  // First load is the blank frame; the POST result fires a second load
  if (editorUrl.value) {
    loading.value = false
    emit('loaded')
  }
}

onMounted(loadEditor)
onBeforeUnmount(() => {
  // Let Collabora tear down its session cleanly
  if (editorFrame.value) editorFrame.value.src = 'about:blank'
})
</script>
