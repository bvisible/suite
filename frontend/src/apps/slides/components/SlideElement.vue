<template>
	<div
		:style="elementStyle"
		:class="{
			'outline outline-offset-4 outline-blue-400':
				currentDataIndex == $attrs['data-index'] ||
				(currentPairedDataIndex == $attrs['data-index'] && isDragging),
		}"
	>
		<component :is="getDynamicComponent(element.type)" :element="element" v-bind="$attrs" />
	</div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { currentDataIndex, currentPairedDataIndex } from '@/stores/slide'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'

const isDragging = inject('isDragging')

const element = defineModel('element', {
	type: Object,
	default: null,
})

const elementStyle = computed(() => ({
	position: 'fixed',
	width: `${element.value.width}px`,
	height: 'auto',
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	cursor: isDragging.value ? 'move' : 'default',
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
