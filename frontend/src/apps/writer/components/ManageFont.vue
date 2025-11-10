<template>
  <div class="flex gap-2">
    <FormControl
      class="w-15"
      variant="outline"
      type="number"
      v-model="size"
      :placeholder="font_size"
    />
    <Combobox
      v-model="selected"
      :options="FONT_FAMILIES"
      :placeholder="FONT_FAMILIES.find((k) => k.value === font_family)?.label"
      :open-on-click="true"
      class="min-w-[10rem]"
      variant="outline"
      :style="selected && { fontFamily: `var(--font-${selected})` }"
    />
  </div>
</template>
<script setup>
import { Combobox, FormControl } from 'frappe-ui'
import { ref, watchEffect, watch } from 'vue'
import { FONT_FAMILIES } from '@/utils'

const props = defineProps({
  editor: Object,
  font_size: String,
  font_family: String,
})
// redo without combobox, and show font family in font family part
const STATIC_FONTS = [
  { value: '6px' },
  { value: '10px' },
  { value: '12px' },
  { value: '14px' },
  { value: '15px' },
  { value: '16px' },
  { value: '17px' },
  { value: '18px' },
  { value: '19px' },
  { value: '20px' },
  { value: '24px' },
  { value: '30px' },
  { value: '48px' },
  { value: '60px' },
  { value: '92px' },
]

const selected = ref(null)
const size = ref(null)

watchEffect(() => {
  selected.value = FONT_FAMILIES.find((opt) =>
    opt.isActive(props.editor),
  )?.value
  let fontSize = props.editor.getAttributes('textStyle')?.fontSize
  if (fontSize && typeof fontSize !== 'number')
    fontSize = +fontSize.slice(0, -2)
  size.value = fontSize
})

watch(selected, (val) => {
  if (val) FONT_FAMILIES.find((k) => k.value === val).action(props.editor)
})
watch(size, (val) => {
  props.editor.commands.setFontSize(val + 'px')
})
</script>
