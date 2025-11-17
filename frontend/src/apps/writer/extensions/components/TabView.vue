<template>
  <div :class="{ hidden: !isActive }">
    <node-view-content />
  </div>
</template>
<script setup>
import { NodeViewContent, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)

const isActive = computed(() => {
  return props.activeId === props.node.attrs.id
})
</script>
