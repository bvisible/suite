<template>
	<div :style="elementStyle">
		<component :is="getDynamicComponent(element.type)" :element="element" />
	</div>
</template>

<script setup>
import { computed } from 'vue'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'

import { activeElementIds, pairElementId, focusElementId } from '@/stores/element'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const outline = computed(() => {
	if (activeElementIds.value.concat([focusElementId.value]).includes(element.value.id))
		return '#70B6F0 solid 2px'
	else if (pairElementId.value === element.value.id) return '#70b6f080 solid 2px'
	else return 'none'
})

const elementStyle = computed(() => ({
	position: activeElementIds.value.includes(element.value.id) ? 'absolute' : 'fixed',
	width: `${element.value.width}px` || 'auto',
	height: 'auto',
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	outline: outline.value,
	boxSizing: 'border-box',
}))

const getDynamicComponent = (type) => {
	switch (type) {
		case 'image':
			return ImageElement
		case 'video':
			return VideoElement
		default:
			return TextElement
	}
}
</script>
