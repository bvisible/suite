<template>
	<div :style="elementStyle">
		<component
			:is="getDynamicComponent(element.type)"
			:element="element"
			@select="selectElement"
			@focus="focusOnElement"
		/>
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

const element = defineModel('element', {
	type: Object,
	default: null,
})

const isDragging = inject('isDragging')

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

const focusOnElement = (e) => {
	e.stopPropagation()
	if (focusElementId.value == element.value.id) return
	setActiveElements([element.value.id], true)
	nextTick(() => {
		e.target.focus()
	})
}

const selectElement = (e) => {
	if (isDragging.value) {
		isDragging.value = false
		return
	}
	if (element.value.type == 'text' && element.value.id == activeElement.value?.id)
		focusOnElement(e)
	else setActiveElements([element.value.id])
}
</script>
