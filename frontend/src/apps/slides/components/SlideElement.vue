<template>
	<div :style="elementStyle">
		<component :is="getDynamicComponent(element.type)" :element="element" />
	</div>
</template>

<script setup>
import { computed, inject, nextTick } from 'vue'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'

import {
	activeElementIds,
	pairElementId,
	focusElementId,
	setActiveElements,
	activeElement,
} from '@/stores/element'

const props = defineProps({
	outline: {
		type: String,
		default: 'none',
	},
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const outline = computed(() => {
	switch (props.outline) {
		case 'primary':
			return '#70B6F0 solid 2px'
		case 'secondary':
			return '#70b6f080 solid 2px'
		default:
			return props.outline
	}
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
