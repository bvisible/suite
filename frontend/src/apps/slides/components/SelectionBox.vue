<template>
	<div v-if="activeElementIds.length" :style="boxStyles">
		<Resizer
			v-if="showResizers"
			:elementType="activeElement?.shapeType || activeElement?.type"
			:dimensions="selectionBounds"
			:style="{ pointerEvents: 'auto' }"
		/>
	</div>
</template>
<script setup>
import { computed } from 'vue'

import Resizer from '@/apps/slides/components/Resizer.vue'

import { slideBounds, selectionBounds } from '@/apps/slides/stores/slide'
import { rotationDelta } from '@/apps/slides/composables/useRotator'
import {
  activeElementIds,
  focusElementId,
  activeElement,
  cropSelectionToFitContent,
} from '@/apps/slides/stores/element'

const props = defineProps({
  isDragging: {
    type: Boolean,
    default: false,
  },
  elementOffset: {
    type: Object,
    default: () => ({ left: 0, top: 0 }),
  },
})

const showResizers = computed(() => {
  return activeElementIds.value.length == 1 && !focusElementId.value && !props.isDragging
})

const outline = computed(() => {
  if (activeElement.value?.shapeType == 'line') return 'none'

  if (activeElementIds.value.length == 1) return `#70B6F0 solid ${2 / slideBounds.scale}px`
  return `#70B6F092 solid ${0.1 / slideBounds.scale}px`
})

const isRotatable = computed(() => {
  return ['shape', 'image'].includes(activeElement.value?.type)
})

const selectionRotation = computed(() => {
  if (activeElementIds.value.length != 1 || !isRotatable.value) return 0
  return (activeElement.value.rotation || 0) + rotationDelta.value
})

const boxStyles = computed(() => {
  const offsetLeft = props.elementOffset.left
  const offsetTop = props.elementOffset.top

  // selectionBounds track the live position; rendering subtracts the
  // transient offset and reapplies it as a transform so moving the box
  // never triggers layout (matches SlideElement)
  const offsetTransform =
    offsetLeft || offsetTop ? `translate(${offsetLeft}px, ${offsetTop}px)` : ''
  const rotateTransform = selectionRotation.value ? `rotate(${selectionRotation.value}deg)` : ''

  return {
    position: 'absolute',
    backgroundColor: activeElementIds.value.length == 1 ? '' : '#70b6f025',
    outline: outline.value,
    width: `${selectionBounds.width}px`,
    height: `${selectionBounds.height}px`,
    left: `${selectionBounds.left - offsetLeft}px`,
    top: `${selectionBounds.top - offsetTop}px`,
    boxSizing: 'border-box',
    zIndex: 9999,
    pointerEvents: activeElementIds.value.length == 1 ? 'none' : 'auto',
    transform: [offsetTransform, rotateTransform].filter(Boolean).join(' '),
    transformOrigin: 'center center',
  }
})

const handleSelectionChange = elementIds => {
  if (!elementIds.length) return
  cropSelectionToFitContent(elementIds)
}

defineExpose({
  handleSelectionChange,
})
</script>
