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
      :options="
        FONT_FAMILIES.map((k) => ({
          ...k,
          type: 'custom',
          slotName: 'font',
          key: k.value,
          onClick: () => k.action(editor),
        }))
      "
      :placeholder="FONT_FAMILIES.find((k) => k.value === font_family)?.label"
      :open-on-click="true"
      class="min-w-[10rem]"
      variant="outline"
    >
      <template #font="{ option }"
        ><span :style="{ fontFamily: `var(--font-${option.value})` }">
          {{ option.label }}</span
        ></template
      >
    </Combobox>
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
