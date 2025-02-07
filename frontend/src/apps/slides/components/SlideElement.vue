<template>
	<div :style="elementStyle">
		<component :is="getDynamicComponent(element.type)" :element="element" v-bind="$attrs" />
	</div>
</template>

<script setup>
import { computed, useAttrs } from 'vue'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'

import {
	activeElementId,
	activeElementIds,
	pairElementId,
	focusElementId,
	activePosition,
} from '@/stores/element'

const attrs = useAttrs()

const element = defineModel('element', {
	type: Object,
	default: null,
})

const outline = computed(() => {
	if (
		activeElementIds.value
			.concat([activeElementId.value, focusElementId.value])
			.includes(attrs['data-index'])
	)
		return '#70B6F0 solid 2px'
	else if (pairElementId.value == attrs['data-index']) return '#70b6f092 solid 2px'
	else return 'none'
})

const elementStyle = computed(() => ({
	position: activeElementIds.value.includes(attrs['data-index']) ? 'absolute' : 'fixed',
	width: `${element.value.width}px`,
	height: `${element.value.height}px`,
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	outline: outline.value,
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
