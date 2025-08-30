<template>
	<div :style="elementStyle">
		<component
			:is="getDynamicComponent(element.type)"
			:key="mode + '-' + element.id"
			:element="element"
			:mode="mode"
			@clearTimeouts="$emit('clearTimeouts')"
		/>
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
	highlight: {
		type: Boolean,
		default: false,
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
		outline: props.highlight ? `#70B6F092 solid ${2 / slideBounds.scale}px` : 'none',
		boxSizing: 'border-box',
		zIndex: element.value.zIndex,
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
</script>
