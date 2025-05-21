<template>
	<div ref="elementDiv" :style="elementStyle">
		<component :is="getDynamicComponent(element.type)" :element="element" />

		<Resizer
			v-if="isElementActive"
			:elementType="element.type"
			:elementDivRef="elementDivRef"
			@updateElementWidth="updateElementWidth"
		/>
	</div>
</template>

<script setup>
import { computed, useTemplateRef } from 'vue'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'
import Resizer from '@/components/Resizer.vue'

import { activeElementIds } from '@/stores/element'

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
	if (!activeElementIds.value.length) return false
	return activeElementIds.value[0] == element.value.id
})

const updateElementWidth = (deltaWidth) => {
	if (element.value.width) {
		element.value.width += deltaWidth
	} else {
		const elementDiv = elementDivRef.value
		const width = elementDiv.getBoundingClientRect().width

		element.value.width = width + deltaWidth
	}
}
</script>
