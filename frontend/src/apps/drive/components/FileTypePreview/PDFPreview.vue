<template>
  <div v-if="isMobile" class="flex flex-col gap-3 w-96 h-full justify-between grow">
    <div class="flex gap-2 justify-center items-center">
      <Button @click="scale -= 0.25" :disabled="scale <= 0.25" label="-" />
      <span class="text-sm">{{ Math.round(scale * 100) }}%</span>
      <Button @click="scale += 0.25" :disabled="scale >= 2" label="+" />
    </div>
    <div class="grow flex items-center justify-center border rounded-sm max-h-[70vh] overflow-auto">
      <LoadingIndicator v-if="loading" class="w-10 text-ink-gray-8 mx-auto h-full" />
      <VuePdfEmbed
        :class="{ hidden: loading }"
        class="rounded-sm"
        :source="src"
        :page="currentPage"
        :scale="scale"
        @loaded="onLoaded"
        @loading-failed="loading = false"
        @rendering-failed="loading = false"
      />
    </div>
    <div v-if="totalPages" class="flex gap-2 justify-center items-center">
      <Button label="Prev" :disabled="currentPage <= 1" @click="currentPage--" />
      <span class="text-sm">{{ currentPage }} / {{ totalPages }}</span>
      <Button label="Next" :disabled="currentPage >= totalPages" @click="currentPage++" />
    </div>
  </div>
  <embed
    v-else
    :src
    type="application/pdf"
    class="w-full h-full max-h-[80vh] max-w-[80vw] self-center"
  />
</template>

<script setup>
import { ref, computed, defineAsyncComponent } from 'vue'
import { LoadingIndicator, Button } from 'frappe-ui'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'

const VuePdfEmbed = defineAsyncComponent(() => import('vue-pdf-embed'))

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('sm')

const props = defineProps({ previewEntity: Object })
const src = computed(
  () => `/api/method/suite.drive.api.files.get_file_content?entity_name=${props.previewEntity.name}`
)

const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(1)
const loading = ref(true)

function onLoaded(doc) {
  totalPages.value = doc.numPages
  loading.value = false
}
</script>
