<template>
  <Combobox
    v-model="selected"
    :variant
    :options="
      options.map((k) => ({
        ...k,
        type: 'custom',
        slotName: 'font',
        key: k.value,
        onClick: () => (editor ? k.action(editor) : (selected = k.value)),
      }))
    "
    :placeholder="options.find((k) => k.value === font_family)?.label"
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
</template>
<script setup>
import { Combobox } from 'frappe-ui'
import { FONT_FAMILIES } from '@/utils'
import { watch } from 'vue'
const selected = defineModel()
const props = defineProps({
  font_family: String,
  editor: { type: Object, default: null },
  variant: { type: String, default: 'outline' },
  options: { type: Array, default: FONT_FAMILIES },
})
</script>
