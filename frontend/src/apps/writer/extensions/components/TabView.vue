<script setup>
import { NodeViewWrapper, NodeViewContent } from '@tiptap/vue-3'
import { computed } from 'vue'

const props = defineProps({
  node: Object,
  editor: Object,
})

const isActive = computed(() => {
  return props.editor.storage.tab.activeTabId === props.node.attrs.id
})
</script>

<template>
  <node-view-wrapper
    v-focus
    as="div"
    :data-tab-id="node.attrs.id"
    :data-tab-label="node.attrs.label"
    :style="{ display: isActive ? 'block' : 'none' }"
  >
    <node-view-content />
  </node-view-wrapper>
</template>