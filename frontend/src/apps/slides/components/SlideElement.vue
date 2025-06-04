<template>
	<div ref="elementDiv" :style="elementStyle">
		<component :is="getDynamicComponent(element.type)" :element="element" />

		<Resizer
			v-if="isElementActive"
			:elementType="element.type"
			:dimensions="selectionBounds"
			@resizeToFitContent="resizeToFitContent"
		/>
	</div>
</template>

<script setup>
import { computed, useTemplateRef } from 'vue'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'
import Resizer from '@/components/Resizer.vue'

import { activeElement, activeElementIds, updateElementWidth } from '@/stores/element'

import { selectionBounds, slideBounds } from '@/stores/slide'

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

const elementDivRef = useTemplateRef('elementDiv')

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

const isElementActive = computed(() => {
	if (!activeElement.value) return false
	return activeElement.value.id == element.value.id
})

const resizeToFitContent = () => {
	// create range of the text node within TextElement
	const target = elementDivRef.value
	const range = document.createRange()
	const textNode = target.firstChild
	const originalWidth = target.offsetWidth
	range.selectNodeContents(textNode)

	// find out width of text content
	const textWidth = range.getBoundingClientRect().width

	const newWidth = textWidth - originalWidth + 5 / slideBounds.scale

	updateElementWidth(newWidth)
}
</script>
