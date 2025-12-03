<template>
  <Popover transition="default">
    <template #target="{ togglePopover, isOpen }">
      <slot
        v-bind="{ onClick: () => togglePopover(), isActive: isOpen }"
      ></slot>
    </template>
    <template #body-main>
      <div class="p-4 flex flex-col gap-4">
        <FormControl
          type="number"
          class="grow"
          v-model.number="local.lineHeight"
          min="0.75"
          max="10"
          step="0.2"
          label="Line Height"
        />
        <div class="space-y-1">
          <FormLabel label="Paragraph Spacing" />
          <div class="grid grid-cols-2 gap-2">
            <FormControl
              type="number"
              v-model.number="local.spacingAbove"
              placeholder="0"
              description="Above"
            />
            <FormControl
              type="number"
              v-model.number="local.spacingBelow"
              placeholder="0"
              description="Below"
            />
          </div>
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { Popover } from 'frappe-ui'
import { FormControl, FormLabel } from 'frappe-ui'
import LucideX from '~icons/lucide/x'

const props = defineProps({
  editor: Object,
})

const current = computed(() => {
  const { $from } = props.editor.state.selection
  const node = $from.node($from.depth)

  if (node.type.name === 'paragraph') {
    return node.attrs
  }

  // Walk up until we find a paragraph
  for (let d = $from.depth; d >= 0; d--) {
    const n = $from.node(d)
    if (n.type.name === 'paragraph') return n.attrs
  }

  return {} // fallback
})

function parsePx(v) {
  if (!v) return 0
  if (typeof v !== 'string') return v
  return parseInt(v.replace('px', ''), 10) || 0
}

const defaults = {
  lineHeight: 1.5,
  spacingAbove: 0,
  spacingBelow: 0,
}

const local = reactive({
  lineHeight: +(current.value.lineHeight || defaults.lineHeight),
  spacingAbove: parsePx(current.value.marginTop),
  spacingBelow: parsePx(current.value.marginBottom),
})

// watch(current, (cur) => {
//   local.lineHeight = cur.lineHeight ? +cur.lineHeight : 1.5
//   local.spacingAbove = parsePx(cur.spacingAbove)
//   local.spacingBelow = parsePx(cur.spacingBelow)
// })

function apply() {
  props.editor.commands.updateAttributes('paragraph', {
    lineHeight:
      local.lineHeight === defaults.lineHeight ? null : local.lineHeight,
    spacingAbove:
      local.spacingAbove === defaults.spacingAbove
        ? null
        : `${local.spacingAbove}px`,
    spacingBelow:
      local.spacingAbove === defaults.spacingAbove
        ? null
        : `${local.spacingBelow}px`,
  })
}

watch(local, apply)
</script>
