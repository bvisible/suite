<template>
	<div :style="elementStyle">
		<component :is="getDynamicComponent(element.type)" :element="element" v-bind="$attrs" />
	</div>
</template>

<script setup>
import { computed, inject, useAttrs } from 'vue'
import { currentDataIndex, currentPairedDataIndex } from '@/stores/slide'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'
import { currentFocusedIndex } from '@/stores/slide'

const attrs = useAttrs()

const element = defineModel('element', {
	type: Object,
	default: null,
})

const showOutline = computed(() => {
	return (
		currentDataIndex.value == attrs['data-index'] ||
		currentPairedDataIndex.value == attrs['data-index'] ||
		currentFocusedIndex.value == attrs['data-index']
	)
})

const elementStyle = computed(() => ({
	position: 'fixed',
	width: `${element.value.width}px`,
	height: 'auto',
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	outline: showOutline.value ? '#70B6F0 solid 2px' : 'none',
	outlineOffset: '5px',
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
