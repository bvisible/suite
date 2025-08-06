<template>
	<div ref="elementDiv" :style="elementStyle">
		<component
			:is="getDynamicComponent(element.type)"
			:element="element"
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

import {
	activeElement,
	activeElementIds,
	focusElementId,
	updateElementWidth,
} from '@/stores/element'

import { selectionBounds, slideBounds } from '@/stores/slide'

const props = defineProps({
	outline: {
		type: String,
		default: 'none',
	},
	isDragging: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['clearTimeouts'])

const element = defineModel('element', {
	type: Object,
	default: null,
})

const elementDivRef = useTemplateRef('elementDiv')

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

const elementStyle = computed(() => ({
	position: activeElementIds.value.includes(element.value.id) ? 'absolute' : 'fixed',
	width: `${element.value.width}px` || 'auto',
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

const showResizers = computed(() => {
	if (!activeElement.value || focusElementId.value) return false
	return activeElement.value.id == element.value.id && !props.isDragging
})
</script>
