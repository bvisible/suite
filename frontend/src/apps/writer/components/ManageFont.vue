<template>
  <div class="flex gap-2">
    <FormControl
      class="w-15"
      variant="outline"
      type="number"
      v-model="size"
      :placeholder="`${font_size}`"
    />
    <FontSelect v-model="selected" :font_family :editor />
  </div>
</template>
<script setup>
import { FormControl } from 'frappe-ui'
import { ref, watchEffect, watch } from 'vue'
import { FONT_FAMILIES } from '@/utils'
import FontSelect from './FontSelect.vue'

const props = defineProps({
  editor: Object,
  font_size: Number,
  font_family: String,
})

const selected = ref(null)
const size = ref(null)

watchEffect(() => {
  // potential perf?
  selected.value = FONT_FAMILIES.find((opt) =>
    opt.isActive(props.editor),
  )?.value
  let fontSize = props.editor.getAttributes('textStyle')?.fontSize
  if (fontSize && typeof fontSize !== 'number')
    fontSize = +fontSize.slice(0, -2)
  if (!Number.isNaN(fontSize)) size.value = fontSize
})
watch(size, (val) => {
  props.editor.commands.setFontSize(val + 'px')
})
</script>
