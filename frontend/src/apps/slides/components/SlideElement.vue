<template>
	<div :style="elementStyle">
		<component
			:is="getDynamicComponent(element.type)"
			:key="mode + '-' + element.id"
			:element="element"
			:mode="mode"
			@clearTimeouts="$emit('clearTimeouts')"
		/>

		<Resizer v-if="showResizers" :elementType="element.type" :dimensions="selectionBounds" />
	</div>
</template>

<script setup>
import { computed, useTemplateRef } from 'vue'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'
import Resizer from '@/components/Resizer.vue'

import { activeElement, activeElementIds, focusElementId } from '@/stores/element'

import { selectionBounds, slideBounds } from '@/stores/slide'

const props = defineProps({
	mode: {
		type: String,
		default: 'editor',
	},
	outline: {
		type: String,
		default: 'none',
	},
	isDragging: {
		type: Boolean,
		default: false,
	},
	elementOffset: {
		type: Object,
		default: () => ({ left: 0, top: 0 }),
	},
})

const emit = defineEmits(['clearTimeouts'])

const isActive = computed(() => {
	return activeElementIds.value.includes(element.value.id)
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const outline = computed(() => {
	switch (props.outline) {
		case 'primary':
			return `#70B6F0 solid ${2 / slideBounds.scale}px`
		case 'secondary':
			return `#70B6F0 solid ${2 / slideBounds.scale}px`
		default:
			return props.outline
	}
})

const elementStyle = computed(() => {
	const offsetLeft = isActive.value ? props.elementOffset.left : 0
	const offsetTop = isActive.value ? props.elementOffset.top : 0
	const offsetWidth = isActive.value ? props.elementOffset.width : 0

	const elementLeft = element.value.left + offsetLeft
	const elementTop = element.value.top + offsetTop

	let elementWidth = element.value.width
	if (elementWidth) {
		elementWidth = `${elementWidth + offsetWidth}px`
	} else {
		elementWidth = 'auto'
	}

	return {
		position: 'absolute',
		width: elementWidth,
		height: 'auto',
		left: `${elementLeft}px`,
		top: `${elementTop}px`,
		outline: outline.value,
		boxSizing: 'border-box',
	}
})

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

const showResizers = computed(() => {
	if (!activeElement.value || focusElementId.value || props.mode == 'slideshow') return false
	return activeElement.value.id == element.value.id && !props.isDragging
})
</script>
