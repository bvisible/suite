<template>
	<div
		:style="elementStyle"
		:class="isEqual(activeElement, element) ? 'outline outline-offset-2 outline-blue-400' : ''"
	>
		<component :is="getDynamicComponent(element.type)" :element="element" />
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { activeElement } from '@/stores/slide'
import { isEqual } from 'lodash'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'

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
